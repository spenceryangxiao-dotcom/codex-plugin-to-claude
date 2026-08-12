#!/usr/bin/env python3
"""Run a bounded tool-free Claude review of a prepared and sanitized brief."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import Any, Callable


MAX_BRIEF_BYTES = 120_000
VERDICTS = {"PASS", "FAIL", "ASK"}

OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "verdict": {"type": "string", "enum": sorted(VERDICTS)},
        "summary": {"type": "string", "minLength": 1},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low"],
                    },
                    "title": {"type": "string", "minLength": 1},
                    "evidence": {"type": "string", "minLength": 1},
                    "recommendation": {"type": "string", "minLength": 1},
                },
                "required": ["severity", "title", "evidence", "recommendation"],
            },
        },
        "question": {"type": "string"},
    },
    "required": ["verdict", "summary", "findings", "question"],
}

SENSITIVE_PATTERNS = (
    ("secret or credential", re.compile(r"(?i)(authorization\s*:\s*bearer|api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]?\s*[\"']?[A-Za-z0-9_./+\-=]{16,}")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("cloud access key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("payment card", re.compile(r"\b(?:\d[ -]*?){13,19}\b")),
    ("phone number", re.compile(r"(?i)(?:customer\s+)?phone\s*:\s*\+?[0-9][0-9 ()-]{7,}[0-9]")),
    ("raw payload", re.compile(r"(?i)\b(raw[_ -]?payload|raw[_ -]?webhook|customer[_ -]?content)\b\s*:")),
)


class SensitiveContentError(ValueError):
    """Raised before invocation when a brief contains prohibited material."""


def inspect_brief(text: str) -> list[str]:
    """Return category names only; never echo matched sensitive text."""
    return [label for label, pattern in SENSITIVE_PATTERNS if pattern.search(text)]


def build_command(model: str, effort: str, max_budget_usd: float) -> list[str]:
    return [
        "claude",
        "-p",
        "--safe-mode",
        "--model",
        model,
        "--effort",
        effort,
        "--max-budget-usd",
        f"{max_budget_usd:.2f}",
        "--tools",
        "",
        "--permission-mode",
        "plan",
        "--disable-slash-commands",
        "--no-session-persistence",
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(OUTPUT_SCHEMA, separators=(",", ":")),
    ]


def build_prompt(brief: str) -> str:
    return f"""You are the independent reviewer. Codex is the primary developer.
Review only the bounded brief below. You have no repository access and must not request tools.

Verdict contract:
- PASS: no material correctness safety security privacy or regression issue remains.
- FAIL: at least one issue Codex can correct; include concrete evidence and recommendation.
- ASK: a real product risk or tradeoff requires the user's decision; put one concise question in `question`.

Do not invent missing evidence. Treat unverified claims as unverified. Never reproduce possible
credentials personal data customer content or raw payloads in the response.

<review_brief>
{brief}
</review_brief>
"""


def _extract_structured(stdout: str) -> dict[str, Any]:
    try:
        envelope = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("Claude returned non-JSON output") from exc

    structured = envelope.get("structured_output")
    if structured is None and isinstance(envelope.get("result"), str):
        try:
            structured = json.loads(envelope["result"])
        except json.JSONDecodeError as exc:
            raise ValueError("Claude result did not contain structured JSON") from exc
    if not isinstance(structured, dict):
        raise ValueError("Claude output did not contain structured_output")
    return structured


def validate_result(result: dict[str, Any]) -> dict[str, Any]:
    verdict = result.get("verdict")
    if verdict not in VERDICTS:
        raise ValueError("Claude returned an invalid verdict")
    if not isinstance(result.get("summary"), str) or not result["summary"].strip():
        raise ValueError("Claude returned an empty summary")
    findings = result.get("findings")
    if not isinstance(findings, list):
        raise ValueError("Claude returned invalid findings")
    if verdict == "FAIL" and not findings:
        raise ValueError("FAIL verdict requires at least one finding")
    question = result.get("question")
    if not isinstance(question, str):
        raise ValueError("Claude returned an invalid question")
    if verdict == "ASK" and not question.strip():
        raise ValueError("ASK verdict requires a question")
    return result


def review(
    brief_path: pathlib.Path | str,
    *,
    model: str = "sonnet",
    effort: str = "high",
    max_budget_usd: float = 1.00,
    timeout_seconds: int = 300,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    path = pathlib.Path(brief_path)
    raw = path.read_bytes()
    if len(raw) > MAX_BRIEF_BYTES:
        raise ValueError(f"review brief exceeds {MAX_BRIEF_BYTES} bytes")
    brief = raw.decode("utf-8")
    if not brief.strip():
        raise ValueError("review brief is empty")

    categories = inspect_brief(brief)
    if categories:
        raise SensitiveContentError(
            "review brief blocked before Claude invocation; prohibited categories: "
            + ", ".join(categories)
        )

    command = build_command(model, effort, max_budget_usd)
    with tempfile.TemporaryDirectory(prefix="claude-review-") as isolated_cwd:
        completed = run(
            command,
            input=build_prompt(brief),
            text=True,
            capture_output=True,
            check=False,
            cwd=isolated_cwd,
            timeout=timeout_seconds,
        )
    if completed.returncode != 0:
        raise RuntimeError(f"Claude review failed with exit code {completed.returncode}")
    return validate_result(_extract_structured(completed.stdout))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brief", type=pathlib.Path, help="prepared sanitized Markdown brief")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--effort", default="high", choices=("low", "medium", "high", "xhigh", "max"))
    parser.add_argument("--max-budget-usd", type=float, default=1.00)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = review(
            args.brief,
            model=args.model,
            effort=args.effort,
            max_budget_usd=args.max_budget_usd,
            timeout_seconds=args.timeout_seconds,
        )
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"review unavailable: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

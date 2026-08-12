---
name: codex-plugin-to-claude
description: Use when the user explicitly asks Codex to have Claude review, cross-check, audit, or challenge a task, or when Codex detects high-impact risk involving production, payments, authentication, security, privacy, destructive data changes, migrations, core architecture, incident response, or a recurring important bug.
---

# Codex Plugin to Claude

## Core contract

Keep Codex as the primary investigator and developer. Use Claude only as an independent, bounded, read-only reviewer. Claude never edits files, runs repository tools, commits, pushes, merges, deploys, or replaces Codex's verification.

## Decide whether to review

| Signal | Action |
|---|---|
| User explicitly requests Claude review | Treat the request as authorization and review without asking again. |
| High-impact risk is detected without an explicit request | Explain the risk, mention possible Claude/API cost, and ask approval before sending anything. Continue safe local investigation while waiting. |
| Ordinary reversible work | Do not invoke Claude. |

High-impact includes production outages, money movement, authentication/authorization, security or privacy boundaries, irreversible or destructive data operations, schema migrations, core architecture changes, repeated failed fixes, and changes with a large blast radius.

## Review workflow

1. Establish ground truth first. Inspect code, schemas, logs, tests, and authoritative sources. Do not ask Claude to validate assumptions that Codex has not checked.
2. Choose the checkpoint:
   - Review diagnosis or plan before implementation when direction, rollback, or architecture is risky.
   - Review the tested implementation before completion when regressions or runtime behavior are risky.
   - Use both checkpoints only when both independently warrant review.
3. Create a fresh brief from [references/review-brief-template.md](references/review-brief-template.md). Include bounded evidence and selected sanitized diff hunks, not an automatic repository dump.
4. Inspect the brief manually. Never include secrets, credentials, personal identifiers, customer content, payment-card data, phone numbers, raw payloads, or unrelated proprietary material. The runner's scanner is an additional guardrail, not proof of safety.
5. Run `python3 scripts/review_runner.py <brief.md>` from this Skill directory. It invokes Claude with no tools, no repository access, no session persistence, structured output, and a default USD 1 budget cap. Use `--model` or `--max-budget-usd` only when the user authorizes a change.
6. Handle exactly one terminal verdict:
   - `PASS`: independently re-check material claims, then proceed.
   - `FAIL`: Codex fixes the cited issues, reruns relevant tests, and may resubmit the revised artifact.
   - `ASK`: stop at the decision boundary and ask the user the returned question.
7. Allow at most two Claude review rounds for the same artifact by default. After that, stop and report unresolved findings rather than looping.

If Claude is unavailable, times out, exceeds budget, or returns invalid output, state that cross-review did not complete. Never convert an unavailable review into `PASS`.

## Completion report

Report the reviewed checkpoint, model, verdict, material findings, Codex's independent verification, and whether any issue remains. Do not expose Claude's raw transport output or sensitive brief content.

## Common mistakes

- Invoking Claude automatically for an implicit risk without approval.
- Sending a full diff or raw incident payload instead of a bounded brief.
- Treating Claude's `PASS` as a substitute for tests or ground truth.
- Letting `FAIL` trigger unbounded autonomous loops.
- Claiming “Claude reviewed” when the command failed or returned invalid output.

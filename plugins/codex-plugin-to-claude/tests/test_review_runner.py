import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest


RUNNER_PATH = (
    pathlib.Path(__file__).parents[1]
    / "skills"
    / "codex-plugin-to-claude"
    / "scripts"
    / "review_runner.py"
)


def load_runner():
    spec = importlib.util.spec_from_file_location("review_runner", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReviewRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load_runner()

    def write_brief(self, content):
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
        handle.write(content)
        handle.close()
        self.addCleanup(pathlib.Path(handle.name).unlink, missing_ok=True)
        return pathlib.Path(handle.name)

    def test_rejects_empty_brief_before_invocation(self):
        brief = self.write_brief("   \n")
        with self.assertRaisesRegex(ValueError, "empty"):
            self.runner.review(brief, run=lambda *args, **kwargs: self.fail("invoked"))

    def test_rejects_api_token_before_invocation(self):
        brief = self.write_brief("Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456")
        with self.assertRaises(self.runner.SensitiveContentError):
            self.runner.review(brief, run=lambda *args, **kwargs: self.fail("invoked"))

    def test_rejects_customer_phone_before_invocation(self):
        brief = self.write_brief("Customer phone: +1 415 555 0198")
        with self.assertRaises(self.runner.SensitiveContentError):
            self.runner.review(brief, run=lambda *args, **kwargs: self.fail("invoked"))

    def test_rejects_raw_payload_marker_before_invocation(self):
        brief = self.write_brief("RAW_PAYLOAD: {\"event\":\"payment\"}")
        with self.assertRaises(self.runner.SensitiveContentError):
            self.runner.review(brief, run=lambda *args, **kwargs: self.fail("invoked"))

    def test_invokes_claude_without_tools_or_session_persistence(self):
        brief = self.write_brief("# Review brief\nRisk: retry can duplicate a charge\nTests: 12 passed")
        captured = {}

        def fake_run(command, **kwargs):
            captured["command"] = command
            captured["kwargs"] = kwargs
            envelope = {
                "structured_output": {
                    "verdict": "PASS",
                    "summary": "No blocking issue found.",
                    "findings": [],
                    "question": "",
                }
            }
            return subprocess.CompletedProcess(command, 0, json.dumps(envelope), "")

        result = self.runner.review(brief, run=fake_run)

        self.assertEqual(result["verdict"], "PASS")
        self.assertIn("--tools", captured["command"])
        self.assertEqual(captured["command"][captured["command"].index("--tools") + 1], "")
        self.assertIn("--no-session-persistence", captured["command"])
        self.assertIn("--json-schema", captured["command"])
        self.assertNotIn(str(brief), " ".join(captured["command"]))
        self.assertIn("retry can duplicate", captured["kwargs"]["input"])

    def test_rejects_unknown_verdict(self):
        brief = self.write_brief("# Review brief\nRisk: migration rollback")

        def fake_run(command, **kwargs):
            envelope = {
                "structured_output": {
                    "verdict": "APPROVE",
                    "summary": "Looks fine.",
                    "findings": [],
                    "question": "",
                }
            }
            return subprocess.CompletedProcess(command, 0, json.dumps(envelope), "")

        with self.assertRaisesRegex(ValueError, "verdict"):
            self.runner.review(brief, run=fake_run)

    def test_fail_verdict_requires_findings(self):
        brief = self.write_brief("# Review brief\nRisk: migration rollback")

        def fake_run(command, **kwargs):
            envelope = {
                "structured_output": {
                    "verdict": "FAIL",
                    "summary": "Blocking issue.",
                    "findings": [],
                    "question": "",
                }
            }
            return subprocess.CompletedProcess(command, 0, json.dumps(envelope), "")

        with self.assertRaisesRegex(ValueError, "finding"):
            self.runner.review(brief, run=fake_run)


if __name__ == "__main__":
    unittest.main()

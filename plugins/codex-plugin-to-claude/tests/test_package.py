import json
import pathlib
import unittest


PLUGIN_ROOT = pathlib.Path(__file__).parents[1]
REPO_ROOT = pathlib.Path(__file__).parents[3]


class PackageTests(unittest.TestCase):
    def test_plugin_manifest_has_public_metadata(self):
        manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())
        self.assertEqual(manifest["name"], "codex-plugin-to-claude")
        self.assertEqual(manifest["version"], "0.1.0")
        self.assertEqual(manifest["license"], "MIT")
        self.assertEqual(
            manifest["repository"],
            "https://github.com/spenceryangxiao-dotcom/codex-plugin-to-claude",
        )
        self.assertEqual(manifest["interface"]["developerName"], "Spencer Yang")
        self.assertLessEqual(len(manifest["interface"]["defaultPrompt"]), 3)

    def test_marketplace_points_to_plugin(self):
        marketplace = json.loads(
            (REPO_ROOT / ".agents" / "plugins" / "marketplace.json").read_text()
        )
        self.assertEqual(marketplace["name"], "codex-plugin-to-claude")
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], "codex-plugin-to-claude")
        self.assertEqual(entry["source"]["path"], "./plugins/codex-plugin-to-claude")

    def test_distribution_contains_no_placeholders(self):
        placeholder = "[" + "TODO:"
        for path in REPO_ROOT.rglob("*"):
            if path.is_file() and ".git" not in path.parts:
                try:
                    content = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                self.assertNotIn(placeholder, content, str(path))

    def test_skill_is_present(self):
        skill = PLUGIN_ROOT / "skills" / "codex-plugin-to-claude" / "SKILL.md"
        self.assertTrue(skill.is_file())
        self.assertIn("name: codex-plugin-to-claude", skill.read_text())


if __name__ == "__main__":
    unittest.main()

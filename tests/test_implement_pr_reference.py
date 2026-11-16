"""The standalone pr skill is gone, and no skill owns generic PR prose."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import repo_skill_catalog  # noqa: E402


MATT = ROOT / "plugins/mattpocock-skills"
IMPLEMENT = MATT / "skills/implement"


class RemovedPrSkillTests(unittest.TestCase):
    def test_pr_is_absent_from_the_catalog_and_the_implement_directory(self) -> None:
        catalog = repo_skill_catalog.load_repo_skill_catalog(ROOT)
        names = {source.name for source in catalog.sources}
        matt = {source.name for source in catalog.sources if source.plugin == "mattpocock-skills"}
        self.assertEqual(len(names), 29)
        self.assertEqual(len(matt), 16)
        self.assertNotIn("pr", names)
        self.assertNotIn("ask-matt", names)
        self.assertIn("implement", matt)
        self.assertFalse((MATT / "skills/pr").exists())
        self.assertFalse((MATT / "skills/ask-matt").exists())
        for leftover in ("PR.md", "CREDITS.md", "LICENSE"):
            self.assertFalse((IMPLEMENT / leftover).exists(), leftover)

    def test_no_skill_is_a_pull_request_authoring_route(self) -> None:
        implement = (IMPLEMENT / "SKILL.md").read_text(encoding="utf-8")
        guide = (ROOT / "plugins/workflow/skills/skill-guide/SKILL.md").read_text(encoding="utf-8")
        readme = (MATT / "README.md").read_text(encoding="utf-8")
        self.assertIn("name: implement", implement)
        self.assertNotIn("PR.md", implement)
        self.assertNotIn("pull request", implement.lower())
        self.assertIn("name: skill-guide", guide)
        self.assertNotIn("`/pr`", guide)
        self.assertNotIn("PR.md", guide)
        self.assertNotIn("pull request", guide.lower())
        for stale in ("skills/pr/", "skills/implement/PR.md", "skills/implement/CREDITS.md", "Dex Horthy"):
            self.assertNotIn(stale, readme)


if __name__ == "__main__":
    unittest.main()

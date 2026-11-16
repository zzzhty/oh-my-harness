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
        self.assertEqual(len(names), 31)
        self.assertEqual(len(matt), 19)
        self.assertNotIn("pr", names)
        self.assertIn("implement", matt)
        self.assertIn("ask-matt", matt)
        self.assertFalse((MATT / "skills/pr").exists())
        for leftover in ("PR.md", "CREDITS.md", "LICENSE"):
            self.assertFalse((IMPLEMENT / leftover).exists(), leftover)

    def test_no_skill_is_a_pull_request_authoring_route(self) -> None:
        implement = (IMPLEMENT / "SKILL.md").read_text(encoding="utf-8")
        router = (MATT / "skills/ask-matt/SKILL.md").read_text(encoding="utf-8")
        readme = (MATT / "README.md").read_text(encoding="utf-8")
        self.assertIn("name: implement", implement)
        self.assertNotIn("PR.md", implement)
        self.assertNotIn("pull request", implement.lower())
        self.assertIn("name: ask-matt", router)
        self.assertIn("A router over the skills in this repo.", router)
        self.assertNotIn("`/pr`", router)
        self.assertNotIn("PR.md", router)
        self.assertNotIn("Write a PR body", router)
        for stale in ("skills/pr/", "skills/implement/PR.md", "skills/implement/CREDITS.md", "Dex Horthy"):
            self.assertNotIn(stale, readme)


if __name__ == "__main__":
    unittest.main()

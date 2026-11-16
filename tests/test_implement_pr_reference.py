"""The standalone pr skill is an on-demand implement reference, not a catalog entry."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import repo_skill_catalog  # noqa: E402


MATT = ROOT / "plugins/mattpocock-skills"
IMPLEMENT = MATT / "skills/implement"
ASK_MATT = (MATT / "skills/ask-matt/SKILL.md").read_text(encoding="utf-8")
SKILL = (IMPLEMENT / "SKILL.md").read_text(encoding="utf-8")
REFERENCE = (IMPLEMENT / "PR.md").read_text(encoding="utf-8")
CREDITS = (IMPLEMENT / "CREDITS.md").read_text(encoding="utf-8")
LICENSE = (IMPLEMENT / "LICENSE").read_text(encoding="utf-8")


class ImplementPrReferenceTests(unittest.TestCase):
    def test_standalone_pr_skill_is_absent_from_the_live_catalog(self) -> None:
        catalog = repo_skill_catalog.load_repo_skill_catalog(ROOT)
        names = {source.name for source in catalog.sources}
        matt = {source.name for source in catalog.sources if source.plugin == "mattpocock-skills"}
        self.assertEqual(len(names), 31)
        self.assertEqual(len(matt), 19)
        self.assertNotIn("pr", names)
        self.assertIn("implement", names)
        self.assertIn("ask-matt", names)
        self.assertFalse((MATT / "skills/pr").exists())
        self.assertFalse(REFERENCE.startswith("---"))
        self.assertNotIn("\nname: pr\n", REFERENCE)

    def test_description_of_existing_changes_does_not_rerun_implementation(self) -> None:
        for expected in (
            "asks only for a pull request description",
            "changes that already exist",
            "read [PR.md](PR.md)",
            "then stop",
            "Do not start or re-run implementation or `tdd`",
            "Do not write a pull request description unless the user asked for one",
            "do not re-run implementation or `tdd` to produce the description",
        ):
            self.assertIn(expected, SKILL)
        for expected in (
            "only when the user asks",
            "changes that already exist does not re-run implementation or `tdd`",
            "not a catalog skill",
            "Finishing implementation does not load it by itself",
            "actual diff",
            "rationale",
            "verification evidence",
            "remaining limitations",
        ):
            self.assertIn(expected, REFERENCE)
        self.assertIn("disable-model-invocation: true", SKILL.split("---", 2)[1])

    def test_preparing_text_does_not_authorize_remote_writes(self) -> None:
        self.assertIn(
            "does not authorize pushing, creating or editing a published pull request, merging, or any other remote write",
            SKILL,
        )
        for expected in (
            "does not grant permission to push, create or edit a published PR",
            "upload evidence, mark ready, request reviewers, close issues, merge",
            "any other remote write",
            "Reuse authorization already established",
            "ask only for missing authority",
            "does not require restarting a completed code review",
            "A template's prefilled claim or checked box is not evidence",
            "issue-closing keywords only when that closure is authorized",
            "Do not invent issue links or completion claims",
            "they do not grant authority for external actions",
            "Distinguish committed changes from staged, unstaged, and untracked",
            "Read-only inspection must leave files, index, refs, and remote state unchanged",
            "never manufacture a failing test",
            "a simple revert does not undo deleted data",
            "State unknowns and prerequisites",
            "**Summary**, **Evidence**, and **Merge Danger**",
            "does not create a standing publication task",
        ):
            self.assertIn(expected, REFERENCE)

    def test_source_and_license_travel_with_the_reference(self) -> None:
        self.assertIn("[CREDITS.md](CREDITS.md)", REFERENCE)
        self.assertIn("[LICENSE](LICENSE)", REFERENCE)
        self.assertTrue((IMPLEMENT / "CREDITS.md").is_file())
        self.assertTrue((IMPLEMENT / "LICENSE").is_file())
        self.assertEqual(
            (IMPLEMENT / "CREDITS.md").parent.joinpath("../../LICENSE").resolve(),
            (MATT / "LICENSE").resolve(),
        )
        for expected in (
            "Dex Horthy",
            "HumanLayer",
            "https://github.com/mattpocock/skills/tree/24fe0ef7737efae15c87225755e9f6f5965e4888/skills/engineering/pr",
            "https://github.com/humanlayer/skills/blob/ca7c8088db69e315a8b2deea43820270457f8f3c/plugins/show-me/skills/show-me/SKILL.md",
        ):
            self.assertIn(expected, CREDITS)
        self.assertIn("Copyright (c) 2026 HumanLayer", LICENSE)
        self.assertIn("MIT License", LICENSE)
        readme = (MATT / "README.md").read_text(encoding="utf-8")
        self.assertIn("skills/implement/CREDITS.md", readme)
        self.assertIn("skills/implement/PR.md", readme)
        self.assertNotIn("skills/pr/", readme)

    def test_ask_matt_keeps_its_role_and_routes_pr_writing_to_implement(self) -> None:
        self.assertIn("name: ask-matt", ASK_MATT)
        self.assertIn(
            "Ask which skill or flow fits your situation. A router over the skills in this repo.",
            ASK_MATT,
        )
        self.assertIn(
            "| Write a PR body from changes and verification evidence | `/implement`, reading [PR.md](../implement/PR.md) only |",
            ASK_MATT,
        )
        self.assertNotIn("`/pr`", ASK_MATT)
        linked = (MATT / "skills/ask-matt/SKILL.md").parent.joinpath("../implement/PR.md").resolve()
        self.assertEqual(linked, (IMPLEMENT / "PR.md").resolve())

    def test_live_counts_change_and_release_history_stays(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        plugin = (MATT / "README.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        unreleased, released = changelog.split("## 1.2.0 — 2026-11-14", 1)
        self.assertIn("The default composition contains 31 skills", readme)
        self.assertIn("The current\ncatalog contains 31 skills.", readme)
        self.assertIn("19 engineering skills", plugin)
        self.assertIn("The standalone `pr` skill is no longer a catalog entry.", plugin)
        self.assertIn(
            "| Implement and verify | implement, code-review, tdd, diagnosing-bugs |",
            plugin,
        )
        self.assertIn("The hub catalog is 31 skills, including 19 Matt skills.", unreleased)
        self.assertIn("The hub catalog is 32 skills.", released)
        release = (ROOT / "docs/releases/1.2.0.md").read_text(encoding="utf-8")
        self.assertIn("The hub catalog is 32 skills, including the existing 20 Matt skills.", release)
        adr = (ROOT / "docs/adr/0012-maintain-a-local-mattpocock-selection.md").read_text(encoding="utf-8")
        self.assertIn("Keep 20 locally maintained skills", adr)


if __name__ == "__main__":
    unittest.main()

"""Matt catalog cleanup keeps constraints and drops retired entrypoints."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import repo_skill_catalog  # noqa: E402


MATT = ROOT / "plugins/mattpocock-skills/skills"
DESIGN = MATT / "codebase-design"


class MattSkillCleanupTests(unittest.TestCase):
    def test_catalog_counts_and_retired_entries(self) -> None:
        catalog = repo_skill_catalog.load_repo_skill_catalog(ROOT)
        by_plugin: dict[str, set[str]] = {}
        for source in catalog.sources:
            by_plugin.setdefault(source.plugin, set()).add(source.name)
        self.assertEqual(len(catalog.sources), 30)
        self.assertEqual(len(by_plugin["maintenance"]), 4)
        self.assertEqual(len(by_plugin["workflow"]), 10)
        self.assertEqual(len(by_plugin["mattpocock-skills"]), 16)
        self.assertNotIn("grill-me", by_plugin["mattpocock-skills"])
        self.assertNotIn("improve-codebase-architecture", by_plugin["mattpocock-skills"])
        self.assertIn("grilling", by_plugin["mattpocock-skills"])
        self.assertIn("grill-with-docs", by_plugin["mattpocock-skills"])
        self.assertIn("codebase-design", by_plugin["mattpocock-skills"])
        self.assertFalse((MATT / "grill-me").exists())
        self.assertFalse((MATT / "improve-codebase-architecture").exists())

    def test_grilling_keeps_its_method_and_one_imported_boundary(self) -> None:
        text = (MATT / "grilling/SKILL.md").read_text(encoding="utf-8")
        for kept in (
            "design tree",
            "The **frontier**",
            "A reply settles only the stated decision, not unrelated permissions.",
            "do not add a second blanket confirmation",
            "A request to discuss remains a discussion.",
        ):
            self.assertIn(kept, text)
        self.assertEqual(text.count("A working directory by itself does not call for glossary or ADR writes."), 1)
        self.assertNotIn("grill-me", text)

    def test_architecture_review_is_explicit_and_not_a_vocabulary_load(self) -> None:
        skill = (DESIGN / "SKILL.md").read_text(encoding="utf-8")
        review = (DESIGN / "ARCHITECTURE-REVIEW.md").read_text(encoding="utf-8")
        report = (DESIGN / "HTML-REPORT.md").read_text(encoding="utf-8")
        self.assertIn("does not start that review", skill)
        self.assertIn("ARCHITECTURE-REVIEW.md", skill)
        self.assertIn("does not start this review", review)
        self.assertIn("The review ends as a proposal.", review)
        self.assertIn("does not start implementation", review)
        self.assertIn("not a completion gate", review)
        self.assertIn("real friction", review)
        self.assertIn("[MIT license](LICENSE)", review)
        self.assertEqual((DESIGN / "LICENSE").read_bytes(), (MATT.parent / "LICENSE").read_bytes())
        self.assertIn("<!doctype html>", report)
        self.assertNotIn("disable-model-invocation", skill.split("---", 2)[1])

    def test_compressed_entries_keep_their_constraints(self) -> None:
        docs = (MATT / "grill-with-docs/SKILL.md").read_text(encoding="utf-8")
        spec = (MATT / "to-spec/SKILL.md").read_text(encoding="utf-8")
        implement = (MATT / "implement/SKILL.md").read_text(encoding="utf-8")
        research = (MATT / "research/SKILL.md").read_text(encoding="utf-8")
        writer = (MATT / "writing-for-agents/SKILL.md").read_text(encoding="utf-8")
        handoff = (MATT / "handoff/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: grill-with-docs", docs)
        self.assertIn("disable-model-invocation: true", docs)
        self.assertIn("`grilling`", docs)
        self.assertIn("`domain-modeling`", docs)
        self.assertNotIn("to-spec", docs)
        self.assertIn("do not restart an interview", spec)
        self.assertIn("only when separately authorized", spec)
        self.assertIn("unattended implementation", spec)
        self.assertNotIn("**Problem and outcome:**", spec)
        self.assertIn("does not authorize tracker setup", implement)
        self.assertIn("Record the starting commit", implement)
        self.assertIn("does not review uncommitted work", implement)
        self.assertIn("explicitly requires test-first", implement)
        self.assertIn("without automatically loading `tdd`", implement)
        self.assertIn("Fix actionable findings within scope, verify the fixes", implement)
        self.assertIn("report unresolved findings or verification limits", implement)
        self.assertIn("If staging or committing is authorized, select only verified task changes", implement)
        self.assertNotIn("pull request", implement.lower())
        self.assertNotIn("PR.md", implement)
        self.assertIn("primary sources", research)
        self.assertIn("inference", research)
        self.assertIn("source links", research)
        self.assertIn("existing document owner", research)
        self.assertNotIn("disable-model-invocation", research)
        self.assertIn("description and the procedure in the body", writer)
        self.assertIn("one home", writer)
        self.assertIn("not automatically better", writer)
        self.assertIn("maintenance:skill-compressor", writer)
        self.assertIn("workflow:prompt-strategy-loop", writer)
        self.assertIn("$TMPDIR", handoff)
        self.assertIn("instead of copying them", handoff)
        self.assertIn("Redact secrets", handoff)
        self.assertIn("does not by itself require one", handoff)
        self.assertIn("does not authorize sending it", handoff)

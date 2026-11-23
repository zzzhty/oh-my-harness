"""The necessity gate is a long-running-goal reference, not a callable skill."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
ROOT = WORKFLOW_ROOT.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import repo_skill_catalog  # noqa: E402


LONG_RUNNING_ROOT = WORKFLOW_ROOT / "skills" / "long-running-goal"
NECESSITY_GATE = LONG_RUNNING_ROOT / "references" / "necessity-gate.md"
NOTICE = LONG_RUNNING_ROOT / "references" / "necessity-gate-NOTICE.md"
MILESTONE_GATE = LONG_RUNNING_ROOT / "components" / "milestone-scope-gate.md"
EXECUTE = LONG_RUNNING_ROOT / "references" / "execute-and-close.md"


class NecessityGateTests(unittest.TestCase):
    def test_scope_discipline_is_not_a_callable_skill(self) -> None:
        catalog = repo_skill_catalog.load_repo_skill_catalog(ROOT)
        names = {source.name for source in catalog.sources}
        workflow = {source.name for source in catalog.sources if source.plugin == "workflow"}
        self.assertNotIn("scope-discipline", names)
        self.assertEqual(len(workflow), 9)
        self.assertFalse((WORKFLOW_ROOT / "skills" / "scope-discipline").exists())
        readme = (WORKFLOW_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("`scope-discipline` is not a catalog entry", readme)
        self.assertIn("necessity-gate.md", readme)
        self.assertNotIn("- `scope-discipline`:", readme)

    def test_shared_necessity_gate_routes_expansion_without_fixed_budgets(self) -> None:
        gate = NECESSITY_GATE.read_text(encoding="utf-8")

        for semantic in (
            "already requested or authorized",
            "necessary consequence",
            "reachable code, data, caller, test, deployment state",
            "Would omitting it",
            "Later-stage or separately owned work",
            "Speculative expansion",
            "Semantic conflict",
            "Do not use fixed limits on files, lines, tests, tool calls, agents, or elapsed time",
            "Do not repeat a search, test, review, or audit with no new oracle",
        ):
            self.assertIn(semantic, gate)
        self.assertIn("necessity-gate-NOTICE.md", gate)

    def test_long_running_goal_uses_a_stage_adapter_without_duplicating_goal_fields(self) -> None:
        skill = (LONG_RUNNING_ROOT / "SKILL.md").read_text(encoding="utf-8")
        execute = EXECUTE.read_text(encoding="utf-8")
        component = MILESTONE_GATE.read_text(encoding="utf-8")
        atomic_template = (
            LONG_RUNNING_ROOT / "templates" / "long_running_goal_template.md"
        ).read_text(encoding="utf-8")
        sequence_template = (
            LONG_RUNNING_ROOT / "templates" / "long_running_goal_sequence_template.md"
        ).read_text(encoding="utf-8")

        self.assertIn("components/milestone-scope-gate.md", skill)
        self.assertIn("At each milestone entry", execute)
        self.assertIn("before material scope or validation expansion", execute)
        self.assertIn("milestone-scope exit gate", execute)
        self.assertLess(
            execute.index("Apply `../components/checkpoint.md`"),
            execute.index("Confirm the milestone-scope exit gate"),
        )
        self.assertIn("../references/necessity-gate.md", component)
        self.assertNotIn("scope-discipline", component)
        self.assertIn(
            "The checkpoint component has already recorded its evidence",
            component,
        )
        self.assertIn("later milestone work", component)
        self.assertIn("without another final scope audit", component)
        self.assertNotIn("## Decision Routing", component)

        self.assertIn("components/milestone-scope-gate.md", atomic_template)
        self.assertIn("components/milestone-scope-gate.md", sequence_template)
        for text in (atomic_template, sequence_template):
            self.assertNotIn("Scope budget", text)
            self.assertNotIn("Validation budget", text)
            self.assertNotIn("Maximum tool count", text)

    def test_third_party_design_attribution_is_preserved(self) -> None:
        notice = NOTICE.read_text(encoding="utf-8")

        self.assertIn("Stop That Shit", notice)
        self.assertIn("MIT License", notice)
        self.assertIn("Copyright (c) 2026 Stop That Shit contributors", notice)


if __name__ == "__main__":
    unittest.main()

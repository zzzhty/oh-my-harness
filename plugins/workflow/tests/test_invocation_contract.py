from __future__ import annotations

import unittest
from pathlib import Path


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = WORKFLOW_ROOT.parents[1]
ORCHESTRATE_ROOT = WORKFLOW_ROOT / "skills" / "orchestrate-subagents"
SUMMARY_ROOT = WORKFLOW_ROOT / "skills" / "summary-in-html"
SOP_ROOT = WORKFLOW_ROOT / "skills" / "sop"
PROMPT_STRATEGY_ROOT = WORKFLOW_ROOT / "skills" / "prompt-strategy-loop"


def skill_description(skill_file: Path) -> str:
    for line in skill_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError(f"description missing: {skill_file}")


class InvocationContractTests(unittest.TestCase):
    def test_summary_trigger_covers_reference_and_source_walkthrough_modes(self) -> None:
        description = skill_description(SUMMARY_ROOT / "SKILL.md")
        metadata = (SUMMARY_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")

        self.assertIn("developer reference", description)
        self.assertIn("source-code walkthrough", description)
        self.assertIn("step-by-step code handoffs", description)
        self.assertIn("real entry points", description)
        self.assertIn("summaries and source-code walkthroughs", metadata)
        self.assertIn("summary or entry-first source-code walkthrough", metadata)

    def test_orchestrate_trigger_is_scoped_to_user_requested_subagents(self) -> None:
        description = skill_description(ORCHESTRATE_ROOT / "SKILL.md")
        metadata = (ORCHESTRATE_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")

        self.assertIn("explicitly asks", description)
        self.assertIn("subagents", description)
        self.assertIn("parallel agents", description)
        self.assertIn("tool availability", description)
        self.assertNotIn("PR review", description)
        self.assertNotIn("architecture review", description)
        self.assertNotIn("debugging", description)
        self.assertNotIn("migration", description)
        self.assertNotIn("allow_implicit_invocation: false", metadata)
        self.assertIn("user-requested Codex subagents", metadata)
        self.assertIn("task_name assignments", metadata)
        self.assertIn("prompt-declared permissions", metadata)

    def test_summary_document_types_have_distinct_authoring_routes(self) -> None:
        skill = (SUMMARY_ROOT / "SKILL.md").read_text(encoding="utf-8")
        common = skill.split("## Common Evidence Inventory", 1)[1].split(
            "## Document-Type Routing", 1
        )[0]
        routing = skill.split("## Document-Type Routing", 1)[1].split(
            "## Shared Artifact Steps", 1
        )[0]
        summary_route = next(
            line for line in routing.splitlines() if "For every `summary`" in line
        )
        walkthrough_route = next(
            line for line in routing.splitlines() if "For `source_walkthrough`" in line
        )

        self.assertIn("collect_summary_inputs.py", common)
        self.assertIn("source-of-truth status", common)
        self.assertNotIn("chapter_contract.md", common)
        self.assertNotIn("source_walkthrough_contract.md", common)
        self.assertNotIn("complete caller", common)

        self.assertIn("references/chapter_contract.md", summary_route)
        self.assertIn("every `summary`", summary_route)
        self.assertNotIn("source_walkthrough_contract.md", summary_route)

        self.assertIn("references/source_walkthrough_contract.md", walkthrough_route)
        self.assertIn("complete caller, handoff, and return route", walkthrough_route)
        self.assertNotIn("chapter_contract.md", walkthrough_route)

    def test_prompt_strategy_uses_authorized_evaluators_without_cross_invocation(self) -> None:
        prompt_strategy = (
            WORKFLOW_ROOT / "skills" / "prompt-strategy-loop" / "SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertIn("active environment or plan authorizes delegation", prompt_strategy)
        self.assertIn("does not invoke `orchestrate-subagents`", prompt_strategy)
        self.assertNotIn("current environment exposes subagent tools", prompt_strategy)

    def test_companion_skills_only_suggest_explicit_long_running_task(self) -> None:
        for skill_file in (
            SOP_ROOT / "SKILL.md",
            PROMPT_STRATEGY_ROOT / "SKILL.md",
        ):
            with self.subTest(skill_file=skill_file):
                text = skill_file.read_text(encoding="utf-8")
                self.assertIn("suggest `long-running-task`", text)
                self.assertIn("wait for explicit user confirmation", text)
                self.assertNotIn("Use `long-running-task` when", text)
                self.assertIn("brief checkpoint to continue across turns", text)
                self.assertIn("Direct execution is the default", text)
                self.assertIn("native `/goal` only if the user explicitly selects it and the host supports it", text)
                for stale in ("staged milestones", "multi-milestone objective", "close/archive lifecycle"):
                    self.assertNotIn(stale, text)

    def test_sop_execute_branch_requires_ready_gate_before_actions(self) -> None:
        skill = (SOP_ROOT / "SKILL.md").read_text(encoding="utf-8")
        execute = skill.split("## Execute", 1)[1].split("## Completion", 1)[0]

        gate = execute.index("check_sop_ready.py <sop-file>")
        first_action = execute.index("Follow the declared steps")
        self.assertLess(gate, first_action)
        self.assertIn("without `--allow-draft`", execute)
        self.assertIn("confirm the top-level status is `Ready`", execute)
        self.assertIn("If the SOP is `Draft` or the check fails, do not execute it", execute)

        modes = skill.split("## Select The Mode", 1)[1].split("## Create Or Update", 1)[0]
        explain = modes.split("**Explain:**", 1)[1].split("**Dry-run:**", 1)[0]
        preview = modes.split("**Dry-run:**", 1)[1].split("**Execute:**", 1)[0]
        self.assertIn("unfinished `Draft`", explain)
        self.assertIn("without running its steps", explain)
        self.assertIn("authorized, non-mutating inspection", preview)
        self.assertIn("inspecting their actual behavior and permissions", preview)
        self.assertIn("Draft may be previewed but cannot authorize execution", preview)
        update = skill.split("## Create Or Update", 1)[1].split("## Execute", 1)[0]
        self.assertIn("Update an existing SOP in place, preserving unrelated content", update)

    def test_broad_review_authority_and_orchestration_invocation_are_separate(self) -> None:
        global_guidance = (
            REPO_ROOT / "agents" / "global-instructions.md"
        ).read_text(encoding="utf-8")
        support_note = (REPO_ROOT / "agents" / "operating-principles.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Broad read-only review requests", global_guidance)
        self.assertIn("does not invoke `$orchestrate-subagents`", global_guidance)
        self.assertIn("`agents/global-instructions.md` owns global authority", support_note)
        self.assertIn("does not invoke `$orchestrate-subagents` by itself", support_note)


if __name__ == "__main__":
    unittest.main()

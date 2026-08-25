from __future__ import annotations

import json
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "long-running-goal"
SKILL = SKILL_DIR / "SKILL.md"
REFERENCES = {
    "create": SKILL_DIR / "references" / "create-and-loop.md",
    "sequence": SKILL_DIR / "references" / "sequence-child-goals.md",
    "cutover": SKILL_DIR / "references" / "production-cutover.md",
    "execute": SKILL_DIR / "references" / "execute-and-close.md",
}
PREFLIGHT = SKILL_DIR / "components" / "planning-preflight.md"
ATOMIC_TEMPLATE = SKILL_DIR / "templates" / "long_running_goal_template.md"
SEQUENCE_TEMPLATE = SKILL_DIR / "templates" / "long_running_goal_sequence_template.md"
WATCHER = SKILL_DIR.parents[1] / ".codex-plugin" / "skill-watcher.json"


class LongRunningGoalDisclosureTests(unittest.TestCase):
    def test_entry_interface_keeps_lifecycle_authority_and_goal_tool_contracts(self) -> None:
        text = SKILL.read_text(encoding="utf-8")

        for semantic in (
            "A `Ready` goal",
            "Keep the goal `Draft`",
            "complete `Draft` or `Ready` contract",
            "only when the user explicitly requests a long-running goal",
            "is not itself a trigger",
            "Use system planning for ordinary complex work",
            "wait for the user's confirmation before creating or converting",
            "Never invent or infer a missing decision",
            "An explicit pause, stop, redirect, or change-scope request overrides",
            "without running milestone commands, editing goal evidence, or updating native goal-tool status",
            "Only a `Ready` goal pre-approves",
            "normally after at least three attempts or three distinct approaches",
            "Stop only at a runtime hard stop",
            "Task temporary cache housekeeping is separate",
            "Use the harness's native goal tools only when the user explicitly asks",
            "check_goal_ready.py [--allow-draft] <goal-file>",
            "non-executable `Draft` that records known facts and open decisions",
        ):
            self.assertIn(semantic, text)

    def test_each_conditional_branch_has_a_strong_pointer_and_completion_criterion(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")

        for relative_path in (
            "references/create-and-loop.md",
            "references/sequence-child-goals.md",
            "references/production-cutover.md",
            "references/execute-and-close.md",
        ):
            self.assertIn(relative_path, skill)
        for trigger in (
            "create or upgrade",
            "Loop-shaped",
            "Sequence Child Goals",
            "production cutover",
            "execute, resume, continue, advance, evolve, or close",
        ):
            self.assertIn(trigger, skill)
        for reference in REFERENCES.values():
            text = reference.read_text(encoding="utf-8")
            self.assertIn("Completion criterion:", text)

        create = REFERENCES["create"].read_text(encoding="utf-8")
        self.assertIn("Trigger:", create)
        self.assertIn("Connector read/write boundaries:", create)
        execute = REFERENCES["execute"].read_text(encoding="utf-8")
        self.assertIn("Apply `../components/checkpoint.md`", execute)
        self.assertIn("Remove closed goals from active navigation", execute)
        cutover = REFERENCES["cutover"].read_text(encoding="utf-8")
        self.assertIn("default/full-shadow/production comparison matrix", cutover)

    def test_sequence_branch_discloses_canonical_contract_and_aliases(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        reference = REFERENCES["sequence"].read_text(encoding="utf-8")
        template = SEQUENCE_TEMPLATE.read_text(encoding="utf-8")
        watcher = json.loads(WATCHER.read_text(encoding="utf-8"))

        self.assertIn(
            "scripts/check_goal_sequence.py <sequence-file> [--allow-draft]",
            skill,
        )
        self.assertIn("Long-Running Goal Sequence", reference)
        self.assertIn("one active harness system goal", reference)
        self.assertIn("Completion criterion:", reference)
        self.assertIn("Done / grill-with-docs", reference)
        self.assertIn("never returns to `Ready` for a per-child authorization", reference)

        self.assertIn("Promotion policy: `automatic-after-close`", template)
        self.assertIn("## Child Preflight Register", template)
        self.assertIn("| Child ID | Marker | Status | Source |", template)
        self.assertIn("## Child Execution Register", template)
        self.assertIn(
            "| Order | Child ID | Parent milestone | Live goal | Closeout evidence | Depends on | State | Current milestone | Close revision |",
            template,
        )
        self.assertIn("sole current-state authority", template)
        self.assertIn("transition evidence historical", template)
        resume = template.split("## Reusable Resume Prompt", 1)[1].split(
            "## Related Documents", 1
        )[0]
        self.assertIn("Child Execution Register", resume)
        self.assertNotIn("<child-a>", resume)
        self.assertNotIn("<child-b>", resume)

        aliases = {
            item["value"]
            for item in watcher["skills"]["workflow:long-running-goal"]["aliases"]
        }
        self.assertIn("long-running goal sequence", aliases)
        self.assertIn("umbrella long-running goal", aliases)

    def test_task_temporary_cache_policy_is_explicit_cross_platform_and_bounded(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        preflight = PREFLIGHT.read_text(encoding="utf-8")
        execute = REFERENCES["execute"].read_text(encoding="utf-8")
        sequence = REFERENCES["sequence"].read_text(encoding="utf-8")
        atomic_template = ATOMIC_TEMPLATE.read_text(encoding="utf-8")
        sequence_template = SEQUENCE_TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("Task temporary cache housekeeping is separate", skill)
        self.assertIn("Close housekeeping policy", preflight)
        self.assertIn("host platform or runtime's standard temporary-directory resolver", preflight)
        self.assertIn("Skipping `grill-with-docs` does not skip this choice", preflight)
        self.assertIn("not unconditional recursive deletion", preflight)
        self.assertIn("If `watcher:housekeeping` is unavailable", execute)
        self.assertIn("Before any command may write task-temporary data", execute)
        self.assertIn("bind every task-temporary producer", execute)
        self.assertIn("missing legacy field", execute)
        self.assertIn("never inherits, widens, or overrides a child's policy", sequence)

        for template in (atomic_template, sequence_template):
            self.assertIn("## Task Temporary Cache / Housekeeping", template)
            self.assertIn("Close housekeeping policy", template)
            self.assertIn("Housekeeping decision source", template)
            self.assertIn("Task temporary cache root strategy", template)
            self.assertIn("Recorded task temporary cache roots", template)
            self.assertIn("Housekeeping boundary", template)
            self.assertIn("watcher:housekeeping", template)

        self.assertIn("every child records and honors its own policy", sequence_template)
        self.assertNotIn("| Housekeeping |", sequence_template)

    def test_planning_preflight_inherits_grilling_frontier_rounds(self) -> None:
        preflight = PREFLIGHT.read_text(encoding="utf-8")

        self.assertIn("rounds/frontier cadence owned by `grilling`", preflight)
        self.assertIn("whole currently unblocked frontier", preflight)
        self.assertIn("number every question", preflight)
        self.assertIn("recommended answer for each", preflight)
        self.assertIn("Wait for the user's batch answers, then recompute the frontier", preflight)
        self.assertIn("depend on unresolved answers belong to a later round", preflight)
        self.assertNotIn("Ask one unresolved design question at a time", preflight)

    def test_preflight_time_assessment_is_timeboxed_and_disclosed(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        preflight = PREFLIGHT.read_text(encoding="utf-8")
        create = REFERENCES["create"].read_text(encoding="utf-8")
        sequence = REFERENCES["sequence"].read_text(encoding="utf-8")
        execute = REFERENCES["execute"].read_text(encoding="utf-8")
        templates = (
            ATOMIC_TEMPLATE.read_text(encoding="utf-8"),
            SEQUENCE_TEMPLATE.read_text(encoding="utf-8"),
        )

        self.assertIn("timeboxed execution-time assessment", skill)
        self.assertIn("rough remaining elapsed-time range", skill)
        self.assertIn("apply `components/planning-preflight.md`", skill)
        self.assertIn("## Preflight Time Assessment", preflight)
        self.assertIn("Timebox the assessment", preflight)
        self.assertIn("Not quickly estimable", preflight)
        self.assertIn("Completion criterion:", preflight)
        self.assertIn("reported to the user", preflight)
        self.assertIn("external-wait and serial/parallel assumptions", preflight)
        self.assertIn("time assessment satisfying", create)
        self.assertIn("evidence rebaseline without rerunning the grill", execute)
        self.assertIn("when resuming after an interruption or milestone transition", execute)
        self.assertIn("range overrun is a timing rebaseline and non-stop", execute)
        self.assertIn("never in either canonical register", sequence)
        self.assertIn("only when every child has one", sequence)

        for template in templates:
            self.assertIn("## Preflight Time Assessment", template)
            self.assertIn("Assessment target", template)
            self.assertIn("Assessment mode", template)
            self.assertIn("Rough elapsed-time estimate", template)
            self.assertIn("Basis or blocker", template)
            self.assertIn("Critical-path time-cost distribution", template)

        sequence_template = templates[1]
        self.assertIn("never in either canonical register", sequence_template)
        self.assertNotIn("| Timing |", sequence_template)


if __name__ == "__main__":
    unittest.main()

"""Static recovery-contract guards and document-validator integration.

These checks do not run a model or observe native Goal failure counting.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GOAL = ROOT / "skills" / "long-running-goal"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "ready_goal.md"


class GoalFailureRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = (GOAL / "SKILL.md").read_text(encoding="utf-8")
        cls.execute = (GOAL / "references" / "execute-and-close.md").read_text(encoding="utf-8")
        cls.recovery = cls.execute.split("## Failure Recovery", 1)[1].split(
            "## Contract Evolution", 1
        )[0]
        cls.atomic = (GOAL / "templates" / "long_running_goal_template.md").read_text(encoding="utf-8")
        cls.sequence = (GOAL / "templates" / "long_running_goal_sequence_template.md").read_text(encoding="utf-8")
        cls.handoff = (GOAL / "references" / "sequence-child-goals.md").read_text(encoding="utf-8")

    def test_deterministic_failure_changes_next_step_before_native_exhaustion(self) -> None:
        for text in (self.skill, self.recovery, self.sequence):
            with self.subTest(surface=text[:60]):
                self.assertRegex(text, r"first or second Goal failure")
                self.assertRegex(text, r"(?:immediately|immediate strategy adjustment)")
        self.assertRegex(self.recovery, r"deterministic failure.*unchanged path")
        self.assertRegex(self.recovery, r"do not repeat it without new evidence")
        self.assertIn("test a different causal hypothesis", self.recovery)
        self.assertIn("record it as unknown", self.recovery)
        self.assertIn("still improve the next step after every failure", self.recovery)
        self.assertNotIn("at least three attempts", self.skill)
        self.assertNotIn("至少三次或三种方式", self.atomic)

    def test_repair_reruns_same_validation_and_unchanged_retry_needs_evidence(self) -> None:
        self.assertRegex(self.recovery, r"After a repair, rerun the same required validation")
        self.assertIn("the implementation changed", self.recovery)
        self.assertRegex(
            self.recovery,
            r"unchanged retry.*only by evidence of a transient fault or a changed prerequisite",
        )
        self.assertIn("stop repeating if it no longer supports a useful next step", self.recovery)
        self.assertIn("修复后可重跑同一必需测试", self.atomic)
        self.assertIn("原样重试仅限有证据的瞬时故障或前置条件变化", self.atomic)

    def test_native_third_failure_stops_even_with_another_approach(self) -> None:
        self.assertIn("The third native Codex Goal failure", self.skill)
        self.assertIn("even if another useful approach exists", self.skill)
        self.assertIn("do not initiate a fourth native attempt", self.skill)
        self.assertIn("recreate/replace a Goal to evade a stop or reset its failures", self.skill)
        self.assertIn("resume automatically", self.recovery)
        self.assertIn("native hard stop with no visible count", self.recovery)
        self.assertIn("stops active parent Goal execution", self.sequence)
        self.assertIn("no automatic fourth native attempt", self.sequence)
        self.assertIn("do not promote a child", self.handoff.lower())
        self.assertIn("create a child native Goal", self.handoff)
        self.assertIn("原生第三次失败或 hard stop 立即停止 Goal", self.atomic)

    def test_command_failures_and_unknown_feedback_do_not_manufacture_counts(self) -> None:
        self.assertIn("Ordinary test or diagnostic command failures do not establish", self.skill)
        self.assertIn("a nonzero command exit does not establish a native Goal failure", self.recovery)
        self.assertIn("Use only a count explicitly supplied by native feedback", self.recovery)
        self.assertIn("otherwise record it as unknown", self.recovery)
        self.assertIn("Do not infer, increment, or maintain a custom runtime counter", self.recovery)
        self.assertIn("do not implement platform counting", self.skill)
        self.assertIn("not verified which events", self.skill)
        self.assertIn("how reset works", self.skill)
        self.assertIn("unknown counts stay unknown", self.handoff)
        self.assertIn("不自建运行时计数器", self.atomic)

    def test_permission_stop_and_equivalent_methods_preserve_all_boundaries(self) -> None:
        self.assertIn("immediately at any stage", self.skill)
        self.assertIn("never wait for a failure threshold", self.skill)
        self.assertIn("Independent authorized work may continue", self.recovery)
        self.assertIn("outside the stopped Goal", self.recovery)
        for text in (self.recovery, self.sequence):
            with self.subTest(surface=text[:60]):
                self.assertIn("existing authorization", text)
                self.assertIn("required methods and gates", text)
                self.assertIn("frozen semantics", text)
                self.assertIn("unchanged acceptance criteria", text)
        self.assertIn("Do not switch routes to evade an authorization or required-method failure", self.recovery)
        self.assertIn("Equivalent fallback or alternate methods are allowed only", self.sequence)
        self.assertNotIn("Do not widen gates, hide failure, use fallback or alternate backends", self.sequence)
        self.assertIn("concrete recovery condition", self.recovery)
        self.assertIn("rather than loop indefinitely", self.recovery)

    def test_failure_routes_load_protocol_without_unconditional_continuation(self) -> None:
        self.assertIn("references/execute-and-close.md#failure-recovery", self.skill)
        self.assertIn("After any failure, apply [Failure Recovery]", self.execute)
        self.assertIn("execute-and-close.md#failure-recovery", self.handoff)
        self.assertIn("Failure Recovery", self.atomic)
        self.assertIn("Failure Recovery", self.sequence)
        self.assertIn("no native hard stop applies", self.execute)
        self.assertNotIn("block only at the recorded hard-stop threshold", self.skill)

    def run_ready_checker(self, text: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="omh-recovery-contract-") as temporary:
            document = Path(temporary) / "goal.md"
            document.write_text(text, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(GOAL / "scripts" / "check_goal_ready.py"), str(document)],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_readiness_accepts_recovery_without_treating_command_failures_as_stops(self) -> None:
        fixture = FIXTURE.read_text(encoding="utf-8")
        scenarios = (
            "A deterministic test failed. Repair the cause or change the causal hypothesis before retrying.",
            "After repairing code, rerun the same required test with unchanged acceptance criteria.",
            "A transient service fault has new availability evidence; retry within existing authorization.",
            "Native count is unknown. Record unknown and improve the next step after every failure.",
        )
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                result = self.run_ready_checker(
                    fixture + "\n## Recovery scenario\n\n" + scenario + "\n\n" + self.recovery
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_readiness_accepts_recorded_native_stop_without_a_retry_engine(self) -> None:
        fixture = FIXTURE.read_text(encoding="utf-8").replace(
            "Overall status: Ready", "Overall status: In Progress"
        ).replace(
            "| M0 | Ready | Pending | Pending |", "| M0 | Blocked | Failed | Pending |"
        ).replace(
            "Baseline recorded.",
            "Runtime hard-stop evidence: 2026-10-08 demo: native feedback identifies "
            "the third Codex Goal failure. Stop active Goal execution; another implementation "
            "path exists but does not authorize a fourth native attempt or Goal recreation.",
        )
        result = self.run_ready_checker(fixture + "\n## Failure Recovery\n" + self.recovery)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

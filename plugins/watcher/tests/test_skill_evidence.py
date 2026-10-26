from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from watcher_runtime.skill.codex_hook_adapter import normalize_hook_payload, write_hook_event
from watcher_runtime.skill.report_pipeline import (
    ReportQuery, ReportOutputPolicy, generate_report, evidence_rows, count_task_outcomes,
)


class SkillEvidenceTests(unittest.TestCase):
    def test_text_counterexamples_never_choose_primary_or_confirm_execution(self):
        for text in (
            "Frequency table: tdd 90, code-review 50, diagnosing-bugs 30",
            '> Old conversation: "I will use tdd and code-review."',
            "I did not execute tdd or code-review; do not use them.",
            "Compare tdd versus code-review for a future task.",
            "Use $tdd for this task.",
        ):
            for hook, field in (("UserPromptSubmit", "prompt"), ("Stop", "last_assistant_message")):
                with self.subTest(text=text, hook=hook):
                    event = normalize_hook_payload({"hook_event_name": hook, field: text}, repo_root=REPO_ROOT)
                    attribution = event["skill_attribution"]
                    self.assertIsNone(attribution["primary"])
                    self.assertTrue(attribution["mentioned"])
                    self.assertEqual(attribution["effective"], [])
                    self.assertEqual(attribution["supporting"], [])
                    self.assertEqual(attribution["execution_status"], "unknown")

    def test_structured_selection_and_manifest_are_not_loading(self):
        event = normalize_hook_payload({
            "hook_event_name": "UserPromptSubmit", "skill_name": "mattpocock-skills:implement",
            "prompt": "Do this task with token sk-syntheticsecret1234567890",
        }, repo_root=REPO_ROOT)
        attribution = event["skill_attribution"]
        self.assertEqual(attribution["primary"]["source"], "provided")
        self.assertEqual(attribution["execution_status"], "unknown")
        self.assertEqual(attribution["supporting"][0]["source"], "manifest_dependency")
        self.assertEqual(event["outcome"], "unknown")
        self.assertIn("user_skill_context", event["codex"])
        self.assertNotIn("sk-syntheticsecret1234567890", json.dumps(event))

    def test_tool_response_text_is_not_failure_evidence(self):
        for response, outcome in (
            ("error exception traceback exited with code 1", "unknown"),
            ({"exit_code": 0, "stdout": "error exception traceback"}, "success"),
            ({"content": [{"text": '{"error": true, "exit_code": 1}'}]}, "unknown"),
            ({"data": {"error": "quoted documentation"}}, "unknown"),
            ({"exit_code": 1, "stderr": "failed"}, "failure"),
            ({"isError": True, "content": []}, "failure"),
            ({"status_code": 200}, "unknown"),
        ):
            with self.subTest(response=response):
                event = normalize_hook_payload({"hook_event_name": "PostToolUse", "tool_response": response}, repo_root=REPO_ROOT)
                self.assertEqual(event["outcome"], outcome)

    def test_lifecycle_retains_selection_and_mentions_without_execution_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            base = {"session_id": "synthetic", "turn_id": "one"}
            def emit(hook, **fields):
                return write_hook_event({**base, "hook_event_name": hook, **fields}, state_dir=state, repo_root=REPO_ROOT)
            emit("SessionStart")
            emit("UserPromptSubmit", skill_name="mattpocock-skills:tdd", prompt="Use tdd")
            emit("PostToolUse", tool_name="Bash", tool_response={"exit_code": 1})
            event = emit("Stop", last_assistant_message="Compare code-review and tdd; error is quoted.")
            self.assertEqual(event["skill_attribution"]["primary"]["name"], "mattpocock-skills:tdd")
            self.assertEqual({item["name"] for item in event["skill_attribution"]["mentioned"]}, {"mattpocock-skills:tdd", "mattpocock-skills:code-review"})
            self.assertEqual(event["task_outcome"], "unknown")
            self.assertEqual(event["codex"]["turn_summary"]["tool_failure_count"], 1)
            self.assertEqual(event["skill_attribution"]["execution_status"], "unknown")
            self.assertFalse((state / "turns" / "synthetic.json").exists())

    def test_alias_projection_dedup_and_unknown_outcomes_leave_logs_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            log = state / "events.jsonl"
            event = {
                "event_type": "turn_summary", "timestamp": "2026-10-01T00:00:00Z",
                "event_id": "one", "session_id": "synthetic", "codex": {"turn_id": "one"},
                "outcome": "failure",
                "skill_attribution": {
                    "primary": {"name": "old:entry", "source": "assistant_announcement"},
                    "supporting": [{"name": "demo:support", "source": "manifest_dependency"}],
                    "effective": ["old:entry", "demo:support"],
                    "mentioned": [{"name": "retired:unmapped", "source": "prompt_mention"}],
                },
            }
            duplicate = copy.deepcopy(event)
            duplicate["event_id"] = "same-turn-second-record"
            data = "\n".join(json.dumps(item) for item in (event, event, duplicate)) + "\n"
            log.write_text(data)
            (state / "skill-metadata-cache.json").write_text(json.dumps({
                "schema_version": 2, "skills": {"demo:entry": {"logical_group": "explicit-workflows"}},
                "legacy_names": {"old:entry": "demo:entry"},
            }))
            result = generate_report(ReportQuery(state_dir=state, log_file=log, skill="demo:entry"), ReportOutputPolicy())
            self.assertEqual(result.event_count, 2)
            self.assertEqual(result.outcome_counts, {"unknown": 1})
            self.assertIn("`old:entry`", result.report)
            self.assertIn("`demo:entry`", result.report)
            self.assertIn("`retired:unmapped`", result.report)
            self.assertIn("assistant_announcement", result.report)
            self.assertIn("historical trigger policy", result.report)
            self.assertIn("execution is unknown", result.report)
            self.assertNotIn("%", result.report)
            self.assertNotIn("Usage By", result.report)
            self.assertNotIn("active", result.report)
            self.assertEqual(log.read_text(), data)
            alias_result = generate_report(ReportQuery(state_dir=state, log_file=log, skill="old:entry"), ReportOutputPolicy())
            self.assertEqual(alias_result.event_count, result.event_count)

    def test_aliases_and_multiple_mentions_share_one_turn_key(self):
        event = {
            "event_type": "turn_summary", "session_id": "s", "codex": {"turn_id": "t"},
            "skill_attribution": {
                "primary": {"name": "new:entry", "source": "provided"},
                "supporting": [{"name": "old:entry", "source": "manifest_dependency"}],
                "mentioned": [
                    {"name": "old:entry", "source": "prompt_mention"},
                    {"name": "new:entry", "source": "assistant_announcement"},
                ],
            },
        }
        original = copy.deepcopy(event)
        rows = evidence_rows([event, event], {"new:entry": "implicit-primitives"}, {"old:entry": "new:entry"})
        self.assertEqual(len(rows), 1)
        for key in ("observed_turns", "selection_turns", "mention_turns", "dependency_turns"):
            self.assertEqual(rows[0][key], 1)
        self.assertEqual(rows[0]["raw_identities"], ["new:entry", "old:entry"])
        self.assertEqual(event, original)

    def test_legacy_single_identity_is_unclassified_and_unknown_is_not_overridden(self):
        event = {"event_type": "turn_summary", "event_id": "old", "skill_name": "old:entry", "outcome": "success"}
        rows = evidence_rows([event], legacy_names={"old:entry": "new:entry"})
        self.assertEqual(rows[0]["skill"], "new:entry")
        self.assertEqual(rows[0]["unclassified_turns"], 1)
        self.assertEqual(count_task_outcomes([event]), {"unknown": 1})
        event.update(task_outcome="success", codex={"turn_summary": {"task_outcome": "unknown"}})
        self.assertEqual(count_task_outcomes([event]), {"unknown": 1})

    def test_incremental_overlap_reuses_hashes_without_changing_raw_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            log = state / "events.jsonl"
            start = datetime(2026, 10, 1, tzinfo=timezone.utc)
            def event(turn, timestamp):
                return {
                    "event_type": "turn_summary", "timestamp": timestamp.isoformat(),
                    "session_id": "s", "codex": {"turn_id": turn}, "task_outcome": "unknown",
                    "skill_attribution": {"mentioned": [{"name": "demo", "source": "prompt_mention"}]},
                }
            original = json.dumps(event("one", start)) + "\n"
            log.write_text(original + original)
            query = ReportQuery(state_dir=state, log_file=log, incremental=True)
            output = ReportOutputPolicy(output=state / "report.md")
            with mock.patch("watcher_runtime.skill.report_pipeline.utc_now", return_value=start + timedelta(minutes=1)):
                first = generate_report(query, output)
                repeated = generate_report(query, output)
            self.assertEqual(first.event_count, 1)
            self.assertEqual(first.outcome_counts, {"unknown": 1})
            self.assertEqual(repeated.event_count, 0)
            self.assertEqual(repeated.outcome_counts, {})
            late = json.dumps(event("late", start + timedelta(seconds=30))) + "\n"
            with log.open("a") as handle:
                handle.write(late)
            with mock.patch("watcher_runtime.skill.report_pipeline.utc_now", return_value=start + timedelta(minutes=2)):
                result = generate_report(query, output)
            self.assertEqual(result.event_count, 1)
            self.assertEqual(result.events[0]["codex"]["turn_id"], "late")
            self.assertEqual(log.read_text(), original + original + late)

    def test_mentions_preserve_summary_privacy_and_do_not_capture_unrelated_turns(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            base = {"session_id": "privacy", "turn_id": "one"}
            def emit(hook, **fields):
                return write_hook_event({**base, "hook_event_name": hook, **fields}, state_dir=state, repo_root=REPO_ROOT)
            emit("SessionStart")
            prompt = "Compare tdd and code-review. " + "private synthetic detail " * 60 + "sk-testsecret123456789"
            emitted = emit("UserPromptSubmit", prompt=prompt)
            self.assertNotIn("user_skill_context", emitted["codex"])
            emit("Stop", last_assistant_message="No skills were executed.")
            base["turn_id"] = "two"
            emit("UserPromptSubmit", prompt="An unrelated ordinary request")
            emit("Stop", last_assistant_message="Done")
            raw = (state / "logs" / "events.jsonl").read_text()
            self.assertEqual(len(raw.splitlines()), 2)
            self.assertNotIn(prompt, raw)
            self.assertNotIn("sk-testsecret123456789", raw)
            self.assertNotIn("An unrelated ordinary request", raw)


if __name__ == "__main__":
    unittest.main()

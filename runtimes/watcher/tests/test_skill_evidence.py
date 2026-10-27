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

from watcher_runtime.skill.report_pipeline import (
    ReportQuery, ReportOutputPolicy, generate_report, evidence_rows, count_task_outcomes,
)


class SkillEvidenceTests(unittest.TestCase):




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



if __name__ == "__main__":
    unittest.main()

"""Check the shipped prompt contract; host/model compliance is separate."""
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1]
TASK = WORKFLOW / "skills" / "long-running-task"


class LongRunningTaskContractTests(unittest.TestCase):
    def setUp(self):
        self.skill = (TASK / "SKILL.md").read_text(encoding="utf-8")
        self.handoff = (TASK / "references" / "host-handoff.md").read_text(encoding="utf-8")

    def test_retired_goal_adrs_only_point_to_the_current_decision(self):
        repo = WORKFLOW.parents[1]
        adr = repo / "docs" / "adr"
        current = "0038-use-native-goals-for-long-running-tasks.md"
        for number in ("0013", "0014", "0019"):
            with self.subTest(adr=number):
                (old,) = adr.glob(f"{number}-*.md")
                lines = old.read_text(encoding="utf-8").strip().splitlines()
                self.assertEqual(len(lines), 3)
                self.assertIn(f"]({current})", lines[2])
        self.assertIn("`long-running-task`", (adr / current).read_text(encoding="utf-8"))
        for entry in (repo / "README.md", WORKFLOW / "README.md",
                      repo / "docs" / "todo" / "README.md"):
            with self.subTest(entry=entry):
                self.assertIn(current, entry.read_text(encoding="utf-8"))

    def test_direct_opt_in_does_not_imply_goal_background_or_delegation(self):
        metadata = (TASK / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("disable-model-invocation: true", self.skill.split("---", 2)[1])
        self.assertIn("allow_implicit_invocation: false", metadata)
        self.assertIn("Ordinary complex work uses system planning.", self.skill)
        direct = self.skill.split("**Direct (default):**", 1)[1].splitlines()[0]
        self.assertIn("do not create a Goal, detach, or invoke orchestration", direct)
        self.assertIn("A native Goal is not a background request.", self.skill)
        self.assertIn("does not itself request orchestration", self.skill)

    def test_native_goal_is_host_owned_and_lookup_does_not_advance(self):
        self.assertIn("host-supported `/goal` entry point", self.skill)
        self.assertIn("The host owns lifecycle, budgets, continuation and hard stops.", self.skill)
        self.assertIn("do not simulate it", self.skill)
        self.assertIn("never commandeer a different active Goal", self.skill)
        self.assertIn("Do not start, replace, or reset a Goal to obtain more attempts", self.skill)
        self.assertIn("`thread/goal/get`", self.handoff)
        self.assertIn("Do not set, clear, pause, or resume a Goal", self.handoff)
        self.assertIn("the lookup must not trigger advancement", self.handoff)
        authority = (TASK / "references" / "scope-authority.md").read_text(encoding="utf-8")
        self.assertIn("not as permission to start, resume", authority)

    def test_missing_capability_and_ambiguous_dispatch_do_not_change_route(self):
        self.assertIn("If detached execution is unsupported", self.skill)
        self.assertIn("silently switch modes", self.skill)
        self.assertIn("Do not spawn two jobs.", self.handoff)
        self.assertIn("query the host for the accepted run before retrying", self.handoff)
        self.assertIn("report that uncertainty rather than submitting again", self.handoff)

    def test_permission_does_not_follow_brief_or_old_request(self):
        self.assertIn("changed scope overrides an older brief or approval", self.skill)
        self.assertIn("The brief is evidence, not an authorization surface.", self.skill)
        self.assertIn("Give read-only workers no write authority", self.skill)
        self.assertIn("exact, disjoint paths within authorized scope", self.skill)

    def test_duplicate_approval_requires_same_operational_effect(self):
        authority = (TASK / "references" / "scope-authority.md").read_text(encoding="utf-8")
        self.assertIn("A host denial wins", authority)
        self.assertIn("affected branch; continue only independent authorized work", authority)
        self.assertIn("working directory", authority)
        self.assertIn("different directories or against different", authority)
        self.assertIn("Revocation and expiry invalidate", authority)
        self.assertIn("instead of asking the user independently", authority)

    def test_terminal_success_is_not_verified_completion(self):
        self.assertIn("A status-only request never starts, resumes, or changes work.", self.skill)
        self.assertIn("Query the recorded host reference for current state", self.handoff)
        self.assertIn("Acknowledgment is not a running-state observation.", self.handoff)
        self.assertIn("result not yet verified.", self.handoff)
        self.assertIn("host task/worker status from the native receipt", self.handoff)
        self.assertIn("for worker dispatch and progress", self.skill)
        self.assertIn("Host terminal success and requested artifact/outcome plus acceptance checks", self.handoff)
        self.assertIn("report cancellation requested, not cancelled", self.handoff)

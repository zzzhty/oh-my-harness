"""Selected skill entry points and their references preserve action boundaries."""

from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATT = ROOT / "plugins/mattpocock-skills/skills"
BASH = shutil.which("bash")


class SkillAuthorityTests(unittest.TestCase):
    def assert_skill_contains(self, path: str, *phrases: str) -> None:
        skill = (MATT / path).read_text(encoding="utf-8")
        for phrase in phrases:
            with self.subTest(path=path, phrase=phrase):
                self.assertIn(phrase, skill)

    def test_implement_preserves_staged_user_work_by_default(self) -> None:
        self.assert_skill_contains(
            "implement/SKILL.md",
            "unstaged by default",
            "Inspect staged and unstaged diffs separately",
            "never whole files containing mixed changes",
            "leave the index intact and report the blocker",
        )

    def test_diagnosis_and_verification_do_not_authorize_repair(self) -> None:
        self.assert_skill_contains(
            "diagnosing-bugs/SKILL.md",
            "does not authorize a repair",
            "When repair is authorized",
        )
        verify = ROOT / "plugins/workflow/skills/create-verification-skill/SKILL.md"
        text = verify.read_text(encoding="utf-8")
        self.assertIn("does not authorize repairing the application", text)
        self.assertIn("report application or shared-environment failures unless repair is authorized", text)

    def test_triage_outcome_does_not_authorize_mutations_even_in_references(self) -> None:
        self.assert_skill_contains(
            "triage/SKILL.md",
            "Agreement with a recommended outcome (including rejection) is not authorization",
            "close an item, or write local records",
            "options, not a bundled approval",
        )
        self.assert_skill_contains("triage/AGENT-BRIEF.md", "Post it only when posting is authorized")
        self.assert_skill_contains(
            "triage/OUT-OF-SCOPE.md",
            "A maintainer decision is not consent",
            "otherwise present it as a proposed next step",
        )

    def test_spec_and_triage_share_only_the_acceptance_criterion_shape(self) -> None:
        spec = (MATT / "to-spec/SKILL.md").read_text(encoding="utf-8")
        brief = (MATT / "triage/AGENT-BRIEF.md").read_text(encoding="utf-8")
        criterion = next(line for line in spec.splitlines() if line.startswith("- [ ] **Condition/action:**"))
        self.assertIn(criterion, brief.split("## Template", 1)[1])
        self.assertIn("**Observable result:**", criterion)
        self.assertIn("**Verification:**", criterion)
        self.assertNotIn("AGENT-BRIEF.md", spec)
        self.assertNotIn("to-spec/", brief)
        self.assertIn("Publish to a tracker only when separately authorized", spec)
        self.assertIn("Post it only when posting is authorized", brief)

    def test_private_artifacts_do_not_default_to_publication(self) -> None:
        self.assert_skill_contains("teach/SKILL.md", "teach without persisting personal material", "skip these reads and writes when no private root is established")
        self.assert_skill_contains("teach/LEARNING-RECORD-FORMAT.md", "even as untracked files")
        self.assert_skill_contains("prototype/SKILL.md", "a format, not permission to share it")
        self.assert_skill_contains("prototype/LOGIC.md", "only to an authorized destination")
        self.assert_skill_contains("prototype/UI.md", "not a shared or production instance")
        self.assert_skill_contains("handoff/SKILL.md", "outside repositories and shared workspaces", "owner-only access", "does not authorize sending it")

    @unittest.skipUnless(BASH, "Bash is required for the HITL template")
    def test_hitl_never_prints_arbitrary_capture_input(self) -> None:
        template = MATT / "diagnosing-bugs/scripts/hitl-loop.template.sh"
        run = subprocess.run(
            [BASH, template.name],
            cwd=template.parent,
            input="secret-on-step\nBearer secret-on-answer\nY\n",
            capture_output=True,
            encoding="utf-8",
            check=True,
            timeout=10,
        )
        self.assertIn("Enter y or n only.", run.stdout)
        self.assertIn("ERRORED=yes", run.stdout)
        self.assertNotIn("secret-on-", run.stdout + run.stderr)

    @unittest.skipUnless(BASH, "Bash is required for the HITL template")
    def test_hitl_incomplete_capture_does_not_emit_a_transcript(self) -> None:
        template = MATT / "diagnosing-bugs/scripts/hitl-loop.template.sh"
        run = subprocess.run(
            [BASH, template.name],
            cwd=template.parent,
            input="\nunusable-private-input\n",
            capture_output=True,
            encoding="utf-8",
            check=False,
            timeout=10,
        )
        self.assertNotEqual(run.returncode, 0)
        self.assertNotIn("ERRORED=", run.stdout)
        self.assertNotIn("unusable-private-input", run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()

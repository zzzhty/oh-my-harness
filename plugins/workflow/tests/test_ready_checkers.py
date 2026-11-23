from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SOP_CHECKER = ROOT / "skills" / "sop" / "scripts" / "check_sop_ready.py"


def replace_all(text: str, *pairs: tuple[str, str]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


class ReadyCheckerTests(unittest.TestCase):
    def run_checker(
        self,
        checker: Path,
        document: Path,
        *extra_args: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(checker), str(document), *extra_args],
            capture_output=True,
            check=False,
            text=True,
        )

    def assert_checker_contract(self, checker: Path, fixture: Path) -> None:
        completed = self.run_checker(checker, fixture)
        self.assertEqual(completed.returncode, 0, completed.stderr)

        incomplete = fixture.read_text(encoding="utf-8")
        incomplete += "\n```bash\nrun <unfinished-command>\n```\n"
        with tempfile.TemporaryDirectory() as tmp:
            document = Path(tmp) / fixture.name
            document.write_text(incomplete, encoding="utf-8")
            failed = self.run_checker(checker, document)

        self.assertEqual(failed.returncode, 1)
        self.assertIn("unresolved placeholders: <unfinished-command>", failed.stderr)

    def test_sop_checker_validates_placeholders_inside_fences(self) -> None:
        self.assert_checker_contract(SOP_CHECKER, FIXTURES / "ready_sop.md")

    def test_sop_recovery_contracts_keep_existing_readiness_and_required_fields(self) -> None:
        # Document structure only: model recovery decisions are reviewed separately.
        for fixture in ("ready_sop.md", "ready_sop_with_recovery.md"):
            ready = (FIXTURES / fixture).read_text(encoding="utf-8")
            draft = ready.replace("Status: Ready", "Status: Draft")
            variants = (
                ("ready", ready, (), 0, None),
                ("draft", draft, (), 1, "SOP status must be Ready"),
                ("draft-preview", draft, ("--allow-draft",), 0, None),
                (
                    "missing-actions",
                    re.sub(r"(?ms)^## Allowed Actions\n.*?(?=^## )", "", ready),
                    (), 1, "missing required section: allowed actions",
                ),
                (
                    "missing-validation",
                    re.sub(r"(?ms)^## Validation\n.*?(?=^## )", "", ready),
                    (), 1, "missing required section: validation",
                ),
                (
                    "missing-step-output",
                    re.sub(r"(?ms)^Expected Output:.*?(?=^Failure Handling:)", "", ready, count=1),
                    (), 1, "Step 1 missing required field: expected output",
                ),
            )
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / fixture
                for name, document, args, expected, diagnostic in variants:
                    with self.subTest(fixture=fixture, variant=name):
                        path.write_text(document, encoding="utf-8")
                        result = self.run_checker(SOP_CHECKER, path, *args)
                        self.assertEqual(result.returncode, expected, result.stderr)
                        if diagnostic:
                            self.assertIn(diagnostic, result.stderr)

    def test_sop_checker_enforces_ready_lifecycle_and_step_contract(self) -> None:
        ready = (FIXTURES / "ready_sop.md").read_text(encoding="utf-8")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def run(name: str, text: str, *args: str) -> subprocess.CompletedProcess[str]:
                document = root / name
                document.write_text(text, encoding="utf-8")
                return self.run_checker(SOP_CHECKER, document, *args)

            draft = ready.replace("Status: Ready", "Status: Draft")
            draft_default = run("draft-default.md", draft)
            draft_allowed = run("draft-allowed.md", draft, "--allow-draft")
            invalid_status = run(
                "in-progress.md",
                ready.replace("Status: Ready", "Status: In Progress"),
            )
            empty_shell = run(
                "empty-shell.md",
                "Status: Ready\n\n"
                + "\n\n".join(
                    f"## {heading}"
                    for heading in (
                        "Summary",
                        "Trigger",
                        "Preconditions",
                        "Working Directory",
                        "Inputs",
                        "Execution Harness",
                        "Allowed Actions",
                        "Forbidden Actions",
                        "Steps",
                        "Validation",
                        "Output Contract",
                        "Stop Conditions",
                        "Update Rules",
                        "Reuse Prompt",
                    )
                )
                + "\n",
            )
            missing_completion = run(
                "missing-completion.md",
                re.sub(
                    r"(?ms)^Completion Criterion:\n\n.*?(?=^## Validation)",
                    "",
                    ready,
                ),
            )
            fenced_step_text, replacement_count = re.subn(
                r"(?ms)^### Step 1\b.*?(?=^## Validation)",
                "```markdown\n"
                "### Step 1: Fake\n\n"
                "Action:\nRun it.\n\n"
                "Expected Output:\nOutput exists.\n\n"
                "Failure Handling:\nStop.\n\n"
                "Completion Criterion:\nCheck passes.\n"
                "```\n\n",
                ready,
            )
            self.assertEqual(replacement_count, 1)
            fenced_step = run("fenced-step.md", fenced_step_text)
            fenced_values = run(
                "fenced-values.md",
                replace_all(
                    ready,
                    (
                        "Action:\n\nRun the demo command.",
                        "Action:\n\n```bash\nrun-demo\n```",
                    ),
                    (
                        "Expected Output:\n\nThe command exits with status zero.",
                        "Expected Output:\n\n```text\nExit status: 0\n```",
                    ),
                    (
                        "Failure Handling:\n\nStop and report the failing command.",
                        "Failure Handling:\n\n```text\nStop and report the failing command.\n```",
                    ),
                    (
                        "Completion Criterion:\n\nThe zero exit status is recorded in the result.",
                        "Completion Criterion:\n\n```text\nThe zero exit status is recorded.\n```",
                    ),
                ),
            )

        self.assertEqual(draft_default.returncode, 1)
        self.assertIn("SOP status must be Ready; found Draft", draft_default.stderr)
        self.assertEqual(draft_allowed.returncode, 0, draft_allowed.stderr)
        self.assertEqual(invalid_status.returncode, 1)
        self.assertIn(
            "invalid top-level SOP status; expected Draft or Ready; found In Progress",
            invalid_status.stderr,
        )
        self.assertEqual(empty_shell.returncode, 1)
        self.assertIn("required section has no substantive content: summary", empty_shell.stderr)
        self.assertEqual(missing_completion.returncode, 0, missing_completion.stderr)
        self.assertEqual(fenced_step.returncode, 1)
        self.assertIn("steps section must include at least one `### Step` entry", fenced_step.stderr)
        self.assertEqual(fenced_values.returncode, 0, fenced_values.stderr)

    def test_compact_sop_retains_permissions_and_observable_steps(self) -> None:
        ready = (FIXTURES / "ready_sop.md").read_text(encoding="utf-8")
        for heading in ("Summary", "Preconditions", "Working Directory", "Forbidden Actions", "Update Rules", "Reuse Prompt"):
            ready = re.sub(rf"(?ms)^## {heading}\n.*?(?=^## |\Z)", "", ready)
        ready = re.sub(r"(?ms)^Failure Handling:\n.*?(?=^## Validation)", "", ready)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "compact.md"
            for variant, expected in (
                (ready, 0),
                (re.sub(r"(?ms)^## Allowed Actions\n.*?(?=^## )", "", ready), 1),
                (re.sub(r"(?ms)^## Stop Conditions\n.*?(?=^## |\Z)", "", ready), 1),
                (re.sub(r"(?ms)^Expected Output:\n.*?(?=^## Validation)", "", ready), 1),
            ):
                with self.subTest(variant=variant):
                    path.write_text(variant, encoding="utf-8")
                    result = self.run_checker(SOP_CHECKER, path)
                    self.assertEqual(result.returncode, expected, result.stderr)



if __name__ == "__main__":
    unittest.main()

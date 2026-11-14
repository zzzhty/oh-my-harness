"""The architecture checker catches recorded mistakes and accepts the current tree."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_architecture as arch

EMPTY = {"file_lines": {}, "text_io_utf8": {}, "ruff": []}

# 6ccb996, before the target index was read as bytes.
TARGET_INDEX_READ = """\
def load(home, name):
    recorded = __import__("json").loads((home / name).read_text())
    return recorded
"""

# 557a629, before run_git passed encoding="utf-8".
GIT_TEXT_RUN = """\
def run_git(repo, args):
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.stdout
"""

# 74f6145, before Get-Content used -Encoding UTF8.
BINDING_READ = (
    "$python = if (Test-Path Env:OMH_PYTHON) { $env:OMH_PYTHON } else "
    '{ (Get-Content -LiteralPath (Join-Path $PSScriptRoot "$group.python") -Raw)'
    '.TrimEnd("`r", "`n") }\n'
)

# d663090, before prepare/verify rejected leftover argv.
CLOSED_COMMAND = """\
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request")
    args, argv = parser.parse_known_args()
    return args, argv
"""

# 6e63ea0 / ADR 0026, when omp was the canonical harness id.
OMP_HARNESS = """\
import sys
HARNESS_ROOTS = {"omp": ".omp"}
INSTRUCTIONS = {"omp": "AGENTS.md"}

def build(sub):
    sub.add_argument("--harness", choices=["omp"])

def main():
    sys.stdout.reconfigure(encoding="utf-8")
"""

EXPLICIT_UTF8 = """\
import os
import subprocess
from pathlib import Path

def ok(path):
    path.read_text(encoding="utf-8")
    path.read_text("utf-8")
    path.write_text("x", encoding="utf-8")
    open(path, "rb")
    open(path, "w", encoding="utf-8")
    fd = os.open(path, os.O_RDONLY)
    os.fdopen(fd, "wb")
    path.open("rb")
    subprocess.run(["git"], text=True, encoding="utf-8")
    subprocess.run(["git"], capture_output=True)
"""


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def errors(items, rule):
    return [item for item in items if item.level == "ERROR" and item.rule == rule]


class ArchitectureCheckTests(unittest.TestCase):
    def test_current_tree_has_no_errors(self) -> None:
        found = arch.check(ROOT, arch.load_baseline())
        self.assertEqual(
            [(item.path, item.line, item.violation) for item in found if item.level == "ERROR"],
            [],
        )

    def test_cli_passes_on_the_repository(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_architecture.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("[ARCH] Passed", completed.stdout)

    def test_known_long_files_stay_within_their_ceilings(self) -> None:
        ceilings = arch.load_baseline()["file_lines"]
        for relative in (
            "plugins/workflow/skills/long-running-goal/scripts/check_goal_ready.py",
            "omh/standalone.py",
            "tests/test_standalone.py",
        ):
            lines = arch.count_lines((ROOT / relative).read_text(encoding="utf-8"))
            self.assertIn(relative, ceilings)
            self.assertLessEqual(lines, ceilings[relative])

    def test_target_index_read_text_is_caught_and_baselined(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "read_index.py", TARGET_INDEX_READ)
            caught = errors(arch.check(root, EMPTY, ruff=False), "text-io-utf8")
            self.assertEqual(len(caught), 1)
            self.assertIn('encoding="utf-8"', caught[0].fix)
            self.assertIn("omh_runtime.launch", caught[0].fix)
            self.assertIn("6ccb996", caught[0].principle)
            rendered = caught[0].render()
            self.assertIn("\n  Violation:", rendered)
            self.assertIn("\n  Fix:", rendered)
            self.assertIn("\n  Principle:", rendered)
            allowed = dict(EMPTY, text_io_utf8={"read_index.py": 1})
            self.assertEqual(errors(arch.check(root, allowed, ruff=False), "text-io-utf8"), [])

    def test_git_text_mode_without_encoding_is_caught(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "run_git.py", GIT_TEXT_RUN)
            caught = errors(arch.check(root, EMPTY, ruff=False), "text-io-utf8")
            self.assertEqual(len(caught), 1)
            self.assertIn("audit_repo.run_git", caught[0].fix)
            self.assertIn("557a629", caught[0].principle)

    def test_powershell_binding_read_without_encoding_is_caught(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "run.ps1", BINDING_READ)
            caught = errors(arch.check(root, EMPTY, ruff=False), "text-io-utf8")
            self.assertEqual(len(caught), 1)
            self.assertIn("plugins/workflow/scripts/run.ps1", caught[0].fix)
            self.assertIn("74f6145", caught[0].principle)
            write(root, "run.ps1", BINDING_READ.replace("-Raw)", "-Raw -Encoding UTF8)"))
            self.assertEqual(errors(arch.check(root, EMPTY, ruff=False), "text-io-utf8"), [])

    def test_explicit_utf8_and_binary_opens_are_not_text_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "explicit.py", EXPLICIT_UTF8)
            write(root, "note.ps1", "# Get-Content readme.txt\nGet-Content -Encoding UTF8 readme.txt\n")
            self.assertEqual(errors(arch.check(root, EMPTY, ruff=False), "text-io-utf8"), [])

    def test_closed_command_parse_known_args_is_caught(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "closed.py", CLOSED_COMMAND)
            caught = errors(arch.check(root, EMPTY, ruff=False), "closed-argv")
            self.assertEqual(len(caught), 1)
            self.assertIn("parse_args", caught[0].fix)
            self.assertIn("omh_runtime.main", caught[0].fix)
            self.assertIn("d663090", caught[0].principle)
            (root / "closed.py").unlink()
            write(root, "plugins/workflow/scripts/omh_runtime.py", "def main():\n    parser.parse_known_args()\n")
            self.assertEqual(errors(arch.check(root, EMPTY, ruff=False), "closed-argv"), [])
            write(
                root,
                "plugins/workflow/scripts/omh_runtime.py",
                "def main():\n    parser.parse_known_args()\n    parser.parse_known_args()\n",
            )
            again = errors(arch.check(root, EMPTY, ruff=False), "closed-argv")
            self.assertEqual(len(again), 1)

    def test_short_canonical_harness_id_is_caught(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "omh/standalone.py", OMP_HARNESS)
            caught = errors(arch.check(root, EMPTY, ruff=False), "harness-identity")
            self.assertTrue(caught)
            self.assertIn("omp", caught[0].violation)
            self.assertIn("omh/standalone.py", caught[0].fix)
            self.assertIn("6e63ea0", caught[0].principle)

    def test_harness_tables_must_stay_one_set(self) -> None:
        source = """\
HARNESS_ROOTS = {"codex": ".codex", "claude-code": ".claude"}
INSTRUCTIONS = {"codex": "AGENTS.md"}

def build(sub):
    sub.add_argument("--harness", choices=["codex", "claude-code"])

def main():
    sys.stdout.reconfigure(encoding="utf-8")
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "omh/standalone.py", source)
            caught = errors(arch.check(root, EMPTY, ruff=False), "harness-identity")
            self.assertTrue(any("INSTRUCTIONS" in item.violation for item in caught))

    def test_third_party_import_in_the_distributor_is_caught(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "omh/extra.py", "import yaml\n")
            caught = errors(arch.check(root, EMPTY, ruff=False), "distributor-stdlib")
            self.assertEqual(len(caught), 1)
            self.assertIn("yaml", caught[0].violation)
            self.assertIn("omh/standalone.py", caught[0].fix)
            self.assertIn("ADR 0031", caught[0].principle)

    def test_entry_point_without_utf8_reconfigure_is_caught(self) -> None:
        source = """\
HARNESS_ROOTS = {"codex": ".codex"}
INSTRUCTIONS = {"codex": "AGENTS.md"}

def build(sub):
    sub.add_argument("--harness", choices=["codex"])

def main():
    print("status")
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "omh/standalone.py", source)
            caught = errors(arch.check(root, EMPTY, ruff=False), "cli-stdout-utf8")
            self.assertEqual(len(caught), 1)
            self.assertIn("omh.standalone.main", caught[0].fix)
            self.assertIn("5ec86f8", caught[0].principle)

    def test_new_and_growing_python_files_follow_the_ceiling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "legacy.py", "\n".join(["x = 1"] * 4) + "\n")
            baseline = {"file_lines": {"legacy.py": 4}, "text_io_utf8": {}, "ruff": []}
            self.assertEqual(arch.check(root, baseline, ruff=False), [])
            write(root, "legacy.py", "\n".join(["x = 1"] * 5) + "\n")
            grown = errors(arch.check(root, baseline, ruff=False), "file-length")
            self.assertEqual(len(grown), 1)
            self.assertIn("baseline of 4", grown[0].violation)
            self.assertIn("scripts/architecture_baseline.json", grown[0].fix)
            write(root, "fresh.py", "\n".join(["x = 1"] * 1001) + "\n")
            fresh = errors(arch.check(root, baseline, ruff=False), "file-length")
            self.assertTrue(any("1000" in item.violation for item in fresh))
            write(root, "medium.py", "\n".join(["x = 1"] * 501) + "\n")
            found = arch.check(root, baseline, ruff=False)
            warnings = [item for item in found if item.level == "WARN" and item.rule == "file-length"]
            self.assertEqual(len(warnings), 1)
            self.assertEqual(arch.exit_code(warnings), 0)

    def test_ruff_blocks_a_new_undefined_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "broken.py", "def broken():\n    return missing_name\n")
            caught = errors(arch.check(root, EMPTY, ruff=True), "ruff")
            self.assertEqual(len(caught), 1)
            self.assertIn("F821", caught[0].violation)
            self.assertIn("ruff.toml", caught[0].fix)
            finger = arch.ruff_fingerprint("broken.py", "F821", "Undefined name `missing_name`")
            allowed = dict(EMPTY, ruff=[finger])
            self.assertEqual(errors(arch.check(root, allowed, ruff=True), "ruff"), [])


if __name__ == "__main__":
    unittest.main()

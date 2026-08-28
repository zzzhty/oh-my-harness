from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_git(*arguments: str, cwd: Path) -> None:
    subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def write_recording_installer(checkout: Path) -> Path:
    installer = checkout / "scripts" / "install_oh_my_harness.py"
    installer.parent.mkdir(parents=True, exist_ok=True)
    installer.write_text(
        "from __future__ import annotations\n"
        "import json\n"
        "import os\n"
        "import sys\n"
        "from pathlib import Path\n"
        "Path(os.environ['INSTALLER_RECORD']).write_text(\n"
        "    json.dumps({'arguments': sys.argv[1:], 'source': str(Path(__file__).resolve())}),\n"
        "    encoding='utf-8',\n"
        ")\n",
        encoding="utf-8",
    )
    return installer


def make_bootstrap_repository(root: Path) -> Path:
    checkout = root / "bootstrap-source"
    checkout.mkdir()
    write_recording_installer(checkout)
    run_git("init", "-b", "main", cwd=checkout)
    run_git("config", "user.email", "installer-test@example.invalid", cwd=checkout)
    run_git("config", "user.name", "Installer Test", cwd=checkout)
    run_git("add", "scripts/install_oh_my_harness.py", cwd=checkout)
    run_git("commit", "-m", "fixture", cwd=checkout)
    return checkout


class UnixInstallerWrapperTests(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "POSIX wrapper test")
    def test_checkout_wrapper_uses_its_local_python_installer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkout = root / "checkout"
            checkout.mkdir()
            wrapper = checkout / "install.sh"
            wrapper.write_bytes((REPO_ROOT / "install.sh").read_bytes())
            installer = write_recording_installer(checkout)
            record = root / "record.json"
            environment = {
                **os.environ,
                "INSTALLER_RECORD": str(record),
                "OH_MY_HARNESS_BOOTSTRAP_PYTHON": sys.executable,
            }

            result = subprocess.run(
                [
                    "sh",
                    str(wrapper),
                    "--repository",
                    "https://example.invalid/oh-my-harness.git",
                    "--ref",
                    "feature",
                ],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
            )
            payload = json.loads(record.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["source"], str(installer.resolve()))
        self.assertEqual(
            payload["arguments"],
            [
                "--repository",
                "https://example.invalid/oh-my-harness.git",
                "--ref",
                "feature",
            ],
        )
        self.assertNotIn("Cloning into", result.stderr)

    @unittest.skipIf(os.name == "nt", "POSIX wrapper test")
    def test_streamed_wrapper_clones_bootstrap_source_and_preserves_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repository = make_bootstrap_repository(root)
            record = root / "record.json"
            environment = {
                **os.environ,
                "INSTALLER_RECORD": str(record),
                "OH_MY_HARNESS_BOOTSTRAP_PYTHON": sys.executable,
            }
            arguments = [
                "--repository",
                str(repository),
                "--ref=main",
                "--dry-run",
            ]

            result = subprocess.run(
                ["bash", "-s", "--", *arguments],
                cwd=root,
                env=environment,
                input=(REPO_ROOT / "install.sh").read_text(encoding="utf-8"),
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(record.is_file(), result.stderr)
            payload = json.loads(record.read_text(encoding="utf-8"))
            bootstrap_root = Path(payload["source"]).parents[2]

        self.assertEqual(payload["arguments"], arguments)
        self.assertIn("Cloning into", result.stderr)
        self.assertFalse(bootstrap_root.exists())


@unittest.skipUnless(
    os.name == "nt" and shutil.which("powershell.exe"),
    "Windows PowerShell wrapper test",
)
class PowerShellStreamedInstallerTests(unittest.TestCase):
    def test_streamed_wrapper_clones_bootstrap_source_and_preserves_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repository = make_bootstrap_repository(root)
            record = root / "record.json"
            environment = {
                **os.environ,
                "INSTALLER_RECORD": str(record),
                "OH_MY_HARNESS_BOOTSTRAP_PYTHON": sys.executable,
                "TEST_BOOTSTRAP_REPOSITORY": str(repository),
            }
            command = (
                "$source = [Console]::In.ReadToEnd(); "
                "$installer = [ScriptBlock]::Create($source); "
                "& $installer --repository $env:TEST_BOOTSTRAP_REPOSITORY "
                "--ref=main --dry-run; "
                "exit $LASTEXITCODE"
            )

            result = subprocess.run(
                [
                    shutil.which("powershell.exe") or "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    command,
                ],
                cwd=root,
                env=environment,
                input=(REPO_ROOT / "install.ps1").read_text(encoding="utf-8"),
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(record.is_file(), result.stderr)
            payload = json.loads(record.read_text(encoding="utf-8"))
            bootstrap_root = Path(payload["source"]).parents[2]

        self.assertEqual(
            payload["arguments"],
            ["--repository", str(repository), "--ref=main", "--dry-run"],
        )
        self.assertIn("Cloning into", result.stderr)
        self.assertFalse(bootstrap_root.exists())


if __name__ == "__main__":
    unittest.main()

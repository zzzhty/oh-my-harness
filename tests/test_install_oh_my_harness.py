from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import install_oh_my_harness as installer  # noqa: E402


class InstallerTests(unittest.TestCase):
    def test_launcher_help_uses_platform_wrapper_syntax(self) -> None:
        self.assertEqual(installer.launcher_help_invocation("nt"), "omh -Help")
        self.assertEqual(installer.launcher_help_invocation("posix"), "omh --help")

    @unittest.skipIf(os.name == "nt", "POSIX launcher assertion")
    def test_long_and_short_launchers_are_identical_ordinary_executables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".oh-my-harness"
            repo = home / "repo"
            repo.mkdir(parents=True)
            launchers = installer.write_launchers(home=home, repo=repo, dry_run=False)

            long_command, short_command = launchers
            self.assertFalse(long_command.is_symlink())
            self.assertFalse(short_command.is_symlink())
            self.assertEqual(
                long_command.read_text(encoding="utf-8"),
                short_command.read_text(encoding="utf-8"),
            )
            content = long_command.read_text(encoding="utf-8")
            self.assertIn(str(repo / "scripts" / "upgrade_oh_my_harness.sh"), content)
            self.assertIn(f"--home {home}", content)
            self.assertTrue(long_command.stat().st_mode & stat.S_IXUSR)

    def test_windows_aliases_dispatch_to_one_powershell_wrapper(self) -> None:
        home = Path(r"C:\Users\Tester\.oh-my-harness")
        repo = home / "repo"
        content = installer.windows_launcher(home=home, repo=repo)
        self.assertIn("upgrade_oh_my_harness.ps1", content)
        self.assertIn('-ManagerHome "', content)
        self.assertIn("%*", content)

    def test_install_refuses_existing_manager_owned_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".oh-my-harness"
            (home / "venv").mkdir(parents=True)
            with self.assertRaisesRegex(SystemExit, "existing manager-owned paths"):
                installer.validate_install_root(home)

    def test_adoption_allows_only_the_exact_existing_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".oh-my-harness"
            repo = home / "repo"
            repo.mkdir(parents=True)
            installer.validate_install_root(home, adopted_repo=repo)

            (home / "bin").mkdir()
            with self.assertRaisesRegex(SystemExit, "existing manager-owned paths"):
                installer.validate_install_root(home, adopted_repo=repo)

    def test_dry_run_does_not_create_manager_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".oh-my-harness"
            with (
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "install_oh_my_harness.py",
                        "--home",
                        str(home),
                        "--repository",
                        "https://example.invalid/oh-my-harness.git",
                        "--dry-run",
                    ],
                ),
                mock.patch.object(installer, "run") as run,
            ):
                installer.main()

            self.assertFalse(home.exists())
            run.assert_called_once()
            self.assertTrue(run.call_args.kwargs["dry_run"])

    def test_adopted_checkout_forwards_the_exact_retired_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".oh-my-harness"
            repo = home / "repo"
            repo.mkdir(parents=True)
            retired_repo = Path(tmp) / "former-checkout"
            with (
                mock.patch.object(installer, "SOURCE_ROOT", repo),
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "install_oh_my_harness.py",
                        "--home",
                        str(home),
                        "--repository",
                        "https://example.invalid/oh-my-harness.git",
                        "--adopt-current-checkout",
                        "--migrate-from-repo",
                        str(retired_repo),
                    ],
                ),
                mock.patch.object(installer, "write_install_state"),
                mock.patch.object(installer, "invoke_refresh") as refresh,
            ):
                installer.main()

            self.assertTrue(installer.launcher_paths(home)[1].is_file())
            self.assertEqual(
                refresh.call_args.kwargs["migrate_from_repo"],
                retired_repo.resolve(strict=False),
            )

    def test_exact_installing_state_auto_resumes_from_managed_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".oh-my-harness"
            repo = home / "repo"
            repo.mkdir(parents=True)
            repository = "https://example.invalid/oh-my-harness.git"
            with mock.patch.object(installer, "installed_revision", return_value="abc123"):
                launchers = installer.write_launchers(home=home, repo=repo, dry_run=False)
                installer.write_install_state(
                    home=home,
                    repository=repository,
                    ref="main",
                    repo=repo,
                    harness="codex",
                    launchers=launchers,
                    status="installing",
                )
                with (
                    mock.patch.object(installer, "SOURCE_ROOT", repo),
                    mock.patch.object(
                        sys,
                        "argv",
                        [
                            "install_oh_my_harness.py",
                            "--home",
                            str(home),
                            "--repository",
                            repository,
                            "--harness",
                            "codex",
                        ],
                    ),
                    mock.patch.object(installer, "clone_repository") as clone,
                    mock.patch.object(installer, "invoke_refresh") as refresh,
                ):
                    installer.main()

            clone.assert_not_called()
            refresh.assert_called_once()
            state = json.loads(
                (home / "state" / "install.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["status"], "ready")

    def test_exact_installing_state_auto_resumes_when_invoked_from_external_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".oh-my-harness"
            repo = home / "repo"
            repo.mkdir(parents=True)
            external_checkout = Path(tmp) / "external-checkout"
            external_checkout.mkdir()
            repository = "https://example.invalid/oh-my-harness.git"
            with mock.patch.object(installer, "installed_revision", return_value="abc123"):
                launchers = installer.write_launchers(home=home, repo=repo, dry_run=False)
                installer.write_install_state(
                    home=home,
                    repository=repository,
                    ref="main",
                    repo=repo,
                    harness="codex",
                    launchers=launchers,
                    status="installing",
                )
                with (
                    mock.patch.object(installer, "SOURCE_ROOT", external_checkout),
                    mock.patch.object(
                        sys,
                        "argv",
                        [
                            "install_oh_my_harness.py",
                            "--home",
                            str(home),
                            "--repository",
                            repository,
                            "--harness",
                            "codex",
                        ],
                    ),
                    mock.patch.object(installer, "clone_repository") as clone,
                    mock.patch.object(installer, "invoke_refresh") as refresh,
                ):
                    installer.main()

            clone.assert_not_called()
            refresh.assert_called_once()
            self.assertEqual(refresh.call_args.kwargs["repo"], repo)
            state = json.loads(
                (home / "state" / "install.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["status"], "ready")

    def test_managed_checkout_without_installing_state_requires_explicit_adoption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".oh-my-harness"
            repo = home / "repo"
            repo.mkdir(parents=True)
            with (
                mock.patch.object(installer, "SOURCE_ROOT", repo),
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "install_oh_my_harness.py",
                        "--home",
                        str(home),
                        "--repository",
                        "https://example.invalid/oh-my-harness.git",
                    ],
                ),
                mock.patch.object(installer, "clone_repository") as clone,
            ):
                with self.assertRaisesRegex(SystemExit, "existing manager-owned paths"):
                    installer.main()

            clone.assert_not_called()

    def test_incomplete_install_accepts_exact_crlf_launcher_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".oh-my-harness"
            repo = home / "repo"
            repo.mkdir(parents=True)
            repository = "https://example.invalid/oh-my-harness.git"
            expected_content = "@echo off\r\nexit /b 0\r\n"
            launchers = installer.launcher_paths(home)
            for launcher in launchers:
                launcher.parent.mkdir(parents=True, exist_ok=True)
                launcher.write_text(expected_content, encoding="utf-8", newline="")

            with (
                mock.patch.object(installer, "installed_revision", return_value="abc123"),
                mock.patch.object(
                    installer,
                    "expected_launcher_content",
                    return_value=expected_content,
                ),
            ):
                installer.write_install_state(
                    home=home,
                    repository=repository,
                    ref="main",
                    repo=repo,
                    harness="codex",
                    launchers=launchers,
                    status="installing",
                )
                allowed = installer.validate_incomplete_adoption(
                    home=home,
                    repo=repo,
                    repository=repository,
                    ref="main",
                    harness="codex",
                )

            self.assertEqual(
                allowed,
                frozenset({home / "venv", home / "bin", home / "state"}),
            )

    def test_exact_installing_state_rejects_shape_and_launcher_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".oh-my-harness"
            repo = home / "repo"
            repo.mkdir(parents=True)
            repository = "https://example.invalid/oh-my-harness.git"
            launchers = installer.write_launchers(home=home, repo=repo, dry_run=False)
            with mock.patch.object(installer, "installed_revision", return_value="abc123"):
                installer.write_install_state(
                    home=home,
                    repository=repository,
                    ref="main",
                    repo=repo,
                    harness="codex",
                    launchers=launchers,
                    status="installing",
                )
                state_file = home / "state" / "install.json"
                payload = json.loads(state_file.read_text(encoding="utf-8"))
                self.assertEqual(
                    set(payload),
                    {
                        "product",
                        "status",
                        "repository",
                        "ref",
                        "revision",
                        "harness",
                        "paths",
                    },
                )
                allowed = installer.validate_incomplete_adoption(
                    home=home,
                    repo=repo,
                    repository=repository,
                    ref="main",
                    harness="codex",
                )

                self.assertEqual(
                    allowed,
                    frozenset({home / "venv", home / "bin", home / "state"}),
                )
                installer.validate_install_root(
                    home,
                    adopted_repo=repo,
                    allowed_existing=allowed,
                )

                invalid_payloads = {
                    "legacy schemaVersion": {**payload, "schemaVersion": 1},
                    "missing product": {
                        key: value for key, value in payload.items() if key != "product"
                    },
                }
                for case, invalid_payload in invalid_payloads.items():
                    with self.subTest(case=case):
                        state_file.write_text(
                            json.dumps(
                                invalid_payload,
                                ensure_ascii=False,
                                indent=2,
                                sort_keys=True,
                            )
                            + "\n",
                            encoding="utf-8",
                        )
                        with self.assertRaisesRegex(SystemExit, "unsupported shape"):
                            installer.validate_incomplete_adoption(
                                home=home,
                                repo=repo,
                                repository=repository,
                                ref="main",
                                harness="codex",
                            )

                state_file.write_text(
                    json.dumps(
                        {**payload, "status": "ready"},
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(SystemExit, "mismatched fields: status"):
                    installer.validate_incomplete_adoption(
                        home=home,
                        repo=repo,
                        repository=repository,
                        ref="main",
                        harness="codex",
                    )

                state_file.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )

                launchers[1].write_text("drift\n", encoding="utf-8")
                with self.assertRaisesRegex(SystemExit, "launcher content changed"):
                    installer.validate_incomplete_adoption(
                        home=home,
                        repo=repo,
                        repository=repository,
                        ref="main",
                        harness="codex",
                    )

    def test_cli_reports_expected_and_command_failures_without_tracebacks(self) -> None:
        cases = (
            (
                SystemExit("specific installation failure"),
                1,
                "error: specific installation failure",
            ),
            (
                subprocess.CalledProcessError(17, ["git", "clone", "source", "target"]),
                17,
                "error: command failed with exit code 17: git clone source target",
            ),
        )
        for failure, expected_code, expected_message in cases:
            with self.subTest(failure=type(failure).__name__):
                stderr = io.StringIO()
                with (
                    mock.patch.object(installer, "main", side_effect=failure),
                    contextlib.redirect_stderr(stderr),
                ):
                    exit_code = installer.cli()

                self.assertEqual(exit_code, expected_code)
                self.assertIn(expected_message, stderr.getvalue())
                self.assertNotIn("Traceback", stderr.getvalue())


@unittest.skipUnless(
    os.name == "nt" and shutil.which("powershell.exe"),
    "Windows PowerShell wrapper test",
)
class PowerShellInstallerWrapperTests(unittest.TestCase):
    def test_python_failure_is_reported_without_a_powershell_exception(self) -> None:
        environment = dict(os.environ)
        environment["OH_MY_HARNESS_BOOTSTRAP_PYTHON"] = sys.executable
        result = subprocess.run(
            [
                shutil.which("powershell.exe") or "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "install.ps1"),
                "-MigrateMarketplace",
                "--home",
                "relative-manager-home",
            ],
            cwd=REPO_ROOT,
            env=environment,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "error: OH_MY_HARNESS_HOME must be an absolute path",
            result.stderr,
        )
        self.assertIn("installation failed with exit code", result.stderr)
        self.assertNotIn("\x1b", result.stderr)
        self.assertNotIn("Exception:", result.stderr)
        self.assertNotIn("At ", result.stderr)

    def test_wrapper_uses_console_color_only_for_interactive_errors(self) -> None:
        script = (REPO_ROOT / "install.ps1").read_text(encoding="utf-8")
        self.assertIn("function Write-AccentError", script)
        self.assertIn("[Console]::IsErrorRedirected", script)
        self.assertIn("[Console]::ForegroundColor", script)
        self.assertIn("Test-Path Env:NO_COLOR", script)
        self.assertIn("[switch]$MigrateMarketplace", script)
        self.assertIn('$forwardedInstallerArguments += "--migrate-marketplace"', script)


if __name__ == "__main__":
    unittest.main()

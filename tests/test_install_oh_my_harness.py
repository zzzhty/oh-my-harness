from __future__ import annotations

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import install_oh_my_harness as installer  # noqa: E402


class InstallerTests(unittest.TestCase):
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

            self.assertTrue((home / "bin" / "omh").is_file())
            self.assertEqual(
                refresh.call_args.kwargs["migrate_from_repo"],
                retired_repo.resolve(strict=False),
            )

    def test_exact_installing_state_can_resume_but_drift_is_rejected(self) -> None:
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

                (home / "bin" / "omh").write_text("drift\n", encoding="utf-8")
                with self.assertRaisesRegex(SystemExit, "launcher content changed"):
                    installer.validate_incomplete_adoption(
                        home=home,
                        repo=repo,
                        repository=repository,
                        ref="main",
                        harness="codex",
                    )


if __name__ == "__main__":
    unittest.main()

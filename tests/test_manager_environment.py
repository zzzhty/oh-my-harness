"""User PATH ownership and idempotence tests; no real user profile is touched."""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import manager_environment as environment


class UserEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.user = Path(self.tmp.name) / "user"
        self.user.mkdir()
        self.home = self.user / ".oh-my-harness"
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(environment.Path, "home", return_value=self.user).start()
        mock.patch.dict(os.environ, {"HOME": str(self.user), "SHELL": "/bin/bash", "PATH": os.environ.get("PATH", "")}, clear=False).start()
        self.stdout = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.stdout)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)

    def profile(self):
        return self.user / ".bashrc"

    def install(self, **kwargs):
        environment.ensure_user_path(self.home, **kwargs)

    @unittest.skipIf(os.name == "nt", "POSIX profiles")
    def test_install_creates_only_active_shell_and_login_profiles(self):
        self.install()
        self.assertTrue(self.profile().is_file())
        self.assertTrue((self.user / ".profile").is_file())
        self.assertFalse((self.user / ".zshrc").exists())
        self.assertIn(environment.START, self.profile().read_text())

    @unittest.skipIf(os.name == "nt", "POSIX profiles")
    def test_repeat_is_byte_and_mtime_idempotent(self):
        self.install()
        before = self.profile().read_bytes(), self.profile().stat().st_mtime_ns
        self.install()
        self.assertEqual(before, (self.profile().read_bytes(), self.profile().stat().st_mtime_ns))
        self.assertEqual(self.profile().read_text().count(environment.START), 1)

    @unittest.skipIf(os.name == "nt", "POSIX profiles")
    def test_preserves_unrelated_profile_text(self):
        old = "export CUSTOM='keep me'\n# personal config\n"
        self.profile().write_text(old)
        self.install()
        self.assertTrue(self.profile().read_text().startswith(old))
        self.install(remove=True)
        self.assertEqual(self.profile().read_text(), old)

    @unittest.skipIf(os.name == "nt", "POSIX profiles")
    def test_dry_run_writes_nothing(self):
        self.install(dry_run=True)
        self.assertFalse(self.home.exists())
        self.assertFalse(self.profile().exists())

    @unittest.skipIf(os.name == "nt", "POSIX profiles")
    def test_relocation_rewrites_owned_blocks(self):
        self.install()
        old_home = self.home
        self.home = self.user / "moved home"
        old_home.rename(self.home)
        self.install()
        text = self.profile().read_text()
        self.assertIn(str(self.home / "bin"), text)
        self.assertNotIn(str(old_home / "bin"), text)
        self.assertEqual(text.count(environment.START), 1)

    @unittest.skipIf(os.name == "nt", "POSIX profiles")
    def test_copied_receipt_does_not_write_to_old_account(self):
        old_profile = Path(self.tmp.name) / "another-account" / ".bashrc"
        old_profile.parent.mkdir()
        old_profile.write_text("DO NOT TOUCH\n")
        state = self.home / "state"
        state.mkdir(parents=True)
        receipt = {"product": "oh-my-harness", "userHome": str(old_profile.parent),
                   "bin": str(old_profile.parent / ".oh-my-harness/bin"),
                   "profiles": [{"path": str(old_profile), "fish": False}]}
        (state / environment.RECEIPT).write_text(json.dumps(receipt))
        self.profile().write_text(environment._block(receipt["bin"]))
        self.install()
        self.assertEqual(old_profile.read_text(), "DO NOT TOUCH\n")
        self.assertIn(str(self.home / "bin"), self.profile().read_text())

    @unittest.skipIf(os.name == "nt", "POSIX profiles")
    def test_profile_symlink_is_preserved(self):
        target = self.user / "dotfiles/bashrc"
        target.parent.mkdir()
        target.write_text("# dotfiles\n")
        self.profile().symlink_to(target)
        self.install()
        self.assertTrue(self.profile().is_symlink())
        self.assertIn(environment.START, target.read_text())

    @unittest.skipIf(os.name == "nt", "POSIX profiles")
    def test_permissions_are_preserved(self):
        self.profile().write_text("# kept\n")
        self.profile().chmod(0o640)
        self.install()
        self.assertEqual(self.profile().stat().st_mode & 0o777, 0o640)

    @unittest.skipIf(os.name == "nt", "POSIX profiles")
    def test_modified_owned_block_is_not_overwritten(self):
        self.install()
        damaged = self.profile().read_text().replace("export PATH=", "export PATH=custom:")
        self.profile().write_text(damaged)
        with self.assertRaisesRegex(RuntimeError, "edited"):
            self.install()
        self.assertEqual(self.profile().read_text(), damaged)

    @unittest.skipIf(os.name == "nt", "POSIX profiles")
    def test_all_profiles_are_preflighted_before_any_write(self):
        self.profile().write_text(environment.START + "\n# incomplete\n")
        with self.assertRaisesRegex(RuntimeError, "incomplete"):
            self.install()
        self.assertFalse((self.user / ".profile").exists())

    @unittest.skipIf(os.name == "nt", "POSIX profiles")
    def test_linked_state_is_rejected(self):
        self.home.mkdir()
        other = self.user / "other"
        other.mkdir()
        (self.home / "state").symlink_to(other, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, "ordinary"):
            self.install()
        self.assertEqual(list(other.iterdir()), [])

    @unittest.skipIf(os.name == "nt", "POSIX profiles")
    def test_zsh_respects_zdotdir(self):
        root = self.user / "zsh-files"
        with mock.patch.dict(os.environ, {"SHELL": "/bin/zsh", "ZDOTDIR": str(root)}):
            self.install()
        self.assertTrue((root / ".zprofile").is_file())
        self.assertTrue((root / ".zshrc").is_file())
        self.assertFalse(self.profile().exists())

    @unittest.skipIf(os.name == "nt", "POSIX profiles")
    def test_fish_respects_xdg(self):
        root = self.user / "xdg"
        with mock.patch.dict(os.environ, {"SHELL": "/bin/fish", "XDG_CONFIG_HOME": str(root)}):
            self.install()
        text = (root / "fish/conf.d/oh-my-harness.fish").read_text()
        self.assertIn("set -gx PATH", text)
        self.assertNotIn("export PATH=", text)

    @unittest.skipUnless(os.name != "nt" and shutil.which("sh"), "needs POSIX sh")
    def test_shell_block_quotes_spaces_apostrophes_and_dollars(self):
        entry = str(self.user / "space ' $ & [literal]" / "bin")
        code = environment._block(entry)
        process = subprocess.run(["sh", "-c", code + code + '\nprintf "%s" "$PATH"'],
                                 env={"PATH": "/usr/bin:/bin"}, capture_output=True, text=True, check=True)
        self.assertEqual(process.stdout, entry + ":/usr/bin:/bin")

    @unittest.skipUnless(os.name != "nt" and shutil.which("sh"), "needs POSIX sh")
    def test_empty_path_does_not_gain_current_directory(self):
        entry = "/some/bin"
        process = subprocess.run([shutil.which("sh"), "-c", environment._block(entry) + 'printf "%s" "$PATH"'],
                                 env={"PATH": ""}, capture_output=True, text=True, check=True)
        self.assertEqual(process.stdout, entry)

    def test_unsafe_posix_path_entries_rejected(self):
        for value in ("/tmp/part:other", "/tmp/line\nbreak", "/tmp/line\rbreak"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                environment._block(value)

    def test_windows_comparison_is_case_insensitive(self):
        current = r"C:\Windows;C:\Users\ME\omh\bin;D:\Tools"
        value, added = environment._windows_path(current, r"c:\users\me\omh\bin")
        self.assertEqual(value, current)
        self.assertFalse(added)

    def test_windows_insertion_and_removal_preserve_other_entries(self):
        original = r"C:\Windows;%USERPROFILE%\Tools;;D:\Other"
        entry = r"D:\My Harness\bin"
        updated, added = environment._windows_path(original, entry)
        self.assertTrue(added)
        restored, removed = environment._windows_path(updated, entry, remove=True)
        self.assertTrue(removed)
        self.assertEqual(restored, original)

    def test_unrecognized_receipt_not_overwritten(self):
        state = self.home / "state"
        state.mkdir(parents=True)
        path = state / environment.RECEIPT
        path.write_text('{"product":"other"}')
        with self.assertRaisesRegex(RuntimeError, "unrecognized"):
            self.install()
        self.assertEqual(path.read_text(), '{"product":"other"}')

    def test_removal_does_not_change_unmanaged_text(self):
        text = "export PATH=/my/own/bin:$PATH\n"
        self.assertEqual(environment._replace_block(text, None, set()), text)


if __name__ == "__main__":
    unittest.main()

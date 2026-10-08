"""Exercise installed public launchers, with real subprocesses and isolated homes."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import site
import subprocess
import sys
import tempfile
import unittest
import venv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import install_oh_my_harness as installer
import manager_state


@unittest.skipUnless(shutil.which("git"), "requires Git")
class PublicLauncherContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.user = self.root / "user"
        self.user.mkdir()
        self.home = self.user / "manager with spaces"
        self.repo = self.home / "repo"
        # A copied worktree .git file points outside the fixture and is not an
        # ordinary manager clone. Overlay current edits onto an independent clone.
        subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(ROOT), str(self.repo)], check=True)
        shutil.copytree(ROOT, self.repo, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv"))
        venv.EnvBuilder(with_pip=False, system_site_packages=True).create(self.home / "venv")
        installer.write_launchers(home=self.home, repo=self.repo, dry_run=False)
        self.launcher = self.home / "bin" / ("omh.cmd" if os.name == "nt" else "omh")
        self.env = dict(os.environ, HOME=str(self.user), USERPROFILE=str(self.user),
                        OH_MY_HARNESS_BOOTSTRAP_PYTHON=sys.executable,
                        CODEX_HOME=str(self.user / ".codex"),
                        # A nested venv inherits the base Python's packages,
                        # not the runner venv's tested dependencies.
                        PYTHONPATH=os.pathsep.join(site.getsitepackages()))
        self.env.pop("PYTHONDONTWRITEBYTECODE", None)
        self.env.pop("GIT_OPTIONAL_LOCKS", None)
        state = self.home / "state"
        state.mkdir()
        self.revision = subprocess.check_output(["git", "-C", str(self.repo), "rev-parse", "HEAD"], text=True).strip()
        self.repository = subprocess.check_output(["git", "-C", str(self.repo), "config", "--get", "remote.origin.url"], text=True).strip()
        self.receipt = {"product": "oh-my-harness", "status": "ready",
                        "repository": self.repository, "revision": self.revision, "ref": "main"}
        (state / "install.json").write_text(json.dumps(self.receipt))
        # If dispatch accidentally bootstraps, fail instead of downloading packages.
        (self.repo / "scripts/bootstrap_tooling_env.py").write_text(
            "raise SystemExit('UNEXPECTED MUTATING BOOTSTRAP')\n")

    def run_cli(self, *args):
        return subprocess.run([str(self.launcher), *args], env=self.env,
                              text=True, capture_output=True, timeout=30)

    def snapshot(self, lock=None):
        result = {}
        for path in self.user.rglob("*"):
            key = str(path.relative_to(self.user))
            stat = path.lstat()
            if lock is not None and path == lock.path:
                # Windows byte-range locks deny reads through a second handle.
                # Read via the owning handle so locked-file bytes stay covered.
                lock.handle.seek(0)
                content = hashlib.sha256(lock.handle.read()).hexdigest()
            else:
                content = os.readlink(path) if path.is_symlink() else (
                    hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "directory")
            result[key] = (stat.st_mode, stat.st_mtime_ns, content)
        return result

    def test_help_and_abbreviations_do_not_write(self):
        before = self.snapshot()
        for command in (("status", "--help"), ("repair", "--he"),
                        ("install", "copilot", "--dry-r"),
                        ("refresh", "--d"), ("repair", "--dry")):
            with self.subTest(command=command):
                result = self.run_cli(*command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.snapshot(), before)

    def test_healthy_json_is_pure_and_read_only(self):
        before = self.snapshot()
        for command in ("status", "version"):
            with self.subTest(command=command):
                result = self.run_cli(command, "--json")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["product"], "oh-my-harness")
                self.assertEqual(self.snapshot(), before)

    def test_global_home_abbreviations_preserve_read_only_dispatch(self):
        before = self.snapshot()
        for option in ("--ho", "--hom", "--home"):
            for arguments in ((option, str(self.home)), (f"{option}={self.home}",)):
                with self.subTest(arguments=arguments):
                    result = self.run_cli(*arguments, "status", "--json")
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout)["home"], str(self.home))
                    self.assertEqual(self.snapshot(), before)

    def test_all_diagnostics_available_during_mutation(self):
        with manager_state.ManagerLock(self.home) as lock:
            before = self.snapshot(lock)
            for command in ("status", "version", "check", "doctor"):
                with self.subTest(command=command):
                    result = self.run_cli(command)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(self.snapshot(lock), before)

    def test_broken_runtime_is_explicit_and_never_repaired(self):
        python = self.home / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        python.unlink()
        python.write_text("invalid executable" if os.name == "nt" else
                          "#!/bin/sh\necho broken-runtime >&2\nexit 91\n")
        python.chmod(0o755)
        before = self.snapshot()
        for command in ("status", "version", "check", "doctor"):
            with self.subTest(command=command):
                args = [command, "--json"] if command in {"status", "version"} else [command]
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("omh repair", result.stderr)
                if "--json" in args:
                    self.assertEqual(json.loads(result.stdout)["error"], "runtime_unavailable")
                self.assertEqual(self.snapshot(), before)

    def test_missing_dependencies_fail_without_installing_them(self):
        self.env.pop("PYTHONPATH", None)
        config = self.home / "venv/pyvenv.cfg"
        config.write_text(config.read_text().replace("include-system-site-packages = true",
                                                   "include-system-site-packages = false"))
        before = self.snapshot()
        result = self.run_cli("version", "--j")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["error"], "runtime_unavailable")
        self.assertEqual(self.snapshot(), before)

    def test_harness_validation_failure_is_read_only(self):
        before = self.snapshot()
        for command in ("check", "doctor"):
            result = self.run_cli(command, "copilot")
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("UNEXPECTED MUTATING BOOTSTRAP", result.stderr)
            self.assertEqual(self.snapshot(), before)

    def test_missing_runtime_and_checkout_json_errors(self):
        shutil.rmtree(self.home / "venv")
        for missing_checkout in (False, True):
            if missing_checkout:
                # Move it outside the observed user tree. Git objects may be
                # read-only on Windows; disappearance is the behavior under test.
                self.repo.rename(self.root / "missing repo")
            before = self.snapshot()
            result = self.run_cli("status", "--json")
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)["error"], "runtime_unavailable")
            self.assertEqual(self.snapshot(), before)

    def test_every_dry_run_preserves_files_and_avoids_lock(self):
        state = self.home / "state"
        (state / "install.json").write_text(json.dumps({**self.receipt, "harness": "copilot-cli"}))
        commands = (("install", "copilot"), ("refresh", "copilot"), ("remove", "copilot"),
                    ("repair",), ("manager", "repair"))
        before = self.snapshot()
        for command in commands:
            with self.subTest(command=command):
                result = self.run_cli(*command, "--dry-run")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.snapshot(), before)
                self.assertFalse((state / "manager.lock").exists())
        with manager_state.ManagerLock(self.home) as lock:
            before = self.snapshot(lock)
            for command in commands:
                result = self.run_cli(*command, "--dry-run")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.snapshot(lock), before)


if __name__ == "__main__":
    unittest.main()

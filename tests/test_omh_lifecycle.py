from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import manager_state  # noqa: E402
import omh  # noqa: E402
import omh_bootstrap  # noqa: E402
from sync_harness_instructions import remove_instruction_sync  # noqa: E402


class ManagerStateTests(unittest.TestCase):
    def write_install(self, home: Path, *, status: str = "ready") -> None:
        state = home / "state"
        state.mkdir(parents=True)
        (state / "install.json").write_text(
            json.dumps(
                {
                    "product": "oh-my-harness",
                    "status": status,
                    "repository": "https://example.invalid/oh-my-harness.git",
                    "ref": "main",
                    "revision": "a" * 40,
                    "harness": "codex",
                    "paths": {},
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def test_ready_install_receipt_migrates_default_harness_to_desired_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".oh-my-harness"
            self.write_install(home)
            manager, desired = manager_state.load_or_initialize(
                home,
                repository="ignored",
                revision="b" * 40,
                release_version="1.0.0",
                bundle_identity="sha256:bundle",
                persist=True,
            )
            self.assertEqual(desired["harnesses"], ["codex"])
            self.assertEqual(manager["releaseVersion"], "1.0.0")
            self.assertTrue((home / "state" / "manager.json").is_file())
            self.assertTrue((home / "state" / "desired.json").is_file())

    def test_incomplete_initial_install_does_not_claim_harness_desired(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".oh-my-harness"
            self.write_install(home, status="installing")
            _manager, desired = manager_state.load_or_initialize(
                home,
                repository="ignored",
                revision="b" * 40,
                release_version="1.0.0",
                bundle_identity="sha256:bundle",
                persist=False,
            )
            self.assertEqual(desired["harnesses"], [])

    @unittest.skipIf(os.name == "nt", "nested Windows byte-range lock is process-scoped")
    def test_manager_lock_rejects_a_second_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".oh-my-harness"
            with manager_state.ManagerLock(home):
                with self.assertRaisesRegex(SystemExit, "another oh-my-harness mutation"):
                    with manager_state.ManagerLock(home):
                        pass


class OmhCliTests(unittest.TestCase):
    def registry(self):
        return SimpleNamespace(
            choices=("claude-code", "codex", "zcode"),
            default_harness="codex",
        )

    def test_no_subcommand_is_refresh(self) -> None:
        self.assertEqual(omh._normalize_argv([]), ["refresh"])
        self.assertEqual(
            omh._normalize_argv(["--home", "/tmp/omh", "--yes"]),
            ["--home", "/tmp/omh", "refresh", "--yes"],
        )

    def test_explicit_command_is_not_rewritten(self) -> None:
        self.assertEqual(
            omh._normalize_argv(["install", "zcode"]),
            ["install", "zcode"],
        )

    def test_top_level_help_is_not_rewritten_to_refresh(self) -> None:
        self.assertEqual(omh._normalize_argv(["--help"]), ["--help"])
        self.assertEqual(omh._normalize_argv(["-Help"]), ["--help"])
        self.assertEqual(
            omh._normalize_argv(["--home", "/tmp/omh", "--help"]),
            ["--home", "/tmp/omh", "--help"],
        )

    def test_remove_without_target_does_not_expand_to_all_desired(self) -> None:
        args = argparse.Namespace(targets=[], harness=None, all=False)
        with mock.patch.object(omh, "_load_registry", return_value=self.registry()):
            targets = omh._target_set(
                args,
                desired=("codex", "zcode"),
                mode="remove",
            )
        self.assertEqual(targets, ())

    def test_install_without_target_uses_registry_default(self) -> None:
        args = argparse.Namespace(targets=[], harness=None, all=False)
        with mock.patch.object(omh, "_load_registry", return_value=self.registry()):
            targets = omh._target_set(args, desired=(), mode="install")
        self.assertEqual(targets, ("codex",))

    def test_refresh_repair_is_public_parser_surface(self) -> None:
        parser = omh.build_parser()
        args = parser.parse_args(["refresh", "codex", "--repair"])
        self.assertEqual(args.command, "refresh")
        self.assertEqual(args.targets, ["codex"])
        self.assertTrue(args.repair)

    def test_latest_stable_tag_uses_semver_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
            (repo / "x").write_text("x", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "x"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-qm", "base"], check=True)
            for tag in ("v1.0.0", "v1.2.0", "v1.10.0", "v2.0.0-rc1"):
                subprocess.run(["git", "-C", str(repo), "tag", tag], check=True)
            self.assertEqual(omh._latest_stable_tag(repo), "v1.10.0")


class LifecycleStateBoundaryTests(unittest.TestCase):
    def test_state_context_rejects_checkout_drift_outside_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".oh-my-harness"
            repo = home / "repo"
            repo.mkdir(parents=True)
            (home / "state").mkdir()
            (home / "state" / "install.json").write_text(
                json.dumps(
                    {
                        "product": "oh-my-harness",
                        "status": "ready",
                        "repository": "repo",
                        "ref": "main",
                        "revision": "a" * 40,
                        "harness": "codex",
                        "paths": {},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            manager_state.write_manager(
                home,
                repository="repo",
                revision="a" * 40,
                release_version="1.0.0",
                bundle_identity="sha256:old",
                channel="stable",
                requested_ref="v1.0.0",
            )
            manager_state.atomic_write_json(
                manager_state.desired_file(home),
                {
                    "schemaVersion": manager_state.STATE_SCHEMA_VERSION,
                    "harnesses": ["codex"],
                    "updatePolicy": {"channel": "stable"},
                    "updatedAt": "test",
                },
            )
            with (
                mock.patch.object(omh, "REPO_ROOT", repo),
                mock.patch.object(omh, "_repository", return_value="repo"),
                mock.patch.object(omh, "_revision", return_value="b" * 40),
                mock.patch.object(omh, "_distribution", return_value=("1.0.0", "sha256:new")),
            ):
                with self.assertRaisesRegex(SystemExit, "differs from manager lifecycle state"):
                    omh._state_context(home, persist=False)

    def test_degraded_manager_blocks_normal_mutation_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".oh-my-harness"
            repo = home / "repo"
            repo.mkdir(parents=True)
            (home / "state").mkdir()
            (home / "state" / "install.json").write_text(
                json.dumps(
                    {
                        "product": "oh-my-harness",
                        "status": "ready",
                        "repository": "repo",
                        "ref": "main",
                        "revision": "a" * 40,
                        "harness": "codex",
                        "paths": {},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            manager_state.write_manager(
                home,
                repository="repo",
                revision="a" * 40,
                release_version="1.0.0",
                bundle_identity="sha256:bundle",
                channel="main",
                requested_ref="origin/main",
                status="degraded",
            )
            manager_state.atomic_write_json(
                manager_state.desired_file(home),
                {
                    "schemaVersion": manager_state.STATE_SCHEMA_VERSION,
                    "harnesses": [],
                    "updatePolicy": {"channel": "main"},
                    "updatedAt": "test",
                },
            )
            with (
                mock.patch.object(omh, "REPO_ROOT", repo),
                mock.patch.object(omh, "_repository", return_value="repo"),
                mock.patch.object(omh, "_revision", return_value="a" * 40),
                mock.patch.object(omh, "_distribution", return_value=("1.0.0", "sha256:bundle")),
            ):
                with self.assertRaisesRegex(SystemExit, "lifecycle is degraded"):
                    omh._state_context(home, persist=False)
                manager, _ = omh._state_context(
                    home, persist=False, allow_degraded=True
                )
            self.assertEqual(manager["status"], "degraded")

    def test_active_operation_blocks_normal_mutation_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            (home / "repo").mkdir(parents=True)
            manager = {
                "schemaVersion": manager_state.STATE_SCHEMA_VERSION,
                "product": "oh-my-harness",
                "status": "ready",
                "repository": "repo",
                "channel": "stable",
                "requestedRef": "v1.0.0",
                "revision": "a" * 40,
                "releaseVersion": "1.0.0",
                "bundleIdentity": "sha256:bundle",
            }
            desired = {
                "schemaVersion": manager_state.STATE_SCHEMA_VERSION,
                "harnesses": ["codex"],
                "updatePolicy": {"channel": "stable"},
            }
            with (
                mock.patch.object(omh, "REPO_ROOT", home / "repo"),
                mock.patch.object(omh, "_repository", return_value="repo"),
                mock.patch.object(omh, "_revision", return_value="a" * 40),
                mock.patch.object(omh, "_distribution", return_value=("1.0.0", "sha256:bundle")),
                mock.patch.object(omh, "load_or_initialize", return_value=(manager, desired)),
                mock.patch.object(
                    omh,
                    "load_current_operation",
                    return_value={
                        "command": "update",
                        "phase": "checkout-switched",
                        "operationId": "op-1",
                    },
                ),
            ):
                with self.assertRaisesRegex(SystemExit, "interrupted manager operation"):
                    omh._state_context(home, persist=False)

    def test_read_only_context_can_inspect_active_operation_and_revision_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            (home / "repo").mkdir(parents=True)
            manager = {
                "schemaVersion": manager_state.STATE_SCHEMA_VERSION,
                "product": "oh-my-harness",
                "status": "ready",
                "repository": "repo",
                "channel": "stable",
                "requestedRef": "v1.0.0",
                "revision": "a" * 40,
                "releaseVersion": "1.0.0",
                "bundleIdentity": "sha256:old",
            }
            desired = {
                "schemaVersion": manager_state.STATE_SCHEMA_VERSION,
                "harnesses": ["codex"],
                "updatePolicy": {"channel": "stable"},
            }
            with (
                mock.patch.object(omh, "REPO_ROOT", home / "repo"),
                mock.patch.object(omh, "_repository", return_value="repo"),
                mock.patch.object(omh, "_revision", return_value="b" * 40),
                mock.patch.object(omh, "_distribution", return_value=("1.0.0", "sha256:new")),
                mock.patch.object(omh, "load_or_initialize", return_value=(manager, desired)),
                mock.patch.object(
                    omh,
                    "load_current_operation",
                    return_value={
                        "command": "update",
                        "phase": "checkout-switched",
                        "operationId": "op-1",
                    },
                ),
            ):
                observed, _ = omh._state_context(
                    home,
                    persist=False,
                    allow_manager_drift=True,
                    allow_active_operation=True,
                )
            self.assertEqual(observed["revision"], "a" * 40)

    def test_internal_update_resume_may_cross_only_the_journaled_revision_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".oh-my-harness"
            repo = home / "repo"
            repo.mkdir(parents=True)
            (home / "state").mkdir()
            (home / "state" / "install.json").write_text(
                json.dumps(
                    {
                        "product": "oh-my-harness",
                        "status": "ready",
                        "repository": "repo",
                        "ref": "main",
                        "revision": "a" * 40,
                        "harness": "codex",
                        "paths": {},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            manager_state.write_manager(
                home,
                repository="repo",
                revision="a" * 40,
                release_version="1.0.0",
                bundle_identity="sha256:old",
                channel="stable",
                requested_ref="v1.0.0",
            )
            manager_state.atomic_write_json(
                manager_state.desired_file(home),
                {
                    "schemaVersion": manager_state.STATE_SCHEMA_VERSION,
                    "harnesses": [],
                    "updatePolicy": {"channel": "stable"},
                    "updatedAt": "test",
                },
            )
            with (
                mock.patch.object(omh, "REPO_ROOT", repo),
                mock.patch.object(omh, "_repository", return_value="repo"),
                mock.patch.object(omh, "_revision", return_value="b" * 40),
                mock.patch.object(omh, "_distribution", return_value=("1.0.0", "sha256:new")),
            ):
                manager, _desired = omh._state_context(
                    home, persist=False, allow_manager_drift=True
                )
            self.assertEqual(manager["revision"], "a" * 40)


class UpdateTransactionTests(unittest.TestCase):
    def make_remote_pair(self, root: Path) -> tuple[Path, str, str]:
        remote = root / "remote.git"
        writer = root / "writer"
        home_repo = root / "home" / "repo"
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        subprocess.run(["git", "clone", "-q", str(remote), str(writer)], check=True)
        for repo in (writer,):
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
        (writer / "marker.txt").write_text("old\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(writer), "add", "marker.txt"], check=True)
        subprocess.run(["git", "-C", str(writer), "commit", "-qm", "old"], check=True)
        subprocess.run(["git", "-C", str(writer), "branch", "-M", "main"], check=True)
        subprocess.run(["git", "-C", str(writer), "push", "-qu", "origin", "main"], check=True)
        subprocess.run(["git", "--git-dir", str(remote), "symbolic-ref", "HEAD", "refs/heads/main"], check=True)
        subprocess.run(["git", "clone", "-q", str(remote), str(home_repo)], check=True)
        old = subprocess.check_output(["git", "-C", str(home_repo), "rev-parse", "HEAD"], text=True).strip()
        (writer / "marker.txt").write_text("new\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(writer), "add", "marker.txt"], check=True)
        subprocess.run(["git", "-C", str(writer), "commit", "-qm", "new"], check=True)
        subprocess.run(["git", "-C", str(writer), "push", "-q", "origin", "main"], check=True)
        new = subprocess.check_output(["git", "-C", str(writer), "rev-parse", "HEAD"], text=True).strip()
        return home_repo, old, new

    def seed_state(self, home: Path, repo: Path, old: str) -> None:
        (home / "state").mkdir(parents=True, exist_ok=True)
        (home / "state" / "install.json").write_text(
            json.dumps(
                {
                    "product": "oh-my-harness",
                    "status": "ready",
                    "repository": str(repo.parent.parent / "remote.git"),
                    "ref": "main",
                    "revision": old,
                    "harness": "codex",
                    "paths": {},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        manager_state.write_manager(
            home,
            repository=str(repo.parent.parent / "remote.git"),
            revision=old,
            release_version="1.0.0",
            bundle_identity="sha256:old",
            channel="main",
            requested_ref="origin/main",
        )
        manager_state.atomic_write_json(
            manager_state.desired_file(home),
            {
                "schemaVersion": manager_state.STATE_SCHEMA_VERSION,
                "harnesses": [],
                "updatePolicy": {"channel": "main"},
                "updatedAt": "test",
            },
        )

    def args(self) -> argparse.Namespace:
        return argparse.Namespace(
            home=None, check=False, channel="main", to=None, allow_downgrade=False
        )

    def test_same_revision_update_commits_channel_and_requested_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            repo = home / "repo"
            repo.mkdir(parents=True)
            manager = {
                "repository": "repo",
                "revision": "a" * 40,
                "releaseVersion": "1.0.0",
                "bundleIdentity": "sha256:bundle",
                "channel": "main",
                "requestedRef": "origin/main",
            }
            desired = {
                "harnesses": ["codex"],
                "updatePolicy": {"channel": "main"},
            }
            args = argparse.Namespace(
                home=str(home),
                check=False,
                channel="stable",
                to="v1.0.0",
                allow_downgrade=False,
            )
            with (
                mock.patch.object(omh, "ManagerLock"),
                mock.patch.object(omh, "_state_context", return_value=(manager, desired)),
                mock.patch.object(omh, "_worktree_clean", return_value=True),
                mock.patch.object(omh, "_repository", return_value="repo"),
                mock.patch.object(omh, "_git"),
                mock.patch.object(omh, "_target_revision", return_value=("v1.0.0", "a" * 40)),
                mock.patch.object(omh, "_revision", return_value="a" * 40),
                mock.patch.object(omh, "_validate_update_target", return_value=("1.0.0", "sha256:bundle")),
                mock.patch.object(omh, "write_manager") as write_manager,
                mock.patch.object(omh, "write_desired") as write_desired,
            ):
                self.assertEqual(omh.command_update(args), 0)

            write_manager.assert_called_once_with(
                home,
                repository="repo",
                revision="a" * 40,
                release_version="1.0.0",
                bundle_identity="sha256:bundle",
                channel="stable",
                requested_ref="v1.0.0",
            )
            write_desired.assert_called_once_with(
                home, ("codex",), channel="stable"
            )

    def test_update_commits_new_manager_state_only_after_new_cli_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, old, new = self.make_remote_pair(root)
            home = repo.parent
            self.seed_state(home, repo, old)

            def distribution(path: Path) -> tuple[str, str]:
                revision = subprocess.check_output(
                    ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
                ).strip()
                return ("1.0.0", "sha256:new" if revision == new else "sha256:old")

            def invoke(_repo: Path, _home: Path, command: str, *extra: str):
                self.assertEqual(command, "_resume-update")
                operation_id = extra[extra.index("--operation-id") + 1]
                rc = omh.command_resume_update(
                    argparse.Namespace(home=str(home), operation_id=operation_id)
                )
                return subprocess.CompletedProcess([], rc)

            with (
                mock.patch.object(omh, "REPO_ROOT", repo),
                mock.patch.object(omh, "_distribution", side_effect=distribution),
                mock.patch.object(omh, "_validate_update_target", return_value=("1.0.0", "sha256:new")),
                mock.patch.object(omh, "_bootstrap_tooling"),
                mock.patch.object(omh, "_invoke_internal", side_effect=invoke),
            ):
                omh.command_update(argparse.Namespace(**{**vars(self.args()), "home": str(home)}))

            self.assertEqual(
                subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip(),
                new,
            )
            manager = json.loads(manager_state.manager_file(home).read_text(encoding="utf-8"))
            self.assertEqual(manager["revision"], new)
            self.assertEqual(manager["bundleIdentity"], "sha256:new")
            self.assertFalse(manager_state.current_operation_file(home).exists())

    def test_failed_new_cli_rolls_checkout_and_state_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, old, _new = self.make_remote_pair(root)
            home = repo.parent
            self.seed_state(home, repo, old)
            calls: list[str] = []

            def invoke(_repo: Path, _home: Path, command: str, *extra: str):
                calls.append(command)
                operation_id = extra[extra.index("--operation-id") + 1]
                if command == "_resume-update":
                    return subprocess.CompletedProcess([], 17)
                rc = omh.command_resume_rollback(
                    argparse.Namespace(
                        home=str(home), operation_id=operation_id, detail="test failure"
                    )
                )
                return subprocess.CompletedProcess([], rc)

            with (
                mock.patch.object(omh, "REPO_ROOT", repo),
                mock.patch.object(omh, "_distribution", return_value=("1.0.0", "sha256:old")),
                mock.patch.object(omh, "_validate_update_target", return_value=("1.0.0", "sha256:new")),
                mock.patch.object(omh, "_bootstrap_tooling"),
                mock.patch.object(omh, "_invoke_internal", side_effect=invoke),
            ):
                with self.assertRaisesRegex(SystemExit, "was rolled back"):
                    omh.command_update(argparse.Namespace(**{**vars(self.args()), "home": str(home)}))

            self.assertEqual(calls, ["_resume-update", "_resume-rollback"])
            self.assertEqual(
                subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip(),
                old,
            )
            manager = json.loads(manager_state.manager_file(home).read_text(encoding="utf-8"))
            self.assertEqual(manager["revision"], old)
            self.assertFalse(manager_state.current_operation_file(home).exists())


class RemoveStateTransactionTests(unittest.TestCase):
    def test_remove_failure_preserves_desired_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(
                home=str(Path(tmp) / "home"),
                targets=["codex"],
                harness=None,
                all=False,
                codex_home=None,
                codex=None,
                yes=True,
                dry_run=False,
            )
            desired = {
                "schemaVersion": manager_state.STATE_SCHEMA_VERSION,
                "harnesses": ["codex"],
                "updatePolicy": {"channel": "stable"},
            }
            with (
                mock.patch.object(omh, "ManagerLock"),
                mock.patch.object(omh, "_state_context", return_value=({}, desired)),
                mock.patch.object(omh, "_load_registry", return_value=SimpleNamespace(choices=("codex",), default_harness="codex")),
                mock.patch.object(omh, "_remove_one", side_effect=SystemExit("remove failed")),
                mock.patch.object(omh, "write_desired") as write_desired,
            ):
                with self.assertRaisesRegex(SystemExit, "remove failed"):
                    omh.command_remove(args)
            write_desired.assert_not_called()


class InstructionRemovalTests(unittest.TestCase):
    def test_remove_current_managed_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "AGENTS.md"
            target = root / "target.md"
            source.write_text("managed\n", encoding="utf-8")
            target.write_text("managed\n", encoding="utf-8")
            plan = SimpleNamespace(
                instructions_source=source,
                instructions_target=target,
                harness_id="zcode",
            )
            remove_instruction_sync(plan, dry_run=False)
            self.assertFalse(target.exists())

    def test_remove_refuses_changed_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "AGENTS.md"
            target = root / "target.md"
            source.write_text("managed\n", encoding="utf-8")
            target.write_text("user changed\n", encoding="utf-8")
            plan = SimpleNamespace(
                instructions_source=source,
                instructions_target=target,
                harness_id="zcode",
            )
            with self.assertRaisesRegex(SystemExit, "changed or unmanaged"):
                remove_instruction_sync(plan, dry_run=False)
            self.assertTrue(target.exists())


class BootstrapHelpTests(unittest.TestCase):
    def test_help_bypasses_tooling_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            scripts = home / "repo" / "scripts"
            scripts.mkdir(parents=True)
            (scripts / "omh.py").write_text("pass\n", encoding="utf-8")
            (scripts / "bootstrap_tooling_env.py").write_text("pass\n", encoding="utf-8")
            with mock.patch.object(omh_bootstrap.subprocess, "run") as run:
                run.return_value = subprocess.CompletedProcess([], 0)
                self.assertEqual(
                    omh_bootstrap.main(["--home", str(home), "--help"]),
                    0,
                )
            run.assert_called_once_with(
                [
                    sys.executable,
                    str(scripts / "omh.py"),
                    "--home",
                    str(home),
                    "--help",
                ]
            )


class BootstrapRepairTests(unittest.TestCase):
    def test_bootstrap_can_reconstruct_missing_managed_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "config", "user.email", "test@example.invalid"], check=True)
            subprocess.run(["git", "-C", str(source), "config", "user.name", "Test"], check=True)
            (source / "marker.txt").write_text("manager", encoding="utf-8")
            subprocess.run(["git", "-C", str(source), "add", "marker.txt"], check=True)
            subprocess.run(["git", "-C", str(source), "commit", "-qm", "base"], check=True)
            revision = subprocess.check_output(
                ["git", "-C", str(source), "rev-parse", "HEAD"],
                text=True,
            ).strip()

            home = root / "home"
            (home / "state").mkdir(parents=True)
            (home / "state" / "manager.json").write_text(
                json.dumps(
                    {
                        "repository": str(source),
                        "revision": revision,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            omh_bootstrap._repair_checkout(home)
            self.assertEqual((home / "repo" / "marker.txt").read_text(encoding="utf-8"), "manager")
            head = subprocess.check_output(
                ["git", "-C", str(home / "repo"), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            self.assertEqual(head, revision)


if __name__ == "__main__":
    unittest.main()

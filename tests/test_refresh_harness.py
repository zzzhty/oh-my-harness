from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import refresh_my_codex as refresh  # noqa: E402


class RefreshHarnessCliTests(unittest.TestCase):
    def run_main(self, arguments: list[str]) -> None:
        with mock.patch.object(sys, "argv", ["refresh_my_codex.py", *arguments]):
            refresh.main()

    def test_retired_prune_option_is_rejected_before_any_refresh_work(self) -> None:
        with mock.patch.object(refresh, "load_repo_skill_catalog") as load_catalog:
            with self.assertRaises(SystemExit) as raised:
                self.run_main(["--prune-plugins", "--dry-run"])
        self.assertEqual(raised.exception.code, 2)
        load_catalog.assert_not_called()

    def test_nonempty_codex_prune_plan_requires_confirmation_by_default(self) -> None:
        plan = refresh.CodexPrunePlan(
            configured=frozenset({"retired"}),
            cached=frozenset({"retired"}),
        )
        with mock.patch("builtins.input", return_value="no") as prompt:
            with self.assertRaisesRegex(SystemExit, "was not confirmed"):
                refresh.confirm_codex_prune(
                    plan,
                    marketplace_name="my-codex",
                    confirmation="when-nonempty",
                    dry_run=False,
                    assume_yes=False,
                )
        prompt.assert_called_once()

    def test_yes_confirms_only_the_precomputed_codex_prune_plan(self) -> None:
        plan = refresh.CodexPrunePlan(
            configured=frozenset({"configured-only"}),
            cached=frozenset({"cache-only"}),
        )
        with mock.patch("builtins.input") as prompt:
            refresh.confirm_codex_prune(
                plan,
                marketplace_name="my-codex",
                confirmation="when-nonempty",
                dry_run=False,
                assume_yes=True,
            )
        prompt.assert_not_called()

    def test_legacy_discovery_profile_option_is_rejected(self) -> None:
        with mock.patch.object(refresh, "load_repo_skill_catalog") as load_catalog:
            with self.assertRaises(SystemExit) as raised:
                self.run_main(["--discovery-profile", "universal", "--dry-run"])
        self.assertEqual(raised.exception.code, 2)
        load_catalog.assert_not_called()

    def test_git_marketplace_install_is_pinned_to_validated_checkout_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with (
                mock.patch.object(refresh, "git_remote_source", return_value="git@example/repo.git"),
                mock.patch.object(
                    refresh,
                    "git_remote_ref_status",
                    return_value=(True, "checkout matches ref"),
                ),
                mock.patch.object(refresh, "git_head_revision", return_value="abc123"),
                mock.patch.object(
                    refresh,
                    "ensure_git_marketplace_source",
                    return_value=0,
                ) as ensure_git,
            ):
                binding = refresh.ensure_marketplace_source(
                    "codex",
                    codex_home=Path(tmp) / "codex",
                    marketplace_name="my-codex",
                    git_source="git@example/repo.git",
                    git_ref="main",
                    git_request_explicit=True,
                    local_source=str(REPO_ROOT),
                    env={},
                    dry_run=True,
                )

        self.assertEqual(
            binding,
            refresh.MarketplaceSourceBinding(
                "git",
                "git@example/repo.git",
                "abc123",
            ),
        )
        self.assertEqual(ensure_git.call_args.kwargs["ref"], "abc123")

    def test_explicit_git_ref_mismatch_never_falls_back_to_local_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with (
                mock.patch.object(refresh, "git_remote_source", return_value="git@example/repo.git"),
                mock.patch.object(
                    refresh,
                    "git_remote_ref_status",
                    return_value=(False, "requested ref does not match HEAD"),
                ),
                mock.patch.object(refresh, "ensure_local_marketplace_source") as ensure_local,
            ):
                with self.assertRaisesRegex(
                    SystemExit,
                    "explicit Git marketplace ref is not the validated checkout",
                ):
                    refresh.ensure_marketplace_source(
                        "codex",
                        codex_home=Path(tmp) / "codex",
                        marketplace_name="my-codex",
                        git_source="git@example/repo.git",
                        git_ref="release",
                        git_request_explicit=True,
                        local_source=str(REPO_ROOT),
                        env={},
                        dry_run=True,
                    )

        ensure_local.assert_not_called()

    def test_explicit_git_install_failure_never_falls_back_to_local_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with (
                mock.patch.object(refresh, "git_remote_source", return_value="git@example/repo.git"),
                mock.patch.object(
                    refresh,
                    "git_remote_ref_status",
                    return_value=(True, "checkout matches ref"),
                ),
                mock.patch.object(refresh, "git_head_revision", return_value="abc123"),
                mock.patch.object(refresh, "ensure_git_marketplace_source", return_value=17),
                mock.patch.object(refresh, "ensure_local_marketplace_source") as ensure_local,
            ):
                with self.assertRaisesRegex(SystemExit, "failed with exit code 17"):
                    refresh.ensure_marketplace_source(
                        "codex",
                        codex_home=Path(tmp) / "codex",
                        marketplace_name="my-codex",
                        git_source="git@example/repo.git",
                        git_ref="main",
                        git_request_explicit=True,
                        local_source=str(REPO_ROOT),
                        env={},
                        dry_run=True,
                    )

        ensure_local.assert_not_called()

    def test_automatic_git_install_failure_falls_back_to_canonical_local_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with (
                mock.patch.object(refresh, "git_remote_source", return_value="git@example/repo.git"),
                mock.patch.object(
                    refresh,
                    "git_remote_ref_status",
                    return_value=(True, "checkout matches ref"),
                ),
                mock.patch.object(refresh, "git_head_revision", return_value="abc123"),
                mock.patch.object(refresh, "ensure_git_marketplace_source", return_value=17),
                mock.patch.object(refresh, "ensure_local_marketplace_source") as ensure_local,
            ):
                binding = refresh.ensure_marketplace_source(
                    "codex",
                    codex_home=Path(tmp) / "codex",
                    marketplace_name="my-codex",
                    git_source="git@example/repo.git",
                    git_ref="main",
                    git_request_explicit=False,
                    local_source=str(REPO_ROOT),
                    env={},
                    dry_run=True,
                )

        self.assertEqual(binding, refresh.MarketplaceSourceBinding("local", str(REPO_ROOT)))
        ensure_local.assert_called_once()

    def test_cli_tracks_a_git_ref_as_an_explicit_codex_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            arguments = [
                "--git-ref",
                "release",
                "--codex-home",
                str(root / "codex"),
                "--dry-run",
                "--skip-bootstrap",
                "--skip-agents",
                "--skip-hooks",
                "--skip-doctor",
            ]
            with (
                mock.patch.object(refresh, "require_excluded_skill_roots_clear"),
                mock.patch.object(refresh, "prepare_instruction_sync"),
                mock.patch.object(refresh, "preflight_codex_distribution"),
                mock.patch.object(refresh, "resolve_codex_executable", return_value="/fake/codex"),
                mock.patch.object(refresh, "require_codex_plugin_commands"),
                mock.patch.object(refresh, "_enabled_codex_harness_plugins", return_value=set()),
                mock.patch.object(refresh, "git_remote_source", return_value="git@example/repo.git"),
                mock.patch.object(
                    refresh,
                    "ensure_marketplace_source",
                    side_effect=SystemExit("stop after argument capture"),
                ) as ensure_marketplace,
            ):
                with self.assertRaisesRegex(SystemExit, "stop after argument capture"):
                    self.run_main(arguments)

        self.assertEqual(ensure_marketplace.call_args.kwargs["git_ref"], "release")
        self.assertTrue(ensure_marketplace.call_args.kwargs["git_request_explicit"])

    def test_invalid_marketplace_policy_fails_codex_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            skill = repo / "plugins" / "demo" / "skills" / "one"
            skill.mkdir(parents=True)
            skill.joinpath("SKILL.md").write_text(
                "---\nname: one\ndescription: fixture\n---\n",
                encoding="utf-8",
            )
            manifest = repo / "plugins" / "demo" / ".codex-plugin" / "plugin.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                json.dumps({"name": "demo", "version": "1.0.0", "skills": "./skills/"}),
                encoding="utf-8",
            )
            metadata = repo / ".agents" / "plugins"
            metadata.mkdir(parents=True)
            metadata.joinpath("marketplace.json").write_text(
                json.dumps(
                    {
                        "name": "test",
                        "plugins": [
                            {
                                "name": "demo",
                                "source": {"source": "local", "path": "./plugins/demo"},
                                "policy": {"installation": "INSTALLED_BY_DEFAULT"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            metadata.joinpath("install-manifest.json").write_text(
                json.dumps(
                    {
                        "schemaVersion": 4,
                        "harness": "codex",
                        "marketplace": "test",
                        "plugins": [{"name": "demo", "install": True, "check": True}],
                    }
                ),
                encoding="utf-8",
            )
            catalog = refresh.load_repo_skill_catalog(repo)
            with self.assertRaisesRegex(SystemExit, "installation policy must be 'AVAILABLE'"):
                refresh.preflight_codex_distribution(
                    catalog,
                    codex_home=root / "codex",
                    marketplace_name="test",
                    marketplace_file=metadata / "marketplace.json",
                    manifest_file=metadata / "install-manifest.json",
                )

    def test_retired_skill_mode_option_is_rejected(self) -> None:
        with mock.patch.object(refresh, "load_repo_skill_catalog") as load_catalog:
            with self.assertRaises(SystemExit) as raised:
                self.run_main(["--skill-mode", "mixed", "--dry-run"])
        self.assertEqual(raised.exception.code, 2)
        load_catalog.assert_not_called()

    def test_unknown_harness_fails_before_catalog_load(self) -> None:
        with mock.patch.object(refresh, "load_repo_skill_catalog") as load_catalog:
            with self.assertRaisesRegex(SystemExit, "unknown harness"):
                self.run_main(["--harness", "unknown", "--dry-run"])
        load_catalog.assert_not_called()

    def test_default_harness_is_codex(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            arguments = [
                "--codex-home",
                str(root / "codex"),
                "--dry-run",
                "--skip-bootstrap",
                "--skip-agents",
                "--skip-hooks",
                "--skip-doctor",
            ]
            with (
                mock.patch.object(refresh, "require_excluded_skill_roots_clear"),
                mock.patch.object(refresh, "prepare_instruction_sync"),
                mock.patch.object(refresh, "preflight_codex_distribution"),
                mock.patch.object(
                    refresh,
                    "resolve_codex_executable",
                    side_effect=SystemExit("resolved default Codex harness"),
                ) as resolve,
            ):
                with self.assertRaisesRegex(SystemExit, "resolved default Codex harness"):
                    self.run_main(arguments)
        resolve.assert_called_once()

    def test_default_tooling_venv_follows_the_resolved_codex_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "custom-codex"
            with mock.patch.object(
                refresh,
                "tooling_python_from_args",
                side_effect=SystemExit("captured venv"),
            ) as tooling:
                with self.assertRaisesRegex(SystemExit, "captured venv"):
                    self.run_main(["--codex-home", str(codex_home), "--dry-run"])

        self.assertEqual(tooling.call_args.args[1], codex_home / "venvs" / "my-codex")

    def test_removed_shared_harness_fails_before_catalog_load(self) -> None:
        with mock.patch.object(refresh, "load_repo_skill_catalog") as load_catalog:
            with self.assertRaisesRegex(SystemExit, "unknown harness 'shared'"):
                self.run_main(["--harness", "shared", "--dry-run"])
        load_catalog.assert_not_called()

    def test_native_harness_does_not_read_codex_marketplace_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with (
                mock.patch.object(refresh, "require_excluded_skill_roots_clear"),
                mock.patch.object(
                    refresh,
                    "load_install_manifest",
                    side_effect=AssertionError("Codex manifest must not be read"),
                ),
                mock.patch.object(refresh, "prepare_instruction_sync"),
                mock.patch.object(refresh, "sync_layer") as sync,
                mock.patch.object(refresh, "apply_instruction_sync"),
            ):
                self.run_main(
                    [
                        "--harness",
                        "zcode",
                        "--codex-home",
                        str(Path(tmp) / "codex"),
                        "--dry-run",
                        "--skip-bootstrap",
                    ]
                )
        sync.assert_called_once()

    def test_excluded_root_failure_precedes_instruction_preflight_and_bootstrap(self) -> None:
        with (
            mock.patch.object(
                refresh,
                "require_excluded_skill_roots_clear",
                side_effect=SystemExit("excluded skill root closure failed"),
            ),
            mock.patch.object(refresh, "prepare_instruction_sync") as prepare,
            mock.patch.object(refresh, "run_tooling_bootstrap") as bootstrap,
        ):
            with self.assertRaisesRegex(SystemExit, "excluded skill root closure failed"):
                self.run_main(["--harness", "zcode", "--dry-run"])
        prepare.assert_not_called()
        bootstrap.assert_not_called()

    def test_legacy_bypass_fails_before_bootstrap(self) -> None:
        with mock.patch.object(refresh, "run_tooling_bootstrap") as bootstrap:
            with self.assertRaises(SystemExit) as raised:
                self.run_main(["--skip-agents-skills", "--dry-run"])
        self.assertEqual(raised.exception.code, 2)
        bootstrap.assert_not_called()


if __name__ == "__main__":
    unittest.main()

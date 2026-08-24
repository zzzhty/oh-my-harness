from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath, PureWindowsPath
from unittest import mock

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(ROOT_SCRIPTS))

import update_mattpocock_skills as updater  # noqa: E402


class MattPocockUpdaterTests(unittest.TestCase):
    def write_upstream_skill(
        self,
        source: Path,
        relative: str,
        *,
        explicit_only: bool,
        body: str = "# Upstream body\n",
    ) -> Path:
        skill_name = relative.rstrip("/").rsplit("/", 1)[-1]
        skill_dir = source / relative
        skill_dir.mkdir(parents=True)
        frontmatter = [
            "---",
            f"name: {skill_name}",
            f"description: Upstream description for {skill_name}.",
        ]
        if explicit_only:
            frontmatter.append("disable-model-invocation: true")
        frontmatter.extend(["---", ""])
        (skill_dir / "SKILL.md").write_text(
            "\n".join(frontmatter) + body,
            encoding="utf-8",
        )
        agent = {
            "interface": {
                "display_name": skill_name.replace("-", " ").title(),
                "short_description": f"Use the published {skill_name} workflow",
            }
        }
        if explicit_only:
            agent["policy"] = {"allow_implicit_invocation": False}
        agent_path = skill_dir / "agents" / "openai.yaml"
        agent_path.parent.mkdir()
        agent_path.write_text(
            yaml.safe_dump(agent, sort_keys=False),
            encoding="utf-8",
        )
        return skill_dir

    def write_upstream_source(
        self,
        source: Path,
        skills: list[tuple[str, bool]],
        *,
        version: str = "1.2.3",
    ) -> None:
        manifest = source / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            json.dumps(
                {
                    "name": "mattpocock-skills",
                    "version": version,
                    "skills": [f"./{relative}" for relative, _ in skills],
                }
            ),
            encoding="utf-8",
        )
        (source / "LICENSE").write_text("MIT\n", encoding="utf-8")
        for relative, explicit_only in skills:
            self.write_upstream_skill(
                source,
                relative,
                explicit_only=explicit_only,
                body="Invoke /prototype exactly as upstream wrote it.\n",
            )

    def write_existing_plugin(self, plugin: Path) -> Path:
        manifest = plugin / ".codex-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            json.dumps(
                {
                    "name": "mattpocock-skills",
                    "version": "1.1.0+codex.old-token",
                    "description": "Old package",
                    "skills": "./skills/",
                    "interface": {},
                }
            ),
            encoding="utf-8",
        )
        stale = plugin / "skills" / "stale" / "SKILL.md"
        stale.parent.mkdir(parents=True)
        stale.write_text("# stale\n", encoding="utf-8")
        updater.write_upstream_lock(
            plugin,
            tag="v1.1.0",
            commit="old-upstream-commit",
            skill_names=["stale"],
        )
        return manifest

    def test_repo_owned_entrypoint_targets_existing_plugin(self) -> None:
        self.assertEqual(updater.repo_root(), REPO_ROOT)
        self.assertEqual(
            updater.target_plugin_root(),
            REPO_ROOT / "plugins" / "mattpocock-skills",
        )
        self.assertTrue(updater.target_plugin_root().is_dir())

    def test_skill_tree_digest_is_stable_across_windows_checkout_semantics(self) -> None:
        posix_entries = {
            PurePosixPath("example/SKILL.md"): ("file", b"# Example\n"),
            PurePosixPath("example/agents"): ("directory", None),
            PurePosixPath("example/agents/openai.yaml"): (
                "file",
                b"interface:\n",
            ),
        }
        windows_entries = {
            PureWindowsPath("example/agents"): ("directory", None),
            PureWindowsPath("example/agents/openai.yaml"): (
                "file",
                b"interface:\r\n",
            ),
            PureWindowsPath("example/SKILL.md"): ("file", b"# Example\r\n"),
        }

        with tempfile.TemporaryDirectory() as tmp:
            skills_root = Path(tmp)
            with mock.patch.object(updater, "tree_entries", return_value=posix_entries):
                posix_digest = updater.skill_tree_sha256(skills_root)
            with mock.patch.object(updater, "tree_entries", return_value=windows_entries):
                windows_digest = updater.skill_tree_sha256(skills_root)

        self.assertEqual(windows_digest, posix_digest)

    def test_sync_copies_every_published_skill_without_content_rewrites(self) -> None:
        skills = [
            ("skills/engineering/ask-matt", True),
            ("skills/engineering/setup-matt-pocock-skills", True),
            ("skills/engineering/diagnosing-bugs", False),
            ("skills/productivity/writing-for-agents", False),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repository = root / "repo"
            source = root / "upstream"
            plugin = repository / "plugins" / "mattpocock-skills"
            self.write_upstream_source(source, skills)
            manifest = self.write_existing_plugin(plugin)

            with (
                mock.patch.object(updater, "repo_root", return_value=repository),
                mock.patch.object(updater, "target_plugin_root", return_value=plugin),
            ):
                packaged = updater.sync_from_source(
                    source,
                    tag="v1.2.3",
                    commit="6acc160e4e0cd062",
                    update_identity=False,
                    run_validation=False,
                )

            expected_names = [relative.rsplit("/", 1)[-1] for relative, _ in skills]
            self.assertEqual(packaged, expected_names)
            self.assertEqual(
                {path.name for path in (plugin / "skills").iterdir()},
                set(expected_names),
            )
            for relative, _ in skills:
                name = relative.rsplit("/", 1)[-1]
                self.assertEqual(
                    updater.tree_entries(source / relative),
                    updater.tree_entries(plugin / "skills" / name),
                )

            ask_matt = (plugin / "skills" / "ask-matt" / "SKILL.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("disable-model-invocation: true", ask_matt)
            self.assertIn("Invoke /prototype exactly as upstream wrote it.", ask_matt)
            self.assertTrue(
                (plugin / "skills" / "setup-matt-pocock-skills" / "SKILL.md").is_file()
            )

            plugin_manifest = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(plugin_manifest["version"], "1.2.3+codex.old-token")
            self.assertIn("unchanged upstream", plugin_manifest["interface"]["longDescription"])

            readme = (plugin / "README.md").read_text(encoding="utf-8")
            self.assertIn("`v1.2.3` (`6acc160e4e0cd062`)", readme)
            self.assertIn("copied unchanged", readme)
            self.assertNotIn("Omitted Upstream Skills", readme)

            upstream_lock = json.loads(
                (plugin / ".codex-plugin" / "upstream-lock.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(upstream_lock["schema_version"], 1)
            self.assertEqual(upstream_lock["upstream"]["tag"], "v1.2.3")
            self.assertEqual(
                upstream_lock["upstream"]["commit"], "6acc160e4e0cd062"
            )
            self.assertEqual(
                upstream_lock["published_skills"],
                sorted(expected_names),
            )
            updater.validate_upstream_lock(plugin)

            metadata = json.loads(
                (plugin / ".codex-plugin" / "skill-watcher.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                metadata["skills"]["mattpocock-skills:ask-matt"]["logical_group"],
                "explicit-workflows",
            )
            self.assertEqual(
                metadata["skills"]["mattpocock-skills:diagnosing-bugs"]["logical_group"],
                "implicit-primitives",
            )
            self.assertEqual(
                metadata["legacy_names"]["mattpocock-skills:writing-great-skills"],
                "mattpocock-skills:writing-for-agents",
            )

    def test_native_codex_metadata_must_match_dual_harness_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "plugin"
            skill = plugin / "skills" / "explicit-skill"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\n"
                "name: explicit-skill\n"
                "description: Explicit upstream skill.\n"
                "disable-model-invocation: true\n"
                "---\n",
                encoding="utf-8",
            )
            agent_path = skill / "agents" / "openai.yaml"
            agent_path.parent.mkdir()
            agent_path.write_text(
                "interface:\n"
                "  display_name: Explicit Skill\n"
                "  short_description: Explicit upstream workflow\n",
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit) as raised:
                updater.validate_native_codex_metadata(plugin)
            self.assertIn("invocation policies disagree", str(raised.exception))

    def test_native_codex_metadata_requires_upstream_agent_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "plugin"
            skill = plugin / "skills" / "missing-agent"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: missing-agent\ndescription: Missing metadata.\n---\n",
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit) as raised:
                updater.validate_native_codex_metadata(plugin)
            self.assertIn("missing upstream agents/openai.yaml", str(raised.exception))

    def test_sync_skip_validation_still_preserves_existing_plugin_on_native_metadata_failure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repository = root / "repo"
            source = root / "upstream"
            plugin = repository / "plugins" / "mattpocock-skills"
            skills = [("skills/engineering/implement", True)]
            self.write_upstream_source(source, skills)
            bad_agent = source / skills[0][0] / "agents" / "openai.yaml"
            bad_agent.write_text(
                "interface:\n"
                "  display_name: Implement\n"
                "  short_description: Build work from a spec\n",
                encoding="utf-8",
            )
            self.write_existing_plugin(plugin)
            sentinel = plugin / "keep.txt"
            sentinel.write_text("keep\n", encoding="utf-8")

            with (
                mock.patch.object(updater, "repo_root", return_value=repository),
                mock.patch.object(updater, "target_plugin_root", return_value=plugin),
                self.assertRaises(SystemExit) as raised,
            ):
                updater.sync_from_source(
                    source,
                    tag="v1.2.3",
                    commit="6acc160e4e0cd062",
                    update_identity=False,
                    run_validation=False,
                )

            self.assertIn("invocation policies disagree", str(raised.exception))
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")
            self.assertTrue((plugin / "skills" / "stale" / "SKILL.md").is_file())
            self.assertEqual(list(plugin.parent.glob(".mattpocock-skills.*")), [])

    def test_sync_refuses_to_overwrite_local_skill_tree_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repository = root / "repo"
            source = root / "upstream"
            plugin = repository / "plugins" / "mattpocock-skills"
            self.write_upstream_source(
                source,
                [("skills/engineering/ask-matt", True)],
            )
            self.write_existing_plugin(plugin)
            stale = plugin / "skills" / "stale" / "SKILL.md"
            stale.write_text("# forbidden local edit\n", encoding="utf-8")

            with (
                mock.patch.object(updater, "repo_root", return_value=repository),
                mock.patch.object(updater, "target_plugin_root", return_value=plugin),
                self.assertRaises(SystemExit) as raised,
            ):
                updater.sync_from_source(
                    source,
                    tag="v1.2.3",
                    commit="6acc160e4e0cd062",
                    update_identity=False,
                    run_validation=False,
                )

            self.assertIn("upstream mirror drift detected", str(raised.exception))
            self.assertEqual(
                stale.read_text(encoding="utf-8"),
                "# forbidden local edit\n",
            )
            self.assertFalse((plugin / "skills" / "ask-matt").exists())

    def test_upstream_lock_rejects_direct_skill_edits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "plugin"
            self.write_existing_plugin(plugin)
            (plugin / "skills" / "stale" / "SKILL.md").write_text(
                "# forbidden local edit\n",
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit) as raised:
                updater.validate_upstream_lock(plugin)

            self.assertIn("upstream mirror drift detected", str(raised.exception))

    def test_sync_refuses_target_outside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repository = root / "repo"
            outside_plugin = root / "outside-plugin"
            outside_plugin.mkdir(parents=True)
            sentinel = outside_plugin / "keep.txt"
            sentinel.write_text("keep\n", encoding="utf-8")

            with (
                mock.patch.object(updater, "repo_root", return_value=repository),
                mock.patch.object(updater, "target_plugin_root", return_value=outside_plugin),
                self.assertRaises(SystemExit) as raised,
            ):
                updater.sync_from_source(
                    root / "unused-upstream",
                    tag="v1.2.3",
                    commit="unused",
                    update_identity=False,
                    run_validation=False,
                )

            self.assertIn("outside expected parent", str(raised.exception))
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")

    def test_duplicate_flattened_skill_name_fails_closed(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            updater.flattened_skill_names(
                [
                    "./skills/engineering/example",
                    "./skills/productivity/example",
                ]
            )
        self.assertIn("duplicate flattened skill name", str(raised.exception))

    def test_latest_semver_tag_uses_numeric_order(self) -> None:
        tags = (
            "aaa\trefs/tags/v1.2.3\n"
            "bbb\trefs/tags/v1.10.0\n"
            "ccc\trefs/tags/not-semver\n"
            "ddd\trefs/tags/v1.10.0^{}\n"
        )
        with mock.patch.object(updater, "run", return_value=tags):
            self.assertEqual(updater.latest_semver_tag(), "v1.10.0")

    def test_requested_tag_must_match_upstream_manifest_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            self.write_upstream_source(source, [], version="1.2.2")
            with self.assertRaises(SystemExit) as raised:
                updater.validate_upstream_release(source, "v1.2.3")
            self.assertIn("does not match requested tag", str(raised.exception))

    def test_sync_updates_repository_identity_after_swap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repository = root / "repo"
            source = root / "upstream"
            plugin = repository / "plugins" / "mattpocock-skills"
            self.write_upstream_source(
                source,
                [("skills/engineering/ask-matt", True)],
            )
            self.write_existing_plugin(plugin)

            with (
                mock.patch.object(updater, "repo_root", return_value=repository),
                mock.patch.object(updater, "target_plugin_root", return_value=plugin),
                mock.patch.object(updater, "update_repository_identity") as update_identity,
            ):
                updater.sync_from_source(
                    source,
                    tag="v1.2.3",
                    commit="6acc160e4e0cd062",
                    update_identity=True,
                    run_validation=False,
                )

            update_identity.assert_called_once_with(repository)

    def test_checked_in_v123_package_uses_native_upstream_codex_contract(self) -> None:
        plugin = updater.target_plugin_root()
        manifest = json.loads(
            (plugin / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertTrue(manifest["version"].startswith("1.2.3+codex."))

        expected_skills = {
            "ask-matt",
            "code-review",
            "codebase-design",
            "diagnosing-bugs",
            "domain-modeling",
            "grill-me",
            "grill-with-docs",
            "grilling",
            "handoff",
            "implement",
            "improve-codebase-architecture",
            "prototype",
            "research",
            "resolving-merge-conflicts",
            "setup-matt-pocock-skills",
            "tdd",
            "teach",
            "to-questionnaire",
            "to-spec",
            "to-tickets",
            "triage",
            "wait-what",
            "wayfinder",
            "wizard",
            "writing-for-agents",
        }
        explicit_only_expected = {
            "ask-matt",
            "grill-me",
            "grill-with-docs",
            "handoff",
            "implement",
            "improve-codebase-architecture",
            "setup-matt-pocock-skills",
            "teach",
            "to-questionnaire",
            "to-spec",
            "to-tickets",
            "triage",
            "wait-what",
            "wayfinder",
        }
        skills_root = plugin / "skills"
        packaged = {
            path.name
            for path in skills_root.iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        }
        self.assertEqual(packaged, expected_skills)
        self.assertNotIn("writing-great-skills", packaged)

        explicit_only_actual = {
            name
            for name in packaged
            if updater.skill_is_explicit_only(skills_root / name)
        }
        self.assertEqual(explicit_only_actual, explicit_only_expected)
        updater.validate_package(plugin)

        metadata = json.loads(
            (plugin / ".codex-plugin" / "skill-watcher.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            metadata["legacy_names"]["mattpocock-skills:writing-great-skills"],
            "mattpocock-skills:writing-for-agents",
        )


if __name__ == "__main__":
    unittest.main()

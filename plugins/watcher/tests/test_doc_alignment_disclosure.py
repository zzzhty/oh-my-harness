from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "doc-alignment"
SKILL = SKILL_DIR / "SKILL.md"
ALIGNMENT = SKILL_DIR / "references" / "alignment-reference.md"
WATCHER_AUDIT = SKILL_DIR / "references" / "watcher-audit.md"
WATCHER = SKILL_DIR.parents[1] / ".codex-plugin" / "skill-watcher.json"
WATCHER_SKILLS = SKILL_DIR.parent
MAINTAINER = WATCHER_SKILLS / "skill-maintainer" / "SKILL.md"
PATCH_POLICY = WATCHER_SKILLS / "skill-maintainer" / "references" / "patch-policy.md"
COMPRESSOR = WATCHER_SKILLS / "skill-compressor" / "SKILL.md"
HOUSEKEEPING = WATCHER_SKILLS / "housekeeping" / "SKILL.md"


class DocAlignmentDisclosureTests(unittest.TestCase):
    def test_entry_interface_keeps_mode_safety_and_one_level_pointers(self) -> None:
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn(
            "In implementation mode, update every active path",
            text,
        )
        self.assertIn(
            "In report-only and scheduled modes, inventory drift, collect evidence, "
            "propose bounded fixes",
            text,
        )
        self.assertIn("write only to a Watcher-owned report", text)
        self.assertIn("target repositories remain read-only", text)
        self.assertIn(
            "run only non-mutating commands against target repositories",
            text,
        )
        self.assertIn(
            "The only permitted writes are Watcher-owned report or runtime state",
            text,
        )
        self.assertIn("Only implementation mode repairs root causes", text)
        self.assertIn("Use implementation mode when the user asks", text)
        self.assertIn("references/watcher-audit.md", text)
        self.assertIn("references/alignment-reference.md", text)
        self.assertIn("report-only work must leave target repositories unchanged", text)
        self.assertIn("every triggered reference completion criterion", text)

    def test_watcher_audit_reference_is_complete_for_operations_branch(self) -> None:
        text = WATCHER_AUDIT.read_text(encoding="utf-8")

        self.assertIn("Trigger:", text)
        self.assertIn("scripts/watcher doc doctor", text)
        self.assertIn("scripts/watcher doc commit-counter", text)
        self.assertIn("scripts/watcher doc report", text)
        self.assertIn("scripts/watcher doc audit", text)
        self.assertIn("owner-command", text)
        self.assertIn("authority_paths", text)
        self.assertIn("commit-dependent", text)
        self.assertIn("Completion criterion:", text)

    def test_alignment_reference_owns_classification_surfaces_and_validation(self) -> None:
        text = ALIGNMENT.read_text(encoding="utf-8")

        for role in (
            "**Overview**",
            "**Guide**",
            "**Architecture / Contract**",
            "**Archive**",
            "**Script / Runner**",
            "**Skill**",
        ):
            self.assertIn(role, text)
        for severity in ("`High`", "`Medium`", "`Low`"):
            self.assertIn(severity, text)
        for semantic in (
            "runtime checks: `check_<target>`",
            "Root docs are current overview and execution entry points only",
            "Active index files are navigation and execution posture",
            "Keep `SKILL.md` frontmatter to `name` and `description`",
            "Match validation to the changed surface",
        ):
            self.assertIn(semantic, text)
        self.assertIn("python3 -m compileall -q scripts/watcher_runtime", text)
        self.assertGreaterEqual(text.count("Completion criterion:"), 6)

    def test_callable_and_watcher_identities_remain_unchanged(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        watcher = json.loads(WATCHER.read_text(encoding="utf-8"))

        self.assertIn("name: doc-alignment", skill)
        self.assertIn("watcher:doc-alignment", watcher["skills"])
        aliases = {
            item["value"]
            for item in watcher["skills"]["watcher:doc-alignment"]["aliases"]
        }
        self.assertIn("doc-alignment", aliases)
        self.assertIn("documentation alignment", aliases)


class WatcherSkillInstructionContractTests(unittest.TestCase):
    def test_skill_maintainer_completion_is_reviewable_and_source_preserving(self) -> None:
        skill = MAINTAINER.read_text(encoding="utf-8")
        policy = PATCH_POLICY.read_text(encoding="utf-8")

        for requirement in (
            "target skill",
            "evidence window and event counts",
            "snapshot and proposal paths",
            "exact bounded edit or explicit no-change decision",
            "validation commands and results",
            "human-review boundary",
            "blockers and assumptions",
            "source `SKILL.md` remained unchanged",
        ):
            self.assertIn(requirement, skill)
        self.assertIn("Every proposal must include", policy)
        self.assertNotIn("Every proposal should include", policy)

    def test_skill_compressor_delegates_meaning_changes_to_one_review_owner(self) -> None:
        text = COMPRESSOR.read_text(encoding="utf-8")

        self.assertIn("stop this behavior-preserving workflow", text)
        self.assertIn("route the candidate through `workflow:prompt-strategy-loop`", text)
        self.assertIn("Core Rule is the single owner", text)
        self.assertIn("keep the candidate explicitly unverified", text)
        self.assertNotIn("independent evaluation is required when compression changes", text)

    def test_housekeeping_inventory_example_is_executable_bounded_and_read_only(self) -> None:
        text = HOUSEKEEPING.read_text(encoding="utf-8")
        match = re.search(r"```bash\n(?P<script>.*?)\n```", text, flags=re.DOTALL)
        self.assertIsNotNone(match)
        script = match.group("script")

        self.assertNotIn("<target>", script)
        self.assertIn('git -C "$housekeeping_target" status', script)
        self.assertIn('find "$housekeeping_target"', script)

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir).resolve()
            subprocess.run(
                ["git", "init", "-q", str(target)],
                check=True,
                capture_output=True,
                text=True,
            )
            (target / ".gitignore").write_text(
                "__pycache__/\n.pytest_cache/\nnode_modules/\n.venv/\n",
                encoding="utf-8",
            )
            for relative in (
                "src/__pycache__",
                ".pytest_cache",
                "node_modules/pkg/__pycache__",
                ".venv/lib/__pycache__",
            ):
                (target / relative).mkdir(parents=True)
            (target / "guidance.md").write_text("old-term\n", encoding="utf-8")

            def target_state() -> list[tuple[str, bool, bytes | None]]:
                return sorted(
                    (
                        str(path.relative_to(target)),
                        path.is_dir(),
                        None if path.is_dir() else path.read_bytes(),
                    )
                    for path in target.rglob("*")
                    if ".git" not in path.relative_to(target).parts
                )

            before = target_state()

            env = os.environ.copy()
            env["HOUSEKEEPING_TARGET"] = str(target)
            result = subprocess.run(
                ["bash", "-c", script],
                cwd=target,
                env=env,
                capture_output=True,
                text=True,
            )

            no_match_env = env.copy()
            no_match_env["HOUSEKEEPING_STALE_PATTERN"] = "not-present"
            no_match = subprocess.run(
                ["bash", "-c", script],
                cwd=target,
                env=no_match_env,
                capture_output=True,
                text=True,
            )
            after = target_state()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(no_match.returncode, 0, no_match.stderr)
        self.assertEqual(after, before)
        self.assertIn(str(target / "src" / "__pycache__"), result.stdout)
        self.assertIn(str(target / ".pytest_cache"), result.stdout)
        self.assertNotIn(str(target / "node_modules" / "pkg" / "__pycache__"), result.stdout)
        self.assertNotIn(str(target / ".venv" / "lib" / "__pycache__"), result.stdout)
        self.assertIn("guidance.md:1:old-term", result.stdout)

    def test_housekeeping_inventory_rejects_a_non_git_target(self) -> None:
        text = HOUSEKEEPING.read_text(encoding="utf-8")
        match = re.search(r"```bash\n(?P<script>.*?)\n```", text, flags=re.DOTALL)
        self.assertIsNotNone(match)
        script = match.group("script")

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir).resolve()
            env = os.environ.copy()
            env["HOUSEKEEPING_TARGET"] = str(target)
            result = subprocess.run(
                ["bash", "-c", script],
                cwd=target,
                env=env,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("housekeeping target is not a Git worktree", result.stderr)
        self.assertNotIn("fatal:", result.stderr)


if __name__ == "__main__":
    unittest.main()

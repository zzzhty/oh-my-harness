from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "repo-lessons-lint"
SKILL = SKILL_ROOT / "SKILL.md"
README = ROOT / "README.md"


class RepoLessonsLintTests(unittest.TestCase):
    def test_skill_is_explicit_and_encodes_repeated_mistakes(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        metadata = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        notice = (SKILL_ROOT / "NOTICE.md").read_text(encoding="utf-8")
        frontmatter = skill.split("---", 2)[1]
        body = skill.split("---", 2)[2]

        self.assertIn("explicitly invokes `repo-lessons-lint`", skill)
        self.assertIn("explicitly asks to encode repeated historical mistakes", skill)
        self.assertIn("Ordinary bugfixes and reviews are not a trigger", frontmatter)
        self.assertIn("current repository", body)
        self.assertIn("Do not fan out across other repositories", body)
        self.assertIn("unless the user explicitly requests them", body)
        self.assertIn("at least twice", body)
        self.assertIn("at least two distinct historical commits firsthand", body)
        self.assertIn("change nothing", body)
        self.assertIn("`Violation`", body)
        self.assertIn("`Fix`", body)
        self.assertIn("`Principle`", body)
        self.assertIn("same command", body)
        self.assertIn("may only shrink", body)
        self.assertIn("real pre-fix code", body)
        self.assertIn("current tree passes", body)
        self.assertIn("agent instruction file", body)
        self.assertLess(body.index("**Architecture.**"), body.index("**Types.**"))
        self.assertLess(body.index("**Types.**"), body.index("**A lint or check script.**"))
        self.assertLess(body.index("**A lint or check script.**"), body.index("**A test.**"))
        self.assertLess(body.index("**A test.**"), body.index("**Docs or agent instructions, last.**"))
        self.assertIn("scripts/check_architecture.py", body)
        self.assertIn("scripts/architecture_baseline.json", body)
        self.assertIn("not required names", body)

        for banned in ("Cursor", "Cloud Agent", "gh ", ".cursor/"):
            self.assertNotIn(banned, skill)
        self.assertNotIn("disable-model-invocation", frontmatter)
        self.assertIn("allow_implicit_invocation: false", metadata)
        self.assertIn("$repo-lessons-lint", metadata)
        self.assertIn("Lauren Tan", notice)
        self.assertIn("Copyright (c) 2026 Lauren Tan", notice)
        self.assertIn("MIT License", notice)
        self.assertIn("`correct`", notice)
        self.assertIn("`repo-lessons-lint`", README.read_text(encoding="utf-8"))


    def test_history_is_a_discovery_gate_not_a_persistent_rule_payload(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        discovery = skill.split("## Find classes", 1)[1].split("## Encode", 1)[0]
        output = skill.split("## Rules a check must carry", 1)[1].split("## Report", 1)[0]
        report = skill.split("## Report", 1)[1]
        self.assertIn("separate occurrences of the same mistake", discovery)
        self.assertIn("Other evidence can help", discovery)
        self.assertIn("does not replace them", discovery)
        self.assertIn("do not add a rule for it", discovery)
        self.assertIn("`Principle` explains why the rule exists", output)
        self.assertIn("do not include the supporting commits in check output", output)
        self.assertIn("historical evidence, commit IDs, or commit links in `AGENTS.md`", output)
        self.assertNotIn("Every rule cites", output)
        self.assertNotIn("includes the two commit ids", output)
        self.assertIn("may cite the two supporting commits in the one-time change report", report)
        self.assertIn("no persistent evidence record is required", report)


if __name__ == "__main__":
    unittest.main()

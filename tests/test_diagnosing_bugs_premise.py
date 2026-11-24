"""The diagnosing-bugs premise check stays explicit about its source."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "plugins" / "mattpocock-skills" / "skills" / "diagnosing-bugs"


class DiagnosingBugsPremiseTests(unittest.TestCase):
    def test_repeated_premise_is_tested_before_another_fix(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        notice = (SKILL_ROOT / "NOTICE.md").read_text(encoding="utf-8")
        readme = (ROOT / "plugins" / "mattpocock-skills" / "README.md").read_text(encoding="utf-8")
        frontmatter = skill.split("---", 2)[1]
        fix = skill.split("## Fix and verify", 1)[1].split("When repair is authorized", 1)[0]

        self.assertIn("two or more fixes that share one premise", fix)
        self.assertIn("write the premise in one sentence", fix)
        self.assertIn("test it directly before another fix", fix)
        self.assertIn("follow that evidence", fix)
        self.assertIn("Remove the condition that produces the failure", fix)
        self.assertIn("instead of compensating", fix)
        self.assertIn("NOTICE.md", fix)
        self.assertNotIn("disable-model-invocation", frontmatter)
        self.assertIn("principle-attack-the-premise", notice)
        self.assertIn("Copyright (c) 2026 Lauren Tan", notice)
        self.assertIn("MIT License", notice)
        self.assertIn("principle-attack-the-premise", readme)
        self.assertIn("skills/diagnosing-bugs/NOTICE.md", readme)
        self.assertIn("does not change the skill's invocation policy", readme)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


class BlastRadiusTests(unittest.TestCase):
    def test_skill_proves_out_of_diff_breakage_without_removed_companions(self) -> None:
        skill_root = ROOT / "skills" / "blast-radius"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        metadata = (skill_root / "agents" / "openai.yaml").read_text(encoding="utf-8")
        notice = (skill_root / "NOTICE.md").read_text(encoding="utf-8")
        frontmatter = skill.split("---", 2)[1]
        body = skill.split("---", 2)[2]

        self.assertIn("explicitly invokes `blast-radius`", skill)
        self.assertIn("Ordinary review is not a trigger", frontmatter)
        self.assertIn("mattpocock-skills:code-review", body)
        self.assertIn("mattpocock-skills:research", body)
        self.assertIn("**What it does.**", body)
        self.assertIn("**The key fact.**", body)
        self.assertIn("**Risks.**", body)
        self.assertIn("**Cleared.**", body)
        self.assertIn("`file:line`", body)
        for level in ("**Said.**", "**Cited.**", "**Walked.**", "**Ran.**", "**Reproduced.**"):
            self.assertIn(level, body)
        self.assertIn("runs the real code", body)
        self.assertIn("unproven", body)

        for banned in ("`why`", "`how`", "`arena`", "unslop", ".cursor/", "Cursor"):
            self.assertNotIn(banned, skill)
        self.assertNotIn("disable-model-invocation", frontmatter)
        self.assertIn("allow_implicit_invocation: false", metadata)
        self.assertIn("$blast-radius", metadata)
        self.assertIn("Lauren Tan", notice)
        self.assertIn("Copyright (c) 2026 Lauren Tan", notice)
        self.assertIn("`why`", notice)
        self.assertIn("`how`", notice)
        self.assertIn("`arena`", notice)
        self.assertIn("`unslop`", notice)
        self.assertIn("`blast-radius`", README.read_text(encoding="utf-8"))


class CreateVerificationSkillTests(unittest.TestCase):
    def test_generator_uses_the_project_skill_location_and_proves_one_feature(self) -> None:
        skill_root = ROOT / "skills" / "create-verification-skill"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        metadata = (skill_root / "agents" / "openai.yaml").read_text(encoding="utf-8")
        notice = (skill_root / "NOTICE.md").read_text(encoding="utf-8")
        frontmatter = skill.split("---", 2)[1]
        example = skill_root / "references" / "feature-map-example"

        self.assertIn("explicitly invokes `create-verification-skill`", skill)
        self.assertIn("Ordinary testing is not a trigger", frontmatter)
        self.assertIn("existing skill location", skill)
        self.assertIn("ask which one to use", skill)
        self.assertIn("ask for a directory before writing", skill)
        self.assertIn("Do not invent a product-specific default path", skill)
        for section in ("**Launch.**", "**Doctor.**", "**Drive.**", "**Evidence.**", "**Cleanup.**", "**Helpers.**"):
            self.assertIn(section, skill)
        self.assertIn("references/feature-map-example/", skill)
        self.assertIn("`Sub-features`", skill)
        self.assertIn("`How to get to it (user POV)`", skill)
        self.assertIn("`Driving it with <driver>`", skill)
        self.assertIn("`Gotchas`", skill)
        self.assertIn("end to end once", skill)
        self.assertIn("evidence still exists", skill)
        self.assertNotIn("maintain-verification-skill", skill)
        self.assertNotIn(".cursor/skills", skill)
        self.assertNotIn("Cursor", skill)
        self.assertNotIn("disable-model-invocation", frontmatter)
        self.assertIn("allow_implicit_invocation: false", metadata)
        self.assertIn("$create-verification-skill", metadata)

        readme = (example / "README.md").read_text(encoding="utf-8")
        self.assertIn("shape specimen", readme)
        for name in ("create-note.md", "search.md"):
            feature = (example / name).read_text(encoding="utf-8")
            self.assertIn("## Sub-features", feature)
            self.assertIn("## How to get to it (user POV)", feature)
            self.assertIn("## Driving it with control-notes", feature)
            self.assertIn("## Gotchas", feature)
        self.assertIn("Lauren Tan", notice)
        self.assertIn("Copyright (c) 2026 Lauren Tan", notice)
        self.assertIn("maintain-verification-skill", notice)
        self.assertIn("`create-verification-skill`", README.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

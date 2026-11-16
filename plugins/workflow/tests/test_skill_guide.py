"""skill-guide navigates available skills and does not keep a routing menu."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

import repo_skill_catalog  # noqa: E402


WORKFLOW = ROOT / "plugins/workflow"
GUIDE = WORKFLOW / "skills/skill-guide"
MATT = ROOT / "plugins/mattpocock-skills"


class SkillGuideTests(unittest.TestCase):
    def test_explicit_navigation_skill_replaces_ask_matt(self) -> None:
        catalog = repo_skill_catalog.load_repo_skill_catalog(ROOT)
        names = {source.name for source in catalog.sources}
        matt = {source.name for source in catalog.sources if source.plugin == "mattpocock-skills"}
        workflow = {source.name for source in catalog.sources if source.plugin == "workflow"}
        self.assertEqual(len(names), 28)
        self.assertEqual(len(matt), 16)
        self.assertEqual(len(workflow), 8)
        self.assertNotIn("ask-matt", names)
        self.assertNotIn("pr", names)
        self.assertNotIn("scope-discipline", names)
        self.assertIn("skill-guide", workflow)
        self.assertFalse((MATT / "skills/ask-matt").exists())

        skill = (GUIDE / "SKILL.md").read_text(encoding="utf-8")
        frontmatter, body = skill.split("---", 2)[1:]
        metadata = (GUIDE / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn("name: skill-guide", frontmatter)
        self.assertIn("disable-model-invocation: true", frontmatter)
        self.assertIn("allow_implicit_invocation: false", metadata)
        self.assertIn("no skill", body)
        self.assertIn("Reading does not invoke the skill.", body)
        self.assertIn("does not activate it", body)
        self.assertIn("Do not search the web", body)
        for package in ("maintenance", "workflow", "mattpocock-skills"):
            self.assertIn(f"`{package}`", body)
        self.assertNotIn("ask-matt", skill)
        self.assertNotIn("`/pr`", skill)
        self.assertNotIn("scope-discipline", skill)

    def test_body_does_not_hardcode_other_catalog_skills(self) -> None:
        catalog = repo_skill_catalog.load_repo_skill_catalog(ROOT)
        body = (GUIDE / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[2]
        mentioned = sorted(source.name for source in catalog.sources if source.name != "skill-guide" and source.name in body)
        self.assertEqual(mentioned, [])

    def test_adapted_boundaries_keep_matt_attribution(self) -> None:
        notice = (GUIDE / "NOTICE.md").read_text(encoding="utf-8")
        readme = (WORKFLOW / "README.md").read_text(encoding="utf-8")
        self.assertIn("ask-matt", notice)
        self.assertIn("Copyright (c) 2026 Matt Pocock", notice)
        self.assertIn("MIT License", notice)
        self.assertIn("skills/skill-guide/NOTICE.md", readme)
        self.assertIn("`skill-guide`", readme)
        matt_readme = (MATT / "README.md").read_text(encoding="utf-8")
        self.assertIn("16 engineering skills", matt_readme)
        self.assertIn("`workflow:skill-guide`", matt_readme)
        self.assertNotIn("$mattpocock-skills:ask-matt", matt_readme)
        prompt = (MATT / ".codex-plugin/plugin.json").read_text(encoding="utf-8")
        self.assertNotIn("ask-matt", prompt)
        self.assertIn("$workflow:skill-guide", prompt)

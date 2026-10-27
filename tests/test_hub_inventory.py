"""Check actual consumers and resources of the pure Hub composition."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from repo_skill_catalog import load_repo_skill_catalog


class HubInventoryTests(unittest.TestCase):
    def test_only_consumed_runtime_groups_and_owned_resources_are_declared(self):
        manifest = json.loads((ROOT / 'content-manifest.json').read_text())
        catalog = load_repo_skill_catalog(ROOT)
        skills = {f'{s.plugin}:{s.name}': s for s in catalog.sources}
        self.assertEqual(len(skills), 29)
        self.assertNotIn('maintenance:skill-maintainer', skills)
        self.assertIn('mattpocock-skills:writing-for-agents', skills)
        self.assertEqual({s.name for s in catalog.sources if s.plugin == 'maintenance'},
                         {'doc-alignment', 'housekeeping', 'skill-compressor'})
        self.assertEqual(manifest['historicalIdentities'], {})
        groups = {group['id']: group for group in manifest['runtimeGroups']}
        self.assertEqual(set(groups), set(manifest['runtimeBindings'].values()))
        self.assertEqual(set(groups), {'maintenance', 'workflow'})
        for identity in manifest['runtimeBindings']:
            self.assertIn(identity, skills)
            self.assertTrue(list((skills[identity].path / 'scripts').glob('*.py')), identity)
        for group in groups.values():
            self.assertEqual(group['imports'], [])
            self.assertIsNone(group['requirementsLock'])
        self.assertFalse((ROOT / 'runtimes/watcher').exists())
        self.assertEqual(list((ROOT / 'plugins').glob('*/.codex-plugin/skill-watcher.json')), [])
        doc = skills['maintenance:doc-alignment'].path
        for resource in ('scripts/audit_docs.py', 'scripts/doc_alignment/audit_repo.py',
                         'scripts/doc_alignment/report.py', 'scripts/check_planning_tree.py',
                         'references/doc-audit.md', 'config/repos.example.json'):
            self.assertTrue((doc / resource).is_file(), resource)


if __name__ == '__main__':
    unittest.main()

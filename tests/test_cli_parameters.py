"""Harness alias parsing and uninstall launcher retention."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

try:
    import test_standalone as fixture
except ModuleNotFoundError:
    from tests import test_standalone as fixture

st = fixture.st


class CliParameterTests(unittest.TestCase):
    setUpClass = classmethod(fixture.StandaloneTests.setUpClass.__func__)
    tearDownClass = classmethod(fixture.StandaloneTests.tearDownClass.__func__)

    def setUp(self):
        fixture.StandaloneTests.setUp(self)
        # Windows Path.home() follows USERPROFILE. Keep it on the fixture home.
        self.user_home = Path(os.environ['HOME'])
        profile = patch.dict(os.environ, {'USERPROFILE': str(self.user_home)})
        profile.start()
        self.addCleanup(profile.stop)

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = st.main(['--source', str(self.source), '--home', str(self.home), *argv])
            except SystemExit as stopped:
                code = stopped.code
        return code, out.getvalue(), err.getvalue()

    def install_named(self, *argv):
        code, out, err = self.run_cli(
            'install', *argv, '--python', sys.executable,
            '--external-venv', self.prepared['root'], '--offline', '--json')
        self.assertEqual(code, 0, out + err)
        return json.loads(out)

    def managed_bytes(self):
        paths = [
            self.user_home / '.codex' / st.OWNER,
            self.user_home / '.codex' / 'AGENTS.md',
            self.user_home / '.codex' / 'skills' / 'example' / 'SKILL.md',
            self.user_home / '.claude' / st.OWNER,
            self.user_home / '.claude' / 'CLAUDE.md',
            self.home / st.TARGETS_FILE,
            self.home / 'runtime-state.json',
            self.home / 'shim.json',
            self.user_home / '.local' / 'bin' / 'omh',
        ]
        return {str(path): path.read_bytes() if path.is_file() else None for path in paths}

    def test_claude_alias_uninstalls_only_claude_code_and_keeps_the_launcher(self):
        self.install_named()
        self.install_named('--harness', 'claude')
        codex, claude = self.user_home / '.codex', self.user_home / '.claude'
        instructions = (self.source / 'agents' / 'global-instructions.md').read_bytes()
        self.assertEqual((claude / 'CLAUDE.md').read_bytes(), instructions)
        self.assertFalse((claude / 'AGENTS.md').exists())
        self.assertEqual((codex / 'AGENTS.md').read_bytes(), instructions)
        indexed = json.loads((self.home / st.TARGETS_FILE).read_bytes())
        self.assertEqual({item['harness'] for item in indexed.values()}, {'codex', 'claude-code'})
        code, out, err = self.run_cli('status', '--json')
        self.assertEqual(code, 0, out + err)
        self.assertEqual({item['harness'] for item in json.loads(out)['targets']}, {'codex', 'claude-code'})
        code, out, err = self.run_cli('status', 'claude', '--json')
        self.assertEqual(code, 0, out + err)
        self.assertEqual({item['harness'] for item in json.loads(out)['targets']}, {'claude-code'})
        code, out, err = self.run_cli('status', '--harness', 'claude', '--json')
        self.assertEqual(code, 0, out + err)
        self.assertEqual({item['harness'] for item in json.loads(out)['targets']}, {'claude-code'})
        codex_bytes = (codex / 'AGENTS.md').read_bytes()
        code, out, err = self.run_cli('uninstall', 'claude')
        self.assertEqual(code, 0, out + err)
        self.assertNotIn('omh command', out)
        self.assertFalse((claude / st.OWNER).exists())
        self.assertFalse((claude / 'CLAUDE.md').exists())
        self.assertEqual((codex / 'AGENTS.md').read_bytes(), codex_bytes)
        self.assertTrue((codex / st.OWNER).is_file())
        indexed = json.loads((self.home / st.TARGETS_FILE).read_bytes())
        self.assertEqual({item['harness'] for item in indexed.values()}, {'codex'})
        shim = self.user_home / '.local' / 'bin' / 'omh'
        if os.name != 'nt':
            self.assertTrue(shim.is_file())
            self.assertIn(st.SHIM_MARKER.encode(), shim.read_bytes())
            self.assertTrue((self.home / 'shim.json').is_file())
        self.install_named('claude')
        code, out, err = self.run_cli('uninstall', '--harness', 'claude', '--json')
        self.assertEqual(code, 0, out + err)
        payload = json.loads(out)
        self.assertIn('changed', payload)
        self.assertNotIn('launcherRemoved', payload)
        self.assertFalse((claude / st.OWNER).exists())
        self.assertTrue((codex / st.OWNER).is_file())
        if os.name != 'nt':
            self.assertTrue(shim.is_file())
            self.assertTrue((self.home / 'shim.json').is_file())

    def test_uninstall_without_a_target_exits_2_and_leaves_files(self):
        self.install_named()
        before = self.managed_bytes()
        code, out, err = self.run_cli('uninstall')
        self.assertEqual(code, 2, out + err)
        self.assertEqual(out, '')
        self.assertIn('codex, claude-code, grok, or claude', err)
        self.assertEqual(self.managed_bytes(), before)
        for argv in (('uninstall', 'copilot'), ('uninstall', 'claude', '--harness', 'grok')):
            code, out, err = self.run_cli(*argv)
            self.assertEqual(code, 2, out + err)
            self.assertEqual(out, '')
            self.assertEqual(self.managed_bytes(), before, argv)

    def test_harness_uninstall_leaves_the_omh_command(self):
        self.install_named()
        runtime = self.home / 'runtime-state.json'
        venv = Path(self.prepared['root'])
        shim = self.user_home / '.local' / 'bin' / 'omh'
        code, out, err = self.run_cli('uninstall', 'codex')
        self.assertEqual(code, 0, out + err)
        self.assertNotIn('omh command', out)
        self.assertFalse((self.user_home / '.codex' / st.OWNER).exists())
        self.assertTrue(runtime.is_file())
        self.assertTrue(venv.is_dir())
        if os.name != 'nt':
            self.assertTrue(shim.is_file())
            self.assertTrue((self.home / 'shim.json').is_file())
        self.install_named()
        code, out, err = self.run_cli('uninstall', '--harness', 'codex', '--json')
        self.assertEqual(code, 0, out + err)
        payload = json.loads(out)
        self.assertIn('changed', payload)
        self.assertNotIn('launcherRemoved', payload)
        self.assertTrue(runtime.is_file())
        if os.name != 'nt':
            self.assertTrue(shim.is_file())

    def test_self_uninstall_removes_only_the_omh_command(self):
        self.install_named()
        runtime = self.home / 'runtime-state.json'
        shim = self.user_home / '.local' / 'bin' / 'omh'
        code, out, err = self.run_cli('self')
        self.assertEqual(code, 2, out + err)
        code, out, err = self.run_cli('self', 'uninstall', 'claude')
        self.assertEqual(code, 2, out + err)
        self.assertTrue((self.user_home / '.codex' / st.OWNER).is_file())
        if os.name == 'nt':
            code, out, err = self.run_cli('self', 'uninstall')
            self.assertEqual(code, 0, out + err)
            self.assertIn('no omh command to remove', out)
            self.assertTrue(runtime.is_file())
            return
        code, out, err = self.run_cli('self', 'uninstall')
        self.assertEqual(code, 0, out + err)
        self.assertIn('removed the omh command', out)
        self.assertFalse(shim.exists())
        self.assertFalse((self.home / 'shim.json').exists())
        self.assertTrue((self.user_home / '.codex' / st.OWNER).is_file())
        self.assertTrue(runtime.is_file())
        code, out, err = self.run_cli('self', 'uninstall', '--json')
        self.assertEqual(code, 0, out + err)
        self.assertIs(json.loads(out)['removed'], False)
        shim.parent.mkdir(parents=True, exist_ok=True)
        shim.write_text('#!/bin/sh\necho other tool\n', encoding='utf-8')
        (self.home / 'shim.json').write_text(json.dumps({
            'binDir': str(shim.parent), 'path': str(shim),
            'source': str(self.source), 'python': sys.executable}), encoding='utf-8')
        code, out, err = self.run_cli('self', 'uninstall')
        self.assertEqual(code, 1, out + err)
        self.assertIn('HARNESS_CONFLICT', err)
        self.assertTrue(shim.is_file())
        self.assertIn('other tool', shim.read_text(encoding='utf-8'))
        self.assertTrue((self.home / 'shim.json').is_file())

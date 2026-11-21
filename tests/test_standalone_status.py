"""Synthetic checks for harness filtering and installer verification."""
import os
import shutil
import unittest

import test_standalone as fixture


class StandaloneStatusTests(unittest.TestCase):
    # Reuse the synthetic target and release fixtures, not the parent test suite.
    setUpClass = classmethod(fixture.StandaloneTests.setUpClass.__func__)
    tearDownClass = classmethod(fixture.StandaloneTests.tearDownClass.__func__)
    setUp = fixture.StandaloneTests.setUp
    call = fixture.StandaloneTests.call
    call_overview = fixture.StandaloneTests.call_overview
    install = fixture.StandaloneTests.install
    bootstrap_installer_fixture = fixture.StandaloneTests.bootstrap_installer_fixture

    def exercise_installer_verification_failure(self, argv):
        work, home, user_home, git, pinned, installer, env = self.bootstrap_installer_fixture(argv)
        self.assertEqual(installer().returncode, 0)
        # Make the downloaded CLI return an unhealthy status after a real refresh.
        # This fault is in the synthetic upstream, never in user state.
        cli = work/'omh/standalone.py'
        cli.write_text(cli.read_text(encoding='utf-8').replace(
            "        if args.command == 'status':\n",
            "        if args.command == 'status':\n            return 1\n"),
            encoding='utf-8')
        skill = work/'plugins/workflow/skills/example/SKILL.md'
        skill.write_text(skill.read_text(encoding='utf-8')+'Refreshed before verification\n', encoding='utf-8')
        git('add','-A'); git('commit','-q','-m','fixture failure'); git('tag','v0.2.0')
        git('push','--quiet',env['OMH_REPO'],'refs/tags/v0.2.0')
        result = installer(OMH_VERSION='v0.2.0',OMH_REF_URL=str(pinned('v0.2.0')))
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode,0,output)
        self.assertIn('Target writes completed',output)
        self.assertIn('verification failed for codex',output)
        self.assertNotIn('done: v0.2.0',output)
        self.assertIn('Refreshed before verification',
            (user_home/'.codex/skills/example/SKILL.md').read_text(encoding='utf-8'))

    @unittest.skipIf(os.name=='nt','POSIX bootstrap script')
    def test_installer_verification_failure_sh(self):
        self.exercise_installer_verification_failure(['/bin/sh',str(fixture.ROOT/'install.sh')])

    def test_installer_verification_failure_ps1(self):
        program = shutil.which('powershell') or shutil.which('pwsh')
        if program is None: self.skipTest('Windows bootstrap requires powershell or pwsh')
        self.exercise_installer_verification_failure([program,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(fixture.ROOT/'install.ps1')])

    def test_status_filters_explicit_harness_without_changing_schema(self):
        self.install()
        second = self.root/'claude secondary/skills'
        self.assertEqual(self.call('install','--harness','claude-code','--skills-root',str(second))[0],0)
        (second/'example/SKILL.md').write_text('drift', encoding='utf-8')
        code, unfiltered = self.call_overview()
        self.assertEqual(code,1)
        self.assertEqual(len(unfiltered['targets']),2)
        code, filtered = self.call_overview('--harness','codex')
        self.assertEqual(code,0)
        self.assertEqual(set(filtered),set(unfiltered))
        self.assertEqual(filtered['targets'],[t for t in unfiltered['targets'] if t['harness']=='codex'])
        code, filtered = self.call_overview('--harness','claude-code')
        self.assertEqual(code,1)
        self.assertEqual(filtered['targets'],[t for t in unfiltered['targets'] if t['harness']=='claude-code'])
        code, missing = self.call_overview('--harness','grok')
        self.assertEqual(code,1)
        self.assertEqual(missing['targets'],[])

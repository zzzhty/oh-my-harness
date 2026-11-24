"""Content CLI behavior when manager.json names the installed binary."""
import contextlib
import hashlib
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


class ManagerRecordTests(unittest.TestCase):
    setUpClass = classmethod(fixture.StandaloneTests.setUpClass.__func__)
    tearDownClass = classmethod(fixture.StandaloneTests.tearDownClass.__func__)

    def setUp(self):
        fixture.StandaloneTests.setUp(self)

    def call(self, command, *extra):
        return fixture.StandaloneTests.call(self, command, *extra)

    def call_overview(self, *extra):
        return fixture.StandaloneTests.call_overview(self, *extra)

    def install(self):
        return fixture.StandaloneTests.install(self)

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = st.main(['--source', str(self.source), '--home', str(self.home), *argv])
            except SystemExit as stopped:
                code = stopped.code
        return code, out.getvalue(), err.getvalue()

    def record(self, path, digest, version='9.9.9'):
        return {
            'schemaVersion': 1,
            'kind': 'binary',
            'binDir': str(path.parent),
            'path': str(path),
            'source': str(self.source),
            'python': sys.executable,
            'pythonDigest': 'abc',
            'digest': digest,
            'binaryVersion': version,
        }

    def test_matching_digest_skips_the_shim_and_status_reports_the_binary(self):
        self.install()
        user_home = self.root / 'userhome'
        self.assertEqual(Path.home(), user_home)
        binary = user_home / '.local' / 'bin' / 'omh'
        binary.parent.mkdir(parents=True, exist_ok=True)
        payload = b'\x7fELF omh-test-binary\n'
        binary.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        record = self.record(binary, digest)
        (self.home / 'manager.json').write_bytes(json.dumps(record).encode())
        sentinel = b'{"sentinel":true}\n'
        (self.home / 'shim.json').write_bytes(sentinel)
        code, result = self.call('refresh')
        self.assertEqual(code, 0, result)
        self.assertEqual(binary.read_bytes(), payload)
        self.assertEqual((self.home / 'shim.json').read_bytes(), sentinel)
        code, overview = self.call_overview()
        self.assertEqual(code, 0, overview)
        launcher = overview['launcher']
        self.assertEqual(launcher['kind'], 'binary')
        self.assertEqual(launcher['digest'], digest)
        self.assertEqual(launcher['binaryVersion'], '9.9.9')
        for key in ('binDir', 'path', 'source', 'python'):
            self.assertEqual(launcher[key], record[key])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            text_code = st.main(['status', '--source', str(self.source), '--home', str(self.home)])
        self.assertEqual(text_code, 0)
        self.assertIn('9.9.9', output.getvalue())
        self.assertIn('→', output.getvalue())

    @unittest.skipIf(os.name == 'nt', 'POSIX launcher shim')
    def test_mismatched_manager_digest_still_conflicts_before_a_receipt(self):
        binary = Path.home() / '.local' / 'bin' / 'omh'
        binary.parent.mkdir(parents=True)
        payload = b'not a shim\n'
        binary.write_bytes(payload)
        self.home.mkdir()
        record = self.record(binary, '0' * 64)
        (self.home / 'manager.json').write_bytes(json.dumps(record).encode())
        code, result = self.call('install')
        self.assertNotEqual(code, 0, result)
        self.assertEqual(result['error']['code'], 'HARNESS_CONFLICT')
        self.assertFalse((self.skills.parent / st.OWNER).exists())
        self.assertEqual(binary.read_bytes(), payload)
        self.assertFalse((self.home / 'shim.json').exists())

    def test_status_keeps_the_shim_when_the_manager_digest_does_not_match(self):
        self.install()
        if os.name == 'nt':
            self.skipTest('POSIX launcher shim')
        shim = json.loads((self.home / 'shim.json').read_bytes())
        binary = Path.home() / '.local' / 'bin' / 'omh'
        binary.write_bytes(b'changed-binary')
        record = self.record(binary, '0' * 64)
        (self.home / 'manager.json').write_bytes(json.dumps(record).encode())
        code, overview = self.call_overview()
        self.assertEqual(code, 0, overview)
        self.assertEqual(overview['launcher']['path'], shim['path'])
        self.assertNotIn('kind', overview['launcher'])

    def test_update_does_not_exec_the_shell_when_manager_json_exists(self):
        home = self.root / 'managed home'
        repo = home / 'repo'
        (repo / '.git').mkdir(parents=True)
        (home / 'manager.json').write_bytes(b'{}\n')
        with patch.object(st.subprocess, 'call', return_value=0) as delegate:
            err = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                code = st.main(['update', '--source', str(repo), '--home', str(home)])
        self.assertEqual(code, 1)
        delegate.assert_not_called()
        payload = json.loads(err.getvalue())
        self.assertEqual(payload['error']['code'], 'OMH_ENVIRONMENT_INVALID')

    def test_python_self_uninstall_ignores_a_binary_manager_record(self):
        self.home.mkdir()
        binary = self.root / 'bin' / 'omh'
        binary.parent.mkdir()
        payload = b'rust-binary'
        binary.write_bytes(payload)
        record = self.record(binary, hashlib.sha256(payload).hexdigest())
        (self.home / 'manager.json').write_bytes(json.dumps(record).encode())
        code, out, err = self.run_cli('self', 'uninstall', '--json')
        self.assertEqual(code, 0, out + err)
        self.assertEqual(json.loads(out)['removed'], False)
        self.assertEqual(binary.read_bytes(), payload)
        self.assertTrue((self.home / 'manager.json').is_file())

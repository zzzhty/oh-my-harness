"""Standalone lifecycle and the shared runtime protocol use synthetic targets only."""
import contextlib
import io
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from omh import standalone as st
rt = st.rt

SPEC = dict(id='workflow', minimumPython=[3,11], imports=[], requirementsLock=None)
HELPER = '''import json, os, sys
from pathlib import Path
print(json.dumps({'argv':sys.argv[1:], 'prefix':sys.prefix, 'env':{k:os.environ.get(k) for k in ('PYTHONPATH','PYTHONHOME','VIRTUAL_ENV')}}))
'''

def environment_snapshot(root):
    return {p.relative_to(root).as_posix(): ('link',os.readlink(p)) if p.is_symlink() else ('file',p.read_bytes())
            for p in root.rglob('*') if p.is_file() or p.is_symlink()}

class StandaloneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env_temp = tempfile.TemporaryDirectory(prefix='OMH TEST runtime 空间 ')
        cls.env_root = Path(cls.env_temp.name).resolve()
        cls.prepared = rt.prepare(dict(protocol=1, spec=SPEC, bundleRoot=str(ROOT), python=sys.executable,
            deploymentRoot=str(cls.env_root/'runtimes'), externalVenv=None, offline=True, wheelCache=str(cls.env_root/'wheels')))
    @classmethod
    def tearDownClass(cls): cls.env_temp.cleanup()
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="OMH TEST target ' $() 空间 ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        home_environment = patch.dict(os.environ, {'HOME': str(self.root/'userhome')})
        home_environment.start(); self.addCleanup(home_environment.stop)
        self.source, self.home, self.skills = self.root/'source', self.root/'manager', self.root/'client/skills'
        skill = self.source/'plugins/workflow/skills/example'
        (skill/'scripts').mkdir(parents=True)
        (skill/'SKILL.md').write_text('---\nname: example\ndescription: example\n---\nExample\n')
        (skill/'scripts/helper.py').write_text(HELPER)
        (self.source/'content-manifest.json').write_text(json.dumps(dict(schemaVersion=1, product='omh-content',
            compositions={'default':['workflow']}, packages=[dict(name='workflow',path='plugins/workflow',kind='skills')],
            runtimeGroups=[SPEC], runtimeBindings={'workflow:example':'workflow'})))
        agents = self.source/'agents'
        agents.mkdir()
        (agents/'global-instructions.md').write_text('# Global Instructions\nTest authority line.\n')
    def call(self, command, *extra):
        output = io.StringIO()
        arguments = ['--source',str(self.source),'--home',str(self.home),'--skills-root',str(self.skills),
            '--python',sys.executable,'--external-venv',self.prepared['root'],'--offline',*extra]
        if command == 'status': arguments.append('--json')
        with contextlib.redirect_stdout(output):
            code = st.main([command, *arguments])
        return code, json.loads(output.getvalue())
    def call_overview(self, *extra):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = st.main(['status','--source',str(self.source),'--home',str(self.home),'--json',*extra])
        return code, json.loads(output.getvalue())
    def install(self):
        code,result=self.call('install')
        self.assertEqual(code,0,result)
        return result
    def launcher(self, *args, override=None, extra_env=None):
        env = {k:v for k,v in os.environ.items() if k not in ('OMH_PYTHON','PYTHONHOME','PYTHONPATH','VIRTUAL_ENV')}
        env['PATH']=''
        if override is not None: env['OMH_PYTHON']=override
        env.update(extra_env or {})
        base=self.skills.parent/'.omh-runtime'
        if os.name == 'nt':
            program=shutil.which('powershell') or shutil.which('pwsh')
            argv=[program,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(base/'run.ps1')]
        else: argv=['/bin/sh', str(base/'run.sh')]
        return subprocess.run([*argv,'workflow',str(self.skills/'example/scripts/helper.py'),*args],
            cwd=self.root,env=env,capture_output=True,text=True,timeout=30)
    def test_read_only_plan_and_status_do_not_create_directories(self):
        code,result = self.call('status')
        self.assertEqual(code,1)  # Not installed yet: reported, still read-only.
        self.assertEqual(result['targets'][0]['state'],'missing')
        self.assertGreater(len(self.call('plan')[1]['changes']),0)
        self.assertFalse(self.home.exists()); self.assertFalse(self.skills.parent.exists())
    def test_global_instructions_are_projected_protected_and_uninstalled(self):
        self.install()
        instructions = self.skills.parent/'AGENTS.md'
        source = self.source/'agents/global-instructions.md'
        self.assertEqual(instructions.read_bytes(), source.read_bytes())
        receipt = json.loads((self.skills.parent/st.OWNER).read_text())
        self.assertIn('AGENTS.md', receipt['slots']); self.assertIn('AGENTS.md', receipt['files'])
        self.assertEqual(self.call('plan')[1]['changes'], [])
        instructions.write_text('# user override\n')
        code,result = self.call('update')
        self.assertNotEqual(code,0,result)
        self.assertEqual(result['error']['code'],'HARNESS_CONFLICT')
        self.assertIn('User-modified', result['error']['message'])
        instructions.write_bytes(source.read_bytes())
        self.assertEqual(self.call('update')[0],0)
        self.assertEqual(self.call('uninstall')[0],0)
        self.assertFalse(instructions.exists())
        for name,text in (('AGENTS.md','unowned'), ('AGENTS.override.md','shadow')):
            skills = self.root/f"conflict {name}/skills"; skills.mkdir(parents=True)
            (skills.parent/name).write_text(text)
            code,result = self.call('install','--skills-root',str(skills))
            self.assertNotEqual(code,0,result)
            self.assertEqual(result['error']['code'],'HARNESS_CONFLICT')
    def test_claude_code_target_uses_its_native_instructions_name(self):
        skills = self.root/'claude/skills'; skills.mkdir(parents=True)
        code,result = self.call('install','--harness','claude-code','--skills-root',str(skills))
        self.assertEqual(code,0,result)
        self.assertTrue((skills.parent/'CLAUDE.md').is_file())
        self.assertFalse((skills.parent/'AGENTS.md').exists())
        self.assertEqual((skills.parent/'CLAUDE.md').read_bytes(),(self.source/'agents/global-instructions.md').read_bytes())
    def test_grok_target_defaults_to_grok_root_and_shadows_conflict(self):
        def grok_call(command, *extra):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = st.main([command,'--source',str(self.source),'--home',str(self.home),
                    '--python',sys.executable,'--external-venv',self.prepared['root'],'--offline',
                    '--harness','grok',*extra])
            return code, json.loads(output.getvalue())
        # No --skills-root: the default resolves under the patched HOME.
        code,result = grok_call('install')
        self.assertEqual(code,0,result)
        grok = Path.home()/'.grok'
        self.assertTrue((grok/'skills/example/SKILL.md').is_file())
        self.assertEqual((grok/'AGENTS.md').read_bytes(),(self.source/'agents/global-instructions.md').read_bytes())
        self.assertEqual(grok_call('uninstall')[0],0)
        for shadow in ('Claude.md','AGENT.md'):
            (grok/shadow).write_text('# other rules\n')
            code,result = grok_call('install')
            self.assertNotEqual(code,0,result)
            self.assertEqual(result['error']['code'],'HARNESS_CONFLICT')
            self.assertFalse((grok/'skills/sop').exists() and (grok/'skills/example').exists())
            (grok/shadow).unlink()
    @unittest.skipIf(os.name=='nt','POSIX launcher shim')
    def test_launcher_shim_lifecycle(self):
        self.install()
        shim = Path.home()/'.local/bin/omh'
        self.assertTrue(shim.is_file()); self.assertTrue(os.access(shim,os.X_OK))
        record = json.loads((self.home/'shim.json').read_text())
        self.assertEqual(shim.read_bytes(), st.shim_script(Path(record['source']), Path(record['python'])))
        result = subprocess.run([str(shim),'status','--home',str(self.home),'--skills-root',str(self.skills),'--json'],
            env={'PATH':''},capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(json.loads(result.stdout)['targets'][0]['owner'],'omh')
        self.assertEqual(self.call('update')[0],0)
        self.assertEqual(self.call('uninstall')[0],0)
        self.assertFalse(shim.exists()); self.assertFalse((self.home/'shim.json').exists())
        shim.parent.mkdir(parents=True,exist_ok=True)
        shim.write_text('#!/bin/sh\necho other tool\n')
        code,result = self.call('install')
        self.assertNotEqual(code,0,result)
        self.assertEqual(result['error']['code'],'HARNESS_CONFLICT')
        self.assertIn('Unowned',result['error']['message'])
        self.assertFalse((self.skills.parent/st.OWNER).exists())
    @unittest.skipIf(os.name=='nt','POSIX launcher shim')
    def test_launcher_shim_imports_from_a_hostile_source_path(self):
        source = str(self.source)
        self.assertIn("'", source)
        self.assertIn('$()', source)
        self.assertIn('空间', source)
        self.install()
        shim = Path.home()/'.local/bin/omh'
        script = shim.read_text(encoding='utf-8')
        self.assertIn('空间', script)
        self.assertNotIn('\\u7a7a', script)
        self.assertIn('$()', script)
        self.assertIn(shlex.quote(source), script)
        env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
        env['PATH'] = ''
        result = subprocess.run([str(shim), '--help'], env=env, capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('usage', result.stdout.lower())
    def test_status_json_matches_runtime_summary(self):
        self.install()
        code, result = self.call_overview()
        self.assertEqual(code, 0, result)
        self.assertEqual([item['id'] for item in result['runtimes']], ['workflow'])
        self.assertRegex(result['runtimes'][0]['version'], r'^3\.\d+')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            text_code = st.main(['status', '--source', str(self.source), '--home', str(self.home)])
        self.assertEqual(text_code, 0)
        text = output.getvalue()
        self.assertIn(f"workflow({result['runtimes'][0]['version']})", text)
        self.assertIn('—', text)
        if os.name != 'nt': self.assertIn('→', text)
    def test_home_lock_refuses_competing_index_update(self):
        self.home.mkdir(parents=True)
        program = (
            'import sys\nfrom pathlib import Path\nfrom omh import standalone as st\n'
            'try:\n'
            '    st.remember_target(Path(sys.argv[1]), Path(sys.argv[2]), "codex", Path(sys.argv[3]), True)\n'
            'except st.rt.RuntimeFailure as error:\n'
            '    print(error.code)\n'
            '    raise SystemExit(1)\n'
        )
        with rt.lock(self.home / st.HOME_LOCK):
            result = subprocess.run([sys.executable, '-B', '-c', program, str(self.home), str(self.root/'t'), str(self.root/'skills')],
                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('HARNESS_RUNTIME_BUSY', result.stdout)
        st.remember_target(self.home, self.root/'one', 'codex', self.root/'one'/'skills', True)
        st.remember_target(self.home, self.root/'two', 'claude-code', self.root/'two'/'skills', True)
        recorded = json.loads((self.home / st.TARGETS_FILE).read_text())
        self.assertEqual(set(recorded), {str(self.root/'one'), str(self.root/'two')})
    def test_stdout_reconfigure_failure_is_a_json_error(self):
        class Stream(io.TextIOBase):
            def __init__(self):
                super().__init__()
                self.parts = []
            def write(self, text):
                self.parts.append(text)
                return len(text)
            def reconfigure(self, **kwargs):
                raise OSError('refused')
        stream = Stream()
        with contextlib.redirect_stdout(stream):
            code = st.main(['status', '--home', str(self.home)])
        self.assertEqual(code, 1)
        payload = json.loads(''.join(stream.parts))
        self.assertEqual(payload['error']['code'], 'OMH_INVALID')
        self.assertIn('stdout encoding', payload['error']['message'])
    def test_stdlib_group_does_not_install_pip(self):
        root = Path(self.prepared['root'])
        pip = root / ('Scripts/pip.exe' if os.name == 'nt' else 'bin/pip')
        self.assertFalse(pip.exists())
        self.assertTrue((root / 'pyvenv.cfg').is_file())
    @unittest.skipIf(os.name=='nt','POSIX launcher shim')
    def test_launcher_shim_honors_an_explicit_bin_directory(self):
        bin_dir = self.root/'custom bin 空间'
        code,result = self.call('install','--bin-dir',str(bin_dir))
        self.assertEqual(code,0,result)
        self.assertTrue((bin_dir/'omh').is_file())
        self.assertFalse((Path.home()/'.local/bin').exists())
        code,result = self.call('update','--bin-dir','relative/bin')
        self.assertNotEqual(code,0,result)
        self.assertIn('absolute',result['error']['message'])
    def test_status_overview_lists_every_target_and_reports_anomalies(self):
        second = self.root/'claude/skills'; second.mkdir(parents=True)
        self.install()
        self.assertEqual(self.call('install','--harness','claude-code','--skills-root',str(second))[0],0)
        code,result = self.call_overview()
        self.assertEqual(code,0,result)
        listed = {item['target']: item for item in result['targets']}
        self.assertEqual(set(listed), {str(self.skills.parent), str(second.parent)})
        self.assertTrue(all(item['state']=='installed' for item in listed.values()))
        self.assertEqual(listed[str(second.parent)]['harness'],'claude-code')
        (self.skills/'example/SKILL.md').write_text('drifted\n')
        code,result = self.call_overview()
        self.assertNotEqual(code,0)
        drifted = [item for item in result['targets'] if item['target']==str(self.skills.parent)][0]
        self.assertEqual(drifted['modified'],{'skills/example/SKILL.md':'modified'})
        (self.skills/'example/SKILL.md').unlink()
        self.assertEqual(self.call('uninstall')[0],0)
        code,result = self.call_overview()
        self.assertEqual([item['target'] for item in result['targets']],[str(second.parent)])
    def test_status_overview_classifies_foreign_and_deleted_targets(self):
        foreign = self.root/'foreign/skills'; foreign.mkdir(parents=True)
        self.home.mkdir(parents=True,exist_ok=True)
        (foreign.parent/st.OWNER).write_text(json.dumps(dict(owner='someone-else',manager='elsewhere')))
        (self.home/st.TARGETS_FILE).write_text(json.dumps({str(foreign.parent): dict(harness='codex',skillsRoot=str(foreign))}))
        code,result = self.call_overview()
        self.assertNotEqual(code,0)
        self.assertEqual(result['targets'][0]['state'],'foreign')
        (foreign.parent/st.OWNER).unlink()
        code,result = self.call_overview()
        self.assertNotEqual(code,0)
        self.assertEqual(result['targets'][0]['state'],'missing')
    def test_status_text_output_is_human_readable(self):
        self.install()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = st.main(['status','--source',str(self.source),'--home',str(self.home)])
        self.assertEqual(code,0)
        text = output.getvalue()
        self.assertIn(str(self.skills.parent),text)
        self.assertIn('installed',text)
        self.assertIn('managed files',text)
        self.assertIn('summary: 1 target, all clean',text)
    def test_future_session_executes_without_source_or_environment_binding(self):
        self.install()
        shutil.rmtree(self.source)
        argv=['space arg','中文',"quote'",'"quoted"','','C:\\path with spaces\\', '$(no shell)']
        result=self.launcher(*argv)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        value=json.loads(result.stdout)
        self.assertEqual(value['argv'],argv)
        self.assertEqual(Path(value['prefix']),Path(self.prepared['root']))
    def test_override_is_fail_closed_and_python_environment_is_sanitized(self):
        self.install()
        for override in ('', 'python', str(self.root/'missing'), str(Path(sys.base_prefix)/('python.exe' if os.name=='nt' else 'bin/python3'))):
            result=self.launcher(override=override)
            self.assertNotEqual(result.returncode,0,result.stdout)
        result=self.launcher(extra_env=dict(PYTHONPATH=str(self.root/'injection'),PYTHONHOME=str(self.root/'wrong'),VIRTUAL_ENV='wrong'))
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(json.loads(result.stdout)['env'],dict(PYTHONPATH=None,PYTHONHOME=None,VIRTUAL_ENV=None))
        self.assertEqual(self.launcher(override=self.prepared['python']).returncode,0)
    def test_repeat_update_uninstall_and_external_environment_preservation(self):
        before=environment_snapshot(Path(self.prepared['root']))
        self.install()
        self.assertEqual(self.call('install')[1]['changed'],0)
        self.assertEqual(self.call('plan')[1]['changes'],[])
        authored=self.source/'plugins/workflow/skills/example/SKILL.md'
        authored.write_text(authored.read_text()+'Updated\n')
        self.assertEqual(self.call('update')[0],0)
        self.assertIn('Updated',(self.skills/'example/SKILL.md').read_text())
        self.assertEqual(self.call('uninstall')[0],0)
        self.assertEqual(self.call('uninstall')[1]['changed'],0)
        self.assertFalse((self.skills.parent/st.OWNER).exists())
        self.assertFalse((self.skills/'example').exists())
        self.assertEqual(environment_snapshot(Path(self.prepared['root'])),before)
    def test_update_removes_obsolete_directories_and_remains_idempotent(self):
        nested=self.source/'plugins/workflow/skills/example/old/nested'
        nested.mkdir(parents=True); (nested/'resource.txt').write_text('old')
        self.install()
        shutil.rmtree(self.source/'plugins/workflow/skills/example/old')
        self.assertEqual(self.call('update')[0],0)
        self.assertFalse((self.skills/'example/old').exists())
        self.assertEqual(self.call('plan')[1]['changes'],[])
        self.assertEqual(self.call('update')[1]['changed'],0)
    def test_user_modified_managed_file_is_protected(self):
        self.install()
        path=self.skills/'example/SKILL.md'
        path.write_text('user edit')
        for operation in ('update','uninstall'):
            code,result=self.call(operation)
            self.assertEqual(code,1,result)
            self.assertEqual(result['error']['code'],'HARNESS_CONFLICT')
            self.assertEqual(path.read_text(),'user edit')
    def test_missing_files_are_restored_and_unrelated_content_is_preserved(self):
        self.install()
        path=self.skills/'example/SKILL.md'; original=path.read_bytes()
        path.unlink()
        user_file=self.skills/'example/user.txt'; user_file.write_text('user')
        user_dir=self.skills/'example/user empty'; user_dir.mkdir()
        self.assertEqual(self.call('status')[1]['targets'][0]['modified']['skills/example/SKILL.md'],'missing')
        with patch.object(st,'plan',wraps=st.plan) as planned:
            self.assertEqual(self.call('update')[0],0)
            self.assertEqual(planned.call_count,1)
        self.assertEqual(path.read_bytes(),original)
        self.assertEqual(self.call('uninstall')[0],0)
        self.assertEqual(user_file.read_text(),'user'); self.assertTrue(user_dir.is_dir())
        self.assertFalse(path.exists())
    def test_update_can_install_an_absent_target_within_manager_home(self):
        self.home=self.root/'manager'
        self.skills=self.home/'clients/codex/skills'
        self.assertEqual(self.call('update')[0],0)
        self.assertTrue((self.skills/'example/SKILL.md').is_file())
    def test_existing_mixed_directory_accepts_nonconflicting_managed_files(self):
        user_file=self.skills/'example/my notes.txt'
        user_file.parent.mkdir(parents=True); user_file.write_text('user notes')
        self.install()
        self.assertEqual(self.call('uninstall')[0],0)
        self.assertEqual(user_file.read_text(),'user notes')
    def test_hardlinked_files_do_not_require_in_place_writes(self):
        self.install()
        path=self.skills/'example/SKILL.md'
        original=path.read_bytes(); user_copy=self.root/'user copy'
        os.link(path,user_copy)
        authored=self.source/'plugins/workflow/skills/example/SKILL.md'
        authored.write_bytes(original+b'Updated\n')
        self.assertEqual(self.call('update')[0],0)
        self.assertEqual(user_copy.read_bytes(),original)
        self.assertEqual(path.read_bytes(),original+b'Updated\n')
    def test_other_manager_owner_cannot_be_taken_over(self):
        self.skills.parent.mkdir(parents=True)
        for owner in ('foreign','omh'):
            (self.skills.parent/st.OWNER).write_text(json.dumps(dict(schemaVersion=1,owner=owner,manager=str(self.root/'other'),target=str(self.skills.parent))))
            self.assertEqual(self.call('install')[1]['error']['code'],'HARNESS_OWNER_CONFLICT')
            self.assertFalse(self.home.exists())
    def test_inert_native_cache_is_not_an_owner_but_native_installation_is(self):
        native=self.skills.parent/'plugins/cache/oh-my-harness/workflow'
        native.mkdir(parents=True); (native/'cached.txt').write_text('inert cache')
        (self.skills.parent/'config.toml').write_text('[marketplaces.oh-my-harness]\nsource_type = "local"\nsource = "cache"\n')
        self.install()
        self.assertEqual(self.call('uninstall')[0],0)
        self.assertEqual((native/'cached.txt').read_text(),'inert cache')
        config=self.skills.parent/'config.toml'
        config.write_text('[plugins."workflow@oh-my-harness"]\nenabled = true\n')
        self.assertEqual(self.call('install')[1]['error']['code'],'HARNESS_OWNER_CONFLICT')
        self.assertFalse((self.skills.parent/st.OWNER).exists())
    def test_unrelated_invalid_client_config_does_not_block_skill_projection(self):
        self.skills.parent.mkdir(parents=True)
        config=self.skills.parent/'config.toml'; config.write_text('unrelated malformed = [')
        self.install()
        self.assertEqual(config.read_text(),'unrelated malformed = [')
    def test_user_files_outside_owned_slots_survive(self):
        self.skills.parent.mkdir(parents=True)
        unrelated=self.skills.parent/'settings.json'; unrelated.write_text('user')
        self.install(); self.assertEqual(self.call('uninstall')[0],0)
        self.assertEqual(unrelated.read_text(),'user')
    def test_runtime_only_prepare_has_no_target_or_installed_receipt(self):
        code,value=self.call('prepare')
        self.assertEqual(code,0,value)
        self.assertFalse(self.skills.parent.exists())
        self.assertFalse((self.home/'installed.json').exists())
    def test_shared_target_lock_refuses_competing_process(self):
        with rt.lock(self.skills.parent/st.LOCK):
            result=subprocess.run([sys.executable,'-B','-m','omh','install','--source',str(self.source),'--home',str(self.home),'--skills-root',str(self.skills), '--python',sys.executable,'--external-venv',self.prepared['root'],'--offline'],cwd=ROOT,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,1)
            self.assertEqual(json.loads(result.stdout)['error']['code'],'HARNESS_RUNTIME_BUSY')
            self.assertFalse(self.home.exists())
    def test_failed_first_install_recovers_and_can_retry(self):
        original=rt.atomic
        failed=False
        def injected(path, content):
            nonlocal failed
            if path == self.skills.parent/st.OWNER and not failed:
                failed=True
                raise OSError('injected receipt write failure')
            return original(path,content)
        with patch.object(rt,'atomic',side_effect=injected):
            self.assertEqual(self.call('install')[0],1)
        self.assertFalse((self.skills/'example').exists())
        self.assertFalse((self.skills.parent/'.omh-runtime').exists())
        self.install()
    def test_hard_interruption_rollback_and_post_crash_edit_protection(self):
        self.install()
        old=st.tree(self.skills)
        (self.source/'plugins/workflow/skills/example/scripts/helper.py').write_text(HELPER+'# new revision\n')
        program='''import os,sys\nfrom pathlib import Path\nfrom omh import standalone as st\noriginal=st.rt.atomic\ndef interrupt(path,content):\n    if path.name==st.OWNER: os._exit(71)\n    return original(path,content)\nst.rt.atomic=interrupt\nst.main(sys.argv[1:])\n'''
        args=['update','--source',str(self.source),'--home',str(self.home),'--skills-root',str(self.skills), '--python',sys.executable,'--external-venv',self.prepared['root'],'--offline']
        result=subprocess.run([sys.executable,'-B','-c',program,*args],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,71,result.stdout+result.stderr)
        helper=self.skills/'example/scripts/helper.py'
        new=helper.read_bytes(); helper.write_text('post crash user edit')
        self.assertEqual(self.call('recover')[1]['error']['code'],'HARNESS_RECOVERY_CONFLICT')
        self.assertEqual(helper.read_text(),'post crash user edit')
        helper.write_bytes(new)
        self.assertEqual(self.call('recover')[0],0)
        self.assertEqual(st.tree(self.skills),old)
        self.assertEqual(self.call('update')[0],0)
    def test_committed_recovery_does_not_reject_later_user_edits(self):
        self.install()
        authored=self.source/'plugins/workflow/skills/example/SKILL.md'
        authored.write_text(authored.read_text()+'Updated\n')
        journal=st.journal_path(self.home,self.skills.parent)
        original=Path.unlink
        def interrupted_cleanup(path,*args,**kwargs):
            if path==journal: raise OSError('injected after commit')
            return original(path,*args,**kwargs)
        with patch.object(Path,'unlink',interrupted_cleanup):
            self.assertEqual(self.call('update')[0],1)
        self.assertTrue(json.loads(journal.read_bytes())['committed'])
        installed=self.skills/'example/SKILL.md'; installed.write_text('later user edit')
        self.assertEqual(self.call('recover')[0],0)
        self.assertEqual(installed.read_text(),'later user edit')
        self.assertFalse(journal.exists())
    @unittest.skipUnless(os.name=='posix','POSIX cleanup replacement fixture')
    def test_committed_cleanup_preserves_linked_or_file_replacement_paths(self):
        for kind in ('symlink','file'):
            with self.subTest(kind=kind):
                nested=self.source/'plugins/workflow/skills/example/old'
                nested.mkdir(exist_ok=True); (nested/'resource.txt').write_text('old')
                self.install()
                journal=st.journal_path(self.home,self.skills.parent)
                original=Path.unlink
                def interrupted_cleanup(path,*args,**kwargs):
                    if path==journal: raise OSError('injected after commit')
                    return original(path,*args,**kwargs)
                with patch.object(Path,'unlink',interrupted_cleanup):
                    self.assertEqual(self.call('uninstall')[0],1)
                installed=self.skills/'example'
                outside=self.root/('user directory '+kind); (outside/'old').mkdir(parents=True)
                if kind=='symlink': installed.symlink_to(outside,target_is_directory=True)
                else: installed.write_text('user file')
                self.assertEqual(self.call('recover')[0],0)
                self.assertTrue((outside/'old').is_dir())
                if kind=='symlink': self.assertTrue(installed.is_symlink())
                else: self.assertEqual(installed.read_text(),'user file')
                installed.unlink()
    @unittest.skipUnless(os.name=='posix','POSIX symlink fixture')
    def test_linked_target_and_source_fail_before_writes(self):
        actual=self.root/'elsewhere'; actual.mkdir()
        self.skills.parent.symlink_to(actual,target_is_directory=True)
        self.assertEqual(self.call('install')[0],1)
        self.assertEqual(list(actual.iterdir()),[])

class RuntimeTests(unittest.TestCase):
    def test_failed_process_keeps_stderr_and_stdout_tails(self):
        with self.assertRaises(rt.RuntimeFailure) as caught:
            rt.run_process(sys.executable, ['-c', 'import sys; sys.stderr.write("pip exploded\\n"); raise SystemExit(3)'])
        self.assertIn('stderr:', str(caught.exception))
        self.assertIn('pip exploded', str(caught.exception))
        with self.assertRaises(rt.RuntimeFailure) as caught:
            rt.run_process(sys.executable, ['-c', 'import sys; sys.stdout.write("ensurepip missing\\n"); raise SystemExit(1)'])
        self.assertIn('stdout:', str(caught.exception))
        self.assertIn('ensurepip missing', str(caught.exception))
    def test_lock_grammar_and_platform_paths(self):
        spec={**SPEC,'requirementsLock':'requirements.lock'}
        valid='FakeDep==1.0 --hash=sha256:'+'a'*64+'\n'
        self.assertEqual(rt.requirements(spec,locked=valid)[1],{'FakeDep':'1.0'})
        for text in ('FakeDep>=1\n','--index-url example\n','FakeDep==1\n','thing @ https://example.test/x.whl\n'):
            with self.assertRaises(rt.RuntimeFailure): rt.requirements(spec,locked=text)
        self.assertEqual(rt.venv_python(Path('C:/Python env'),True),Path('C:/Python env/Scripts/python.exe'))
        lock=Path('C:/空 间/lock')
        args=rt.pip_arguments(lock,Path('C:/wheel cache'),True)
        self.assertEqual(args[-1],str(lock)); self.assertIn('--require-hashes',args); self.assertIn('--no-index',args)
    def test_invalid_version_and_imports_never_create_venv(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            request=dict(protocol=1,spec={**SPEC,'minimumPython':[3,sys.version_info.minor+1]},bundleRoot=str(ROOT),python=sys.executable,deploymentRoot=str(root/'runtimes'),externalVenv=None,offline=True,wheelCache=str(root/'wheels'))
            with self.assertRaises(rt.RuntimeFailure): rt.prepare(request)
            self.assertFalse((root/'runtimes').exists())
    def test_owned_partial_preparation_resumes_without_deleting_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            request=dict(protocol=1,spec=SPEC,bundleRoot=str(ROOT),python=sys.executable,deploymentRoot=str(root/'runtimes'),externalVenv=None,offline=True,wheelCache=str(root/'wheels'))
            old=rt.prepare(request)
            changed={**request,'spec':{**SPEC,'imports':['json']}}
            original=rt.run_process
            def fail_venv(python,args,*positional,**keywords):
                if args[:4]==['-I','-B','-m','venv']: rt.fail('injected interrupted preparation')
                return original(python,args,*positional,**keywords)
            with patch.object(rt,'run_process',side_effect=fail_venv):
                with self.assertRaises(rt.RuntimeFailure): rt.prepare(changed)
            partial=next(p.parent for p in (root/'runtimes/workflow').glob('*/.omh-runtime.json') if p.parent!=Path(old['root']))
            custom=partial/'custom.txt'; custom.write_text('keep')
            recovered=rt.prepare(changed)
            self.assertEqual(Path(recovered['root']),partial)
            self.assertEqual(custom.read_text(),'keep')
            rt.verify(SPEC,old,'')
    @unittest.skipUnless(os.name=='posix','POSIX preparation link fixtures')
    def test_partial_preparation_never_writes_through_user_links(self):
        for kind in ('config_symlink','config_hardlink','activation_symlink','library_symlink','wheel_data_symlink'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as folder:
                root=Path(folder).resolve()
                request=dict(protocol=1,spec=SPEC,bundleRoot=str(ROOT),python=sys.executable,deploymentRoot=str(root/'runtimes'),externalVenv=None,offline=True,wheelCache=str(root/'wheels'))
                if kind=='wheel_data_symlink':
                    bundle=root/'bundle'; bundle.mkdir()
                    (bundle/'requirements.lock').write_text('FakeDep==1.0 --hash=sha256:'+'a'*64+'\n')
                    request.update(bundleRoot=str(bundle),spec={**SPEC,'requirementsLock':'requirements.lock'})
                original=rt.run_process
                def fail_venv(python,args,*positional,**keywords):
                    if args[:4]==['-I','-B','-m','venv']: rt.fail('injected interruption')
                    return original(python,args,*positional,**keywords)
                with patch.object(rt,'run_process',side_effect=fail_venv):
                    with self.assertRaises(rt.RuntimeFailure): rt.prepare(request)
                partial=next((root/'runtimes/workflow').glob('*/.omh-runtime.json')).parent
                outside=root/'user data'; outside.write_text('keep user contents')
                if kind=='config_symlink': (partial/'pyvenv.cfg').symlink_to(outside)
                elif kind=='config_hardlink': os.link(outside,partial/'pyvenv.cfg')
                elif kind=='activation_symlink':
                    (partial/'bin').mkdir(); (partial/'bin/activate').symlink_to(outside)
                else:
                    directory=root/'user modules'; directory.mkdir()
                    (partial/('share' if kind=='wheel_data_symlink' else 'lib')).symlink_to(directory,target_is_directory=True)
                with self.assertRaises(rt.RuntimeFailure): rt.prepare(request)
                self.assertEqual(outside.read_text(),'keep user contents')
    @unittest.skipUnless(os.name=='posix','POSIX ordinary venv alias fixture')
    def test_partial_preparation_accepts_ordinary_venv_aliases(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            request=dict(protocol=1,spec=SPEC,bundleRoot=str(ROOT),python=sys.executable,deploymentRoot=str(root/'runtimes'),externalVenv=None,offline=True,wheelCache=str(root/'wheels'))
            original=rt.run_process
            def fail_venv(python,args,*positional,**keywords):
                if args[:4]==['-I','-B','-m','venv']: rt.fail('injected interruption')
                return original(python,args,*positional,**keywords)
            with patch.object(rt,'run_process',side_effect=fail_venv):
                with self.assertRaises(rt.RuntimeFailure): rt.prepare(request)
            partial=next((root/'runtimes/workflow').glob('*/.omh-runtime.json')).parent
            (partial/'bin').mkdir(); (partial/'bin/python').symlink_to(Path(sys.executable).resolve())
            (partial/'lib').mkdir(); (partial/'lib64').symlink_to(partial/'lib',target_is_directory=True)
            user_file=root/'user file'; user_file.write_text('keep')
            (partial/'my note').symlink_to(user_file)
            executable=Path(sys.executable).resolve(); before=hashlib.sha256(executable.read_bytes()).hexdigest()
            prepared=rt.prepare(request)
            self.assertFalse(Path(prepared['python']).is_symlink())
            self.assertEqual(hashlib.sha256(executable.read_bytes()).hexdigest(),before)
            self.assertEqual(user_file.read_text(),'keep'); self.assertTrue((partial/'my note').is_symlink())
    def test_valid_runtime_does_not_depend_on_marker_format_or_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            request=dict(protocol=1,spec=SPEC,bundleRoot=str(ROOT),python=sys.executable,deploymentRoot=str(root/'runtimes'),externalVenv=None,offline=True,wheelCache=str(root/'wheels'))
            prepared=rt.prepare(request)
            Path(prepared['root'],'.omh-runtime.json').unlink()
            Path(prepared['root'],'unrelated-marker.json').write_text('irrelevant marker')
            legacy={k:v for k,v in prepared.items() if k!='deploymentRoot'}
            legacy['identity']='a historical identity'
            self.assertEqual(rt.verify(SPEC,legacy,''),legacy)
            self.assertEqual(rt.prepare(request),prepared)
            self.assertFalse(Path(prepared['root'],'.omh-runtime.json').exists())
    def test_unknown_incompatible_directory_is_not_rebuilt(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            request=dict(protocol=1,spec=SPEC,bundleRoot=str(ROOT),python=sys.executable,deploymentRoot=str(root/'runtimes'),externalVenv=None,offline=True,wheelCache=str(root/'wheels'))
            original=rt.run_process
            def fail_venv(python,args,*positional,**keywords):
                if args[:4]==['-I','-B','-m','venv']: rt.fail('injected interruption')
                return original(python,args,*positional,**keywords)
            with patch.object(rt,'run_process',side_effect=fail_venv):
                with self.assertRaises(rt.RuntimeFailure): rt.prepare(request)
            marker=next((root/'runtimes/workflow').glob('*/.omh-runtime.json'))
            marker.unlink(); custom=marker.parent/'user.txt'; custom.write_text('do not replace')
            with self.assertRaises(rt.RuntimeFailure): rt.prepare(request)
            self.assertEqual(custom.read_text(),'do not replace')
            self.assertFalse(rt.venv_python(marker.parent).exists())
    def test_explicit_runtime_deployment_can_live_under_the_source_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve(); source=root/'source'; source.mkdir()
            request=dict(protocol=1,spec=SPEC,bundleRoot=str(source),python=sys.executable,deploymentRoot=str(source/'.runtime-envs'),externalVenv=None,offline=True,wheelCache=str(root/'wheels'))
            prepared=rt.prepare(request)
            self.assertTrue(Path(prepared['root']).is_relative_to(source/'.runtime-envs'))
            rt.verify(SPEC,prepared,'')
    @unittest.skipUnless(os.name=='posix','POSIX external venv alias fixture')
    def test_external_venv_alias_is_resolved_and_never_modified(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            request=dict(protocol=1,spec=SPEC,bundleRoot=str(ROOT),python=sys.executable,deploymentRoot=str(root/'runtimes'),externalVenv=None,offline=True,wheelCache=str(root/'wheels'))
            prepared=rt.prepare(request); before=environment_snapshot(Path(prepared['root']))
            alias=root/'external alias'; alias.symlink_to(prepared['root'],target_is_directory=True)
            reused=rt.prepare({**request,'externalVenv':str(alias)})
            self.assertTrue(reused['external']); self.assertEqual(reused['root'],prepared['root'])
            self.assertEqual(environment_snapshot(Path(prepared['root'])),before)
    def test_external_dependency_mismatch_never_runs_pip(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            request=dict(protocol=1,spec=SPEC,bundleRoot=str(ROOT),python=sys.executable,deploymentRoot=str(root/'runtimes'),externalVenv=None,offline=True,wheelCache=str(root/'wheels'))
            prepared=rt.prepare(request); before=environment_snapshot(Path(prepared['root']))
            request.update(externalVenv=prepared['root'],spec={**SPEC,'imports':['OMH_NONEXISTENT_MODULE']})
            with self.assertRaises(rt.RuntimeFailure): rt.prepare(request)
            self.assertEqual(environment_snapshot(Path(prepared['root'])),before)
    def test_offline_hash_locked_wheel_and_missing_dependency_diagnosis(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve(); source=root/'bundle'; source.mkdir()
            wheels=root/'wheels'; wheels.mkdir()
            wheel=wheels/'omh_test_dep-1.0-py3-none-any.whl'
            with zipfile.ZipFile(wheel,'w') as archive:
                archive.writestr('omh_test_dep.py','VALUE = 42\n')
                archive.writestr('omh_test_dep-1.0.dist-info/METADATA','Metadata-Version: 2.1\nName: omh-test-dep\nVersion: 1.0\n')
                archive.writestr('omh_test_dep-1.0.dist-info/WHEEL','Wheel-Version: 1.0\nGenerator: OMH-test\nRoot-Is-Purelib: true\nTag: py3-none-any\n')
                archive.writestr('omh_test_dep-1.0.dist-info/RECORD','')
            lock='omh-test-dep==1.0 --hash=sha256:'+hashlib.sha256(wheel.read_bytes()).hexdigest()+'\n'
            (source/'requirements.lock').write_text(lock)
            spec={**SPEC,'requirementsLock':'requirements.lock','imports':['omh_test_dep']}
            request=dict(protocol=1,spec=spec,bundleRoot=str(source),python=sys.executable,deploymentRoot=str(root/'runtimes'),externalVenv=None,offline=True,wheelCache=str(wheels))
            config=root/'hostile-pip.ini'; escaped=root/'unowned target'
            config.write_text('[global]\ntarget = '+str(escaped)+'\n')
            with patch.dict(os.environ, {'PIP_CONFIG_FILE':str(config)}):
                prepared=rt.prepare(request)
            self.assertFalse(escaped.exists())
            rt.verify(spec,prepared,lock)
            (source/'requirements.lock').write_text(lock.replace(hashlib.sha256(wheel.read_bytes()).hexdigest(),'0'*64))
            with self.assertRaises(rt.RuntimeFailure) as caught: rt.prepare(request)
            self.assertEqual(caught.exception.code,'HARNESS_RUNTIME_OFFLINE_MISSING')
            rt.verify(spec,prepared,lock)
            bad_external={**request,'externalVenv':prepared['root'],'spec':{**spec,'imports':['OMH_NONEXISTENT_MODULE']}}
            snapshot=environment_snapshot(Path(prepared['root']))
            with self.assertRaises(rt.RuntimeFailure): rt.prepare(bad_external)
            self.assertEqual(environment_snapshot(Path(prepared['root'])),snapshot)
    @unittest.skipUnless(os.name=='nt','Windows native junction fixture')
    def test_junction_is_rejected_on_python_311(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve(); (root/'actual').mkdir()
            subprocess.run(['cmd','/c','mklink','/J',str(root/'junction'),str(root/'actual')],check=True,capture_output=True)
            self.addCleanup(lambda: (root/'junction').rmdir() if (root/'junction').exists() else None)
            with self.assertRaises(rt.RuntimeFailure): rt.safe_path(root/'junction/file')

if __name__=='__main__': unittest.main()

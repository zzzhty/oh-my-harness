#!/usr/bin/env python3
"""Exercise the pinned Rust exporter and imported payload in an isolated Home."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def launcher(home, env, script, *arguments, override=None, group='workflow'):
    import shutil
    base = home / '.claude/.omh-runtime'
    if os.name == 'nt':
        program = shutil.which('powershell') or shutil.which('pwsh')
        command = [program, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(base / 'run.ps1')]
    else:
        command = ['/bin/sh', str(base / 'run.sh')]
    child_env = {k:v for k,v in env.items() if k != 'OMH_PYTHON'}
    if override is not None: child_env['OMH_PYTHON'] = override
    return subprocess.run([*command, group, str(script), *arguments],
        env=child_env, cwd=home, capture_output=True, text=True, timeout=30)


def check_installed_helpers(home, env):
    for skill, helper, group in (
        ('sop', 'check_sop_ready.py', 'workflow'),
        ('long-running-goal', 'check_goal_ready.py', 'workflow'),
        ('summary-in-html', 'collect_summary_inputs.py', 'workflow'),
        ('doc-alignment', 'audit_docs.py', 'maintenance'),
    ):
        result = launcher(home, env, home / '.claude/skills' / skill / 'scripts' / helper, '--help', group=group)
        assert result.returncode == 0, (skill, result.stdout, result.stderr)


def exercise_shared_runtime(run, invoke, root, temp, home, env, atm):
    manager = Path(env['ATM_HOME'])
    assert not (home / '.oh-my-harness').exists()
    reverse_user = temp / 'reverse-order user'
    reverse_user.mkdir()
    reverse_env = dict(HOME=str(reverse_user), USERPROFILE=str(reverse_user),
        CODEX_HOME=str(reverse_user / '.codex'), ATM_HOME=str(temp / 'reverse-order manager'))
    source = run('harness', 'status')['manager']['repository']
    for arguments in (
        ('harness','bootstrap','--source',source),
        ('harness','runtime','prepare','workflow','--python',str(Path(sys.executable).absolute()),
         '--deployment-root',str(reverse_user / '.claude/skills'),'--offline'),
    ):
        result = invoke(*arguments, extra_env=reverse_env)
        assert result.returncode == 0, (result.stdout,result.stderr)
    blocked = invoke('install','skills','--harness','claude-code',extra_env=reverse_env)
    assert blocked.returncode != 0 and 'HARNESS_OWNER_CONFLICT' in blocked.stdout + blocked.stderr
    assert not (reverse_user / '.claude/.omh-owner.json').exists()
    blocked = invoke('harness','runtime','prepare','workflow','--python',Path(sys.executable).absolute(),
        '--deployment-root',home / '.claude/runtime','--offline')
    assert blocked.returncode != 0 and 'HARNESS_OWNER_CONFLICT' in blocked.stdout + blocked.stderr
    for group in ('workflow', 'maintenance'):
        prepared = run('harness', 'status')['runtimes'][group]
        assert Path(prepared['root'], '.omh-runtime.json').is_file()
        assert not Path(prepared['root'], '.atm-runtime.json').exists()
    check_installed_helpers(home, env)
    helper = temp / 'argv helper 空间.py'
    helper.write_text("import json,sys; print(json.dumps({'prefix':sys.prefix,'argv':sys.argv[1:]}))\n")
    arguments = ['space arg', '中文', '', '"quote"', "single'", '$(no shell)', 'C:\\path with spaces\\']
    result = launcher(home, env, helper, *arguments)
    assert result.returncode == 0, (result.stdout,result.stderr)
    assert json.loads(result.stdout)['argv'] == arguments
    for override in ('', 'python', str(temp / 'missing interpreter')):
        result = launcher(home, env, helper, override=override)
        assert result.returncode != 0
    current = (home / '.claude/.omh-runtime/workflow.json').read_bytes()
    failed = invoke('harness','runtime','prepare','workflow','--python',temp / 'missing','--offline')
    assert failed.returncode != 0
    assert (home / '.claude/.omh-runtime/workflow.json').read_bytes() == current
    # Runtime storage and skill targets are explicit, independent locations.
    deployed = run('harness','runtime','prepare','workflow','--python',Path(sys.executable).absolute(),
        '--deployment-root',temp / 'custom runtime storage 空间','--offline')['prepared']
    assert Path(deployed['root']).is_relative_to(temp / 'custom runtime storage 空间')
    assert Path(json.loads(launcher(home,env,helper).stdout)['prefix']) == Path(deployed['root'])
    reused = run('harness','runtime','prepare','workflow','--python',Path(sys.executable).absolute(),
        '--external-venv',deployed['root'],'--offline')['prepared']
    assert reused['external'] is True
    # A changed skill prevents the runtime binding and receipt switch as well.
    skill = home / '.claude/skills/sop/scripts/check_sop_ready.py'
    old = skill.read_bytes(); before = (manager / 'state/distribution.json').read_bytes()
    binding = (home / '.claude/.omh-runtime/workflow.json').read_bytes()
    skill.write_bytes(old + b'\n# TEST_ONLY user modification\n')
    failed = invoke('harness','runtime','prepare','workflow','--python',Path(sys.executable).absolute(),'--offline')
    assert failed.returncode != 0
    assert (manager / 'state/distribution.json').read_bytes() == before
    assert (home / '.claude/.omh-runtime/workflow.json').read_bytes() == binding
    skill.write_bytes(old)
    # Explicitly resolve the external runtime before the existing manager handoff.
    run('harness','runtime','prepare','workflow','--python',Path(sys.executable).absolute(),'--offline')
    assert not (home / '.oh-my-harness').exists()
    destination = temp / 'relocated manager 空间'
    run('harness','migrate','--to',destination,'--source',run('harness','status')['manager']['repository'],
        '--python',Path(sys.executable).absolute(),'--offline')
    env['ATM_HOME'] = str(destination)
    status = run('harness','status')
    for prepared in status['runtimes'].values():
        assert Path(prepared['root']).is_relative_to(destination)
    result = launcher(home,env,helper)
    assert result.returncode == 0, (result.stdout,result.stderr)
    assert Path(json.loads(result.stdout)['prefix']).is_relative_to(destination)
    assert Path(deployed['root']).is_dir()  # Reused/custom environments are retained.
    assert run('harness','plan','refresh','--harness','claude-code,codex')['files'] == []


def exercise_owner_handoff(run, invoke, root, temp, home, env):
    # This helper starts after ATM removal, with no overlapping owner remaining.
    def standalone(command):
        result = subprocess.run([str(Path(sys.executable).absolute()), '-B', '-m', 'omh', command,
            '--home',str(temp / 'standalone manager'),'--skills-root',str(home / '.claude/skills'),
            '--python',str(Path(sys.executable).absolute()),'--offline'], cwd=root, env=env,
            capture_output=True,text=True,timeout=120)
        assert result.returncode == 0, (command,result.stdout,result.stderr)
        return json.loads(result.stdout)
    import importlib.util
    spec = importlib.util.spec_from_file_location('omh_runtime_check', root / 'plugins/workflow/scripts/omh_runtime.py')
    runtime = importlib.util.module_from_spec(spec); spec.loader.exec_module(runtime)
    with runtime.lock(home / '.claude/.omh-owner.lock'):
        failed = invoke('install', 'skills', '--harness', 'claude-code')
        assert failed.returncode != 0 and 'HARNESS_BUSY' in failed.stdout + failed.stderr
    standalone('install')
    check_installed_helpers(home, env)
    owner = json.loads((home / '.claude/.omh-owner.json').read_text())
    assert owner['owner'] == 'omh'
    assert standalone('status')['receipt']['owner'] == 'omh'
    runtimes = json.loads((temp / 'standalone manager/runtime-state.json').read_text())
    assert all(Path(p['root']).is_relative_to(temp / 'standalone manager/runtimes') for p in runtimes.values())
    failed = invoke('install','skills','--harness','claude-code')
    assert failed.returncode != 0 and 'HARNESS_OWNER_CONFLICT' in failed.stdout + failed.stderr
    standalone('uninstall')
    run('install','skills','--harness','claude-code,codex')
    failed = subprocess.run([str(Path(sys.executable).absolute()),'-B','-m','omh','install',
        '--home',str(temp / 'second standalone manager'),'--skills-root',str(home / '.claude/skills'),
        '--python',str(Path(sys.executable).absolute()),'--offline'],cwd=root,env=env,capture_output=True,text=True,timeout=30)
    assert failed.returncode != 0 and 'HARNESS_OWNER_CONFLICT' in failed.stdout + failed.stderr
    assert not (temp / 'second standalone manager').exists()
    run('uninstall','skills','--harness','claude-code,codex')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--atm', required=True, type=Path)
    parser.add_argument('--shared-runtime', action='store_true', help='Exercise the candidate ATM protocol integration and owner handoff')
    args = parser.parse_args()
    atm = args.atm.resolve(strict=True)
    root = Path(__file__).resolve().parents[1]
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    version = (root / 'VERSION').read_text().strip()
    with tempfile.TemporaryDirectory(prefix='OMH_TEST_ONLY_内容 ') as directory:
        temp = Path(directory).resolve()
        home = temp / 'user'
        home.mkdir()
        env = {k: v for k, v in os.environ.items() if not k.startswith(('ATM_', 'OH_MY_HARNESS_', 'OMH_'))}
        env.update(HOME=str(home), USERPROFILE=str(home), ATM_HOME=str(temp / 'manager'),
                   CODEX_HOME=str(home / '.codex'), PATH='', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
        def invoke(*arguments, extra_env=None):
            result = subprocess.run([str(atm), *map(str, arguments)], env={**env, **(extra_env or {})},
                                    capture_output=True, text=True, encoding='utf-8', timeout=90)
            return result
        def run(*arguments):
            result = invoke(*arguments)
            if result.returncode: raise AssertionError((arguments, result.returncode, result.stdout, result.stderr))
            return json.loads(result.stdout)
        archive = temp / 'omh.omh'
        run('harness', 'export', '--source', root, '--output', archive,
            '--repository', 'https://github.com/zzzhty/oh-my-harness', '--revision', revision,
            '--url', f'https://github.com/zzzhty/oh-my-harness/releases/download/v{version}/omh.omh')
        imported = run('harness', 'import', '--lock', temp / 'omh.lock.json', '--archive', archive)
        assert imported['selected'] is False
        assert not (temp / 'manager/state/distribution.json').exists()
        assert not (home / '.codex').exists()
        payload = Path(imported['source'])
        assert not (payload / 'scripts').exists()
        assert not (payload / '.agents/harnesses').exists()
        assert not (payload / 'plugins/watcher').exists()
        archive.unlink()
        run('harness', 'fetch', '--lock', temp / 'omh.lock.json', '--output', payload)
        run('harness', 'bootstrap', '--source', payload)
        run('install', 'skills', '--harness', 'claude-code,codex')
        run('check', 'skills', '--harness', 'claude-code,codex', '--strict')
        assert run('harness', 'plan', 'refresh', '--harness', 'claude-code,codex')['files'] == []
        assert run('harness', 'status')['hooksEnabled'] is False
        assert not (temp / 'manager/venv').exists()
        assert not (home / '.codex/hooks.json').exists()
        assert not (home / '.openclaw').exists()
        catalog = json.loads((payload / 'canonical-catalog.json').read_text())
        skills = {item['id']: item for item in catalog['skills']}
        assert len(skills) == 29
        assert 'maintenance:doc-alignment' in skills
        assert 'mattpocock-skills:writing-for-agents' in skills
        assert not any('skill-maintainer' in name or name.startswith('watcher:') for name in skills)
        assert catalog['attributionOverlays'] == []
        assert not (payload / 'runtimes/watcher').exists()
        manifest = json.loads((payload / 'content-manifest.json').read_text())
        assert manifest['historicalIdentities'] == {}
        assert {group['id'] for group in manifest['runtimeGroups']} == {'maintenance', 'workflow'}
        assert set(manifest['runtimeBindings'].values()) == {'maintenance', 'workflow'}
        # Prepare only the declared standard-library helper groups, at final
        # paths inside this disposable manager. The static lifecycle above ran
        # with no Python on PATH and created no runtimes.
        prepared_python = None
        for group in ('maintenance', 'workflow'):
            result = run('harness', 'runtime', 'prepare', group, '--python',
                         Path(sys.executable).absolute(), '--offline')
            python = Path(result['prepared']['python'])
            assert python.is_file() and python.is_relative_to(temp / 'manager/runtimes' / group)
            if group == 'maintenance':
                prepared_python = python
        script = payload / skills['maintenance:doc-alignment']['path'] / 'scripts/audit_docs.py'
        # Explicit skill helper health only; no client invocation or hook event.
        subprocess.run([str(prepared_python), '-B', str(script), '--help'],
                       env=env, check=True, capture_output=True, timeout=30)
        assert run('harness', 'status')['hooksEnabled'] is False
        run('update', 'skills', '--harness', 'claude-code,codex')
        if args.shared_runtime:
            exercise_shared_runtime(run, invoke, root, temp, home, env, atm)
        run('uninstall', 'skills', '--harness', 'claude-code,codex')
        if args.shared_runtime:
            exercise_owner_handoff(run, invoke, root, temp, home, env)

        assert run('harness', 'status')['harnessReceipts'] == {}
        print(json.dumps({'contentIdentity': imported['contentIdentity'], 'targets': ['claude-code', 'codex'],
                          'skills': len(skills), 'preparedGroups': ['maintenance', 'workflow'],
                          'hooksEnabled': False, 'nativeClientInvocation': 'not tested'}))


if __name__ == '__main__':
    main()

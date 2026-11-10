#!/usr/bin/env python3
"""Exercise the standalone distributor end to end in an isolated Home."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SKILL_PLUGINS = ('maintenance', 'workflow', 'mattpocock-skills')
HELPERS = (
    ('sop', 'check_sop_ready.py', 'workflow'),
    ('long-running-goal', 'check_goal_ready.py', 'workflow'),
    ('summary-in-html', 'collect_summary_inputs.py', 'workflow'),
    ('doc-alignment', 'audit_docs.py', 'maintenance'),
)


def standalone(env, *arguments, timeout=120):
    result = subprocess.run([str(Path(sys.executable).absolute()), '-B', '-m', 'omh', *map(str, arguments)],
        cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', timeout=timeout)
    payload = json.loads(result.stdout) if result.stdout.strip() else {}
    return result, payload


def checked(env, *arguments):
    result, payload = standalone(env, *arguments)
    assert result.returncode == 0, (arguments, result.stdout, result.stderr)
    return payload


def expected_skills():
    skills = set()
    for name in SKILL_PLUGINS:
        for skill in sorted((ROOT / 'plugins' / name / 'skills').iterdir()):
            if (skill / 'SKILL.md').is_file(): skills.add(skill.name)
    return skills


def launcher(home, env, script, *arguments, override=None, group='workflow'):
    base = home / '.codex/.omh-runtime'
    if os.name == 'nt':
        program = shutil.which('powershell') or shutil.which('pwsh')
        command = [program, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(base / 'run.ps1')]
    else:
        command = ['/bin/sh', str(base / 'run.sh')]
    child_env = {k: v for k, v in env.items() if k != 'OMH_PYTHON'}
    if override is not None: child_env['OMH_PYTHON'] = override
    return subprocess.run([*command, group, str(script), *arguments],
        env=child_env, cwd=home, capture_output=True, text=True, encoding='utf-8', timeout=30)


def check_installed_helpers(home, env):
    for skill, helper, group in HELPERS:
        result = launcher(home, env, home / '.codex/skills' / skill / 'scripts' / helper, '--help', group=group)
        assert result.returncode == 0, (skill, result.stdout, result.stderr)


def main():
    with tempfile.TemporaryDirectory(prefix='OMH_TEST_ONLY_standalone_') as directory:
        temp = Path(directory).resolve()
        home = temp / 'user'
        home.mkdir()
        skills = home / '.codex/skills'
        state = temp / 'manager home'
        env = {k: v for k, v in os.environ.items() if not k.startswith(('OH_MY_HARNESS_', 'OMH_'))}
        env.update(HOME=str(home), USERPROFILE=str(home), CODEX_HOME=str(home / '.codex'),
                   PATH='', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
        python = str(Path(sys.executable).absolute())

        # Read-only planning creates neither a target nor manager state.
        plan = checked(env, 'plan', '--home', state, '--skills-root', skills, '--offline')
        assert plan['changes'] and not state.exists() and not skills.parent.exists()

        install = checked(env, 'install', '--home', state, '--skills-root', skills, '--python', python, '--offline')
        assert set(install['runtimes']) == {'maintenance', 'workflow'}
        status, payload = standalone(env, 'status', '--home', state, '--skills-root', skills, '--json')
        target = payload['targets'][0]
        assert status.returncode == 0 and target['state'] == 'installed' and target['owner'] == 'omh'
        assert target['modified'] == {} and target['recoveryRequired'] is False
        overview = subprocess.run([str(Path(sys.executable).absolute()), '-B', '-m', 'omh', 'status',
            '--home', str(state)], cwd=ROOT, env=env, capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=60)
        assert overview.returncode == 0, overview.stdout + overview.stderr
        assert str(skills.parent) in overview.stdout and 'installed' in overview.stdout
        receipt_files = json.loads((home / '.codex/.omh-owner.json').read_text())['files']
        projected = {name.split('/')[1] for name in receipt_files
                     if name.startswith('skills/') and name.count('/') >= 2}
        assert projected == expected_skills()
        instructions = home / '.codex/AGENTS.md'
        assert instructions.read_bytes() == (ROOT / 'agents/global-instructions.md').read_bytes()
        assert 'AGENTS.md' in receipt_files
        assert (home / '.codex/.omh-owner.json').is_file()
        assert not (home / '.codex/hooks.json').exists()

        # Helpers run through the persisted launcher, without the source checkout.
        check_installed_helpers(home, env)
        helper = temp / 'argv helper 空间.py'
        helper.write_text("import json,sys; print(json.dumps({'prefix':sys.prefix,'argv':sys.argv[1:]}))\n")
        arguments = ['space arg', '中文', '', '"quote"', "single'", '$(no shell)', 'C:\\path with spaces\\']
        result = launcher(home, env, helper, *arguments)
        assert result.returncode == 0, (result.stdout, result.stderr)
        assert json.loads(result.stdout)['argv'] == arguments
        for override in ('', 'python', str(temp / 'missing interpreter')):
            result = launcher(home, env, helper, override=override)
            assert result.returncode != 0

        # A lingering native marketplace configuration is never taken over.
        conflicting = temp / 'conflicting harness'
        (conflicting / 'skills').mkdir(parents=True)
        (conflicting / 'config.toml').write_text('[plugins."workflow@oh-my-harness"]\nenabled = true\n')
        result, _ = standalone(env, 'install', '--home', temp / 'second manager', '--skills-root', conflicting / 'skills',
                               '--python', python, '--offline')
        assert result.returncode != 0 and 'HARNESS_OWNER_CONFLICT' in result.stdout + result.stderr
        assert not (conflicting / '.omh-owner.json').exists()
        assert not any((conflicting / 'skills').iterdir())

        # Unowned instructions fail closed on a fresh target.
        owned_instructions = temp / 'unowned instructions harness'
        (owned_instructions / 'skills').mkdir(parents=True)
        (owned_instructions / 'AGENTS.md').write_text('# user authored\n')
        result, _ = standalone(env, 'install', '--home', temp / 'third manager', '--skills-root', owned_instructions / 'skills',
                               '--python', python, '--offline')
        assert result.returncode != 0 and 'HARNESS_CONFLICT' in result.stdout + result.stderr

        assert checked(env, 'update', '--home', state, '--skills-root', skills, '--python', python, '--offline')['changed'] == 0
        shim = home / '.local/bin/omh'
        if os.name != 'nt':
            assert shim.is_file() and os.access(shim, os.X_OK)
            result = subprocess.run([str(shim), 'status', '--home', str(state), '--skills-root', str(skills), '--json'],
                env={k: v for k, v in env.items() if k != 'PYTHONPATH'},
                capture_output=True, text=True, encoding='utf-8', timeout=60)
            assert result.returncode == 0, (result.stdout, result.stderr)
            assert json.loads(result.stdout)['targets'][0]['owner'] == 'omh'
        uninstall = checked(env, 'uninstall', '--home', state, '--skills-root', skills)
        assert uninstall['changed'] > 0 and not (home / '.codex/.omh-owner.json').exists()
        assert not instructions.exists()
        if os.name != 'nt': assert not shim.exists()
        status, payload = standalone(env, 'status', '--home', state, '--skills-root', skills, '--json')
        assert status.returncode == 1 and payload['targets'][0]['state'] == 'missing'
        status, payload = standalone(env, 'status', '--home', state, '--json')
        assert status.returncode == 0 and payload['targets'] == []

        # The grok target resolves its own default root and rule filename.
        grok = home / '.grok'
        checked(env, 'install', '--home', state, '--harness', 'grok', '--python', python, '--offline')
        assert (grok / 'skills/sop/SKILL.md').is_file()
        assert (grok / 'AGENTS.md').read_bytes() == (ROOT / 'agents/global-instructions.md').read_bytes()
        (grok / 'Claude.md').write_text('# shadow rules\n')
        blocked, _ = standalone(env, 'update', '--home', state, '--harness', 'grok', '--python', python, '--offline')
        assert blocked.returncode != 0 and 'HARNESS_CONFLICT' in blocked.stdout + blocked.stderr
        (grok / 'Claude.md').unlink()
        checked(env, 'uninstall', '--home', state, '--harness', 'grok')
        assert not (grok / 'AGENTS.md').exists() and not (grok / 'skills/sop').exists()

        print(json.dumps({'targets': ['standalone'], 'skills': len(expected_skills()),
                          'instructions': 'AGENTS.md', 'launcher': os.name != 'nt',
                          'preparedGroups': ['maintenance', 'workflow'], 'hooksEnabled': False,
                          'nativeClientInvocation': 'not tested'}))


if __name__ == '__main__':
    main()

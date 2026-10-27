#!/usr/bin/env python3
"""Exercise the pinned Rust exporter and imported payload in an isolated Home."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--atm', required=True, type=Path)
    args = parser.parse_args()
    atm = args.atm.resolve(strict=True)
    root = Path(__file__).resolve().parents[1]
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    version = (root / 'VERSION').read_text().strip()
    with tempfile.TemporaryDirectory(prefix='OMH_TEST_ONLY_内容 ') as directory:
        temp = Path(directory).resolve()
        home = temp / 'user'
        home.mkdir()
        env = {k: v for k, v in os.environ.items() if not k.startswith(('ATM_', 'OH_MY_HARNESS_'))}
        env.update(HOME=str(home), USERPROFILE=str(home), ATM_HOME=str(temp / 'manager'),
                   CODEX_HOME=str(home / '.codex'), PATH='', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
        def run(*arguments):
            result = subprocess.run([str(atm), *map(str, arguments)], env=env, check=True,
                                    capture_output=True, text=True, encoding='utf-8', timeout=90)
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
        run('uninstall', 'skills', '--harness', 'claude-code,codex')
        assert run('harness', 'status')['harnessReceipts'] == {}
        print(json.dumps({'contentIdentity': imported['contentIdentity'], 'targets': ['claude-code', 'codex'],
                          'skills': len(skills), 'preparedGroups': ['maintenance', 'workflow'],
                          'hooksEnabled': False, 'nativeClientInvocation': 'not tested'}))


if __name__ == '__main__':
    main()

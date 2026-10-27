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
        # Explicit helper health only; no native client invocation or hook event.
        env['ATM_HARNESS_ROOT'] = str(payload)
        script = payload / 'runtimes/watcher/scripts/watcher'
        subprocess.run([sys.executable, '-B', str(script), 'skill', 'doctor', '--repo-root', str(payload)],
                       env=env, check=True, capture_output=True, timeout=30)
        print(json.dumps({'contentIdentity': imported['contentIdentity'], 'targets': ['claude-code', 'codex'],
                          'hooksEnabled': False, 'nativeClientInvocation': 'not tested'}))


if __name__ == '__main__':
    main()

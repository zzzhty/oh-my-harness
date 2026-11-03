"""Bounded directory projection with per-target ownership and durable recovery."""
from __future__ import annotations
import argparse
import base64
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tomllib

SOURCE = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('omh_runtime', SOURCE / 'plugins/workflow/scripts/omh_runtime.py')
rt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rt)

OWNER = '.omh-owner.json'
LOCK = '.omh-owner.lock'

def data(path):
    rt.safe_path(path)
    if not path.exists(): return None
    if not path.is_file(): rt.fail(f'Not an ordinary owned file: {path}')
    if path.stat().st_size > 128 * 1024 * 1024: rt.fail(f'File exceeds distribution limit: {path}')
    return path.read_bytes()

def tree(root):
    rt.safe_path(root)
    if not root.exists(): return {}
    if not root.is_dir(): rt.fail(f'Not a directory: {root}')
    result = {}
    for path in sorted(root.rglob('*')):
        rt.safe_path(path)
        if path.is_file(): result[path.relative_to(root).as_posix()] = data(path)
        elif not path.is_dir(): rt.fail(f'Unsupported filesystem object: {path}')
        if len(result) > 5000: rt.fail('Too many distribution files')
    return result

def sha(value): return hashlib.sha256(value).hexdigest()

def receipt(root, home):
    value = data(root / OWNER)
    if value is None: return None
    item = json.loads(value)
    if item.get('owner') != 'omh' or item.get('manager') != str(home) or item.get('target') != str(root):
        rt.fail('Target belongs to a different owner; uninstall with that owner before handoff', 'HARNESS_OWNER_CONFLICT')
    if item.get('schemaVersion') != 1: rt.fail('Unsupported receipt')
    if not isinstance(item['slots'], list) or not isinstance(item['files'], dict): rt.fail('Invalid receipt')
    for slot in item['slots']: relative(slot)
    for name, fingerprint in item['files'].items():
        relative(name)
        if not re.fullmatch(r'[0-9a-f]{64}', fingerprint) or not any(name.startswith(slot + '/') for slot in item['slots']): rt.fail('Invalid ownership inventory')
    return item

def relative(name):
    if (not name or '\\' in name or ':' in name or any(p in ('', '.', '..') for p in name.split('/'))
            or any(ord(c) < 32 for c in name) or Path(name).is_absolute()):
        rt.fail('Invalid relative content path')
    for part in name.split('/'):
        if part.endswith(('.', ' ')) or any(c in '<>"|?*' for c in part) or re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', part, re.I):
            rt.fail('Content path is not portable')
    return Path(name)

def journal_path(home, root):
    return home / 'transactions' / (sha(str(root).encode()) + '.json')

def b64(value): return None if value is None else base64.b64encode(value).decode()
def unb64(value): return None if value is None else base64.b64decode(value, validate=True)

def write_value(path, value):
    if value is None:
        rt.safe_path(path)
        path.unlink(missing_ok=True)
    else: rt.atomic(path, value)

def clean_empty_directories(root, names):
    for name in names:
        try:
            path = rt.safe_path(root / relative(name))
            if path.is_dir(): path.rmdir()
        except rt.RuntimeFailure: pass  # A later user link is outside cleanup ownership.
        except FileNotFoundError: pass
        except OSError as error:
            if error.errno not in (errno.ENOTEMPTY, errno.EEXIST, errno.ENOTDIR): raise

def recover(home, root):
    path = journal_path(home, root)
    raw = data(path)
    if raw is None: return False
    journal = json.loads(raw)
    if journal['target'] != str(root) or journal['manager'] != str(home): rt.fail('Recovery identity mismatch')
    if not journal['committed']:
        # Only rollback needs before/after matching. Committed recovery merely
        # finishes empty-directory cleanup and preserves subsequent user edits.
        for change in journal['changes']:
            destination = root / relative(change['path'])
            if data(destination) not in (unb64(change['before']), unb64(change['after'])):
                rt.fail(f'Post-failure edit preserved: {destination}', 'HARNESS_RECOVERY_CONFLICT')
        for change in reversed(journal['changes']):
            write_value(root / relative(change['path']), unb64(change['before']))
        clean_empty_directories(root, reversed(journal['createdDirectories']))
    else:
        clean_empty_directories(root, journal['cleanupDirectories'])
    path.unlink()
    return True

def transact(home, root, changes):
    path = journal_path(home, root)
    if path.exists(): rt.fail('Run recover before modifying this target', 'HARNESS_RECOVERY_REQUIRED')
    if not changes: return
    if len(changes) > 5000 or sum(len(c['before'] or '') + len(c['after'] or '') for c in changes) > 128 * 1024 * 1024:
        rt.fail('Distribution transaction exceeds limits')
    directories = set()
    for change in changes:
        parent = (root / relative(change['path'])).parent
        while parent != root:
            rt.safe_path(parent)
            if not parent.exists(): directories.add(parent.relative_to(root).as_posix())
            parent = parent.parent
    cleanup = set()
    previous = next((unb64(c['before']) for c in changes if c['path'] == OWNER), None)
    if previous:
        previous = json.loads(previous)
        for name in previous['files']:
            parent = (root / relative(name)).parent
            while any(parent == root / slot or (root / slot) in parent.parents for slot in previous['slots']):
                cleanup.add(parent.relative_to(root).as_posix())
                parent = parent.parent
    journal = dict(schemaVersion=1, manager=str(home), target=str(root), committed=False,
                   changes=changes, createdDirectories=sorted(directories, key=lambda p: (len(Path(p).parts), p)),
                   cleanupDirectories=sorted(cleanup, key=lambda p: (-len(Path(p).parts), p)))
    rt.atomic(path, rt.encode(journal))
    try:
        for change in changes:
            destination = root / relative(change['path'])
            if data(destination) != unb64(change['before']): rt.fail('Target changed after planning')
            write_value(destination, unb64(change['after']))
        clean_empty_directories(root, journal['cleanupDirectories'])
        journal['committed'] = True
        rt.atomic(path, rt.encode(journal))
    except BaseException:
        # Ordinary failures roll back; hard interruption leaves the durable journal.
        recover(home, root)
        raise
    path.unlink()

def manifest(source):
    value = json.loads(data(source / 'content-manifest.json'))
    if value['schemaVersion'] != 1 or value['product'] != 'omh-content': rt.fail('Unsupported content manifest')
    if set(value['compositions']['default']) != {p['name'] for p in value['packages']}: rt.fail('Unsupported composition')
    return value

def prepare_runtimes(source, home, python, deployment, external, offline):
    result = {}
    for spec in manifest(source)['runtimeGroups']:
        result[spec['id']] = rt.prepare(dict(protocol=1, spec=spec, bundleRoot=str(source),
            python=str(python), deploymentRoot=str(deployment), externalVenv=str(external) if external else None,
            wheelCache=str(home / 'cache/wheels'), offline=offline))
    # This is standalone configuration, never emitted by the runtime provider itself.
    rt.atomic(home / 'runtime-state.json', rt.encode(result))
    return result

def projected(source, skills, prepared):
    root = skills.parent
    value = manifest(source)
    output, slots, names = {}, set(), set()
    for package in value['packages']:
        name = package['name']
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name) or package['path'] != f'plugins/{name}': rt.fail('Invalid package path')
        package_root = source / relative(package['path'])
        for skill in sorted((package_root / 'skills').iterdir()):
            rt.safe_path(skill)
            if not skill.is_dir(): continue
            if not re.fullmatch(r'[A-Za-z0-9_-]+', skill.name) or skill.name.lower() in names: rt.fail('Duplicate or invalid skill name')
            names.add(skill.name.lower())
            if not (skill / 'SKILL.md').is_file(): rt.fail('Incomplete skill')
            slot = (skills / skill.name).relative_to(root).as_posix()
            slots.add(slot)
            for suffix, content in tree(skill).items():
                if '__pycache__' in Path(suffix).parts or suffix.endswith('.pyc'): continue
                if suffix.endswith('.py'):
                    replacement = f'Path({json.dumps(str(root / ".omh-support" / name))})'
                    content = content.decode().replace('Path(__file__).resolve().parents[3] / "scripts"', replacement).encode()
                output[f'{slot}/{suffix}'] = content
        for suffix, content in tree(package_root / 'scripts').items():
            if '__pycache__' not in Path(suffix).parts and not suffix.endswith('.pyc'):
                output[f'.omh-support/{name}/{suffix}'] = content
    slots.add('.omh-runtime')
    if any(name.startswith('.omh-support/') for name in output): slots.add('.omh-support')
    for spec in value['runtimeGroups']:
        for name, content in rt.binding_files(spec, prepared.get(spec['id']), source).items():
            output[f'.omh-runtime/{name}'] = content
    return output, sorted(slots)

def file_drift(root, old):
    result = {}
    for name, fingerprint in (old['files'] if old else {}).items():
        current = data(root / relative(name))
        if current is None: result[name] = 'missing'
        elif sha(current) != fingerprint: result[name] = 'modified'
    return result

def plan(source, home, skills, operation, prepared):
    root = skills.parent
    old = receipt(root, home)
    if old is None and operation != 'uninstall':
        # A native plugin configuration is evidence of an existing installation.
        # An inert cache or marketplace entry alone is not an installation owner.
        config = data(root / 'config.toml')
        coordinates = {'atm-harness', 'oh-my-harness'}
        if config and any(name.encode() in config for name in coordinates):
            native = tomllib.loads(config.decode('utf-8'))
            if any(key.rsplit('@', 1)[-1] in coordinates for key in native.get('plugins', {})):
                rt.fail('Existing native OMH configuration needs explicit owner handoff', 'HARNESS_OWNER_CONFLICT')
    if journal_path(home, root).exists(): rt.fail('Recovery required', 'HARNESS_RECOVERY_REQUIRED')
    desired, slots = ({}, []) if operation == 'uninstall' else projected(source, skills, prepared)
    old_files = old['files'] if old else {}
    changes = []
    for name in sorted(set(old_files) | set(desired)):
        current = data(root / relative(name))
        new = desired.get(name)
        if current is not None:
            if name not in old_files: rt.fail(f'Unowned target file exists: {name}', 'HARNESS_CONFLICT')
            if sha(current) != old_files[name] and current != new:
                rt.fail(f'User-modified target file: {name}', 'HARNESS_CONFLICT')
        if current != new: changes.append(dict(path=name, before=b64(current), after=b64(new)))
    new_receipt = None if operation == 'uninstall' else rt.encode(dict(schemaVersion=1, owner='omh', manager=str(home), target=str(root),
        sourceIdentity=rt.digest({p:sha(v) for p,v in desired.items()}), slots=slots, files={p:sha(v) for p,v in desired.items()}))
    if data(root / OWNER) != new_receipt: changes.append(dict(path=OWNER, before=b64(data(root / OWNER)), after=b64(new_receipt)))
    return changes

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'install', 'update', 'uninstall', 'status', 'plan', 'recover'])
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--home', type=Path, default=Path.home() / '.oh-my-harness')
    parser.add_argument('--harness', choices=['codex', 'claude-code'], default='codex')
    parser.add_argument('--skills-root', type=Path)
    parser.add_argument('--deployment-root', type=Path)
    parser.add_argument('--python', type=Path)
    parser.add_argument('--external-venv', type=Path)
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--operation', choices=['install', 'update', 'uninstall'], default='install')
    args = parser.parse_args(argv)
    try:
        home, source = rt.safe_path(args.home), rt.safe_path(args.source)
        skills = rt.safe_path(args.skills_root or Path.home() / ('.codex' if args.harness == 'codex' else '.claude') / 'skills')
        root = skills.parent
        if home == root or home.is_relative_to(root): rt.fail('Manager and skill target must be separate')
        if args.command == 'status':
            old = receipt(root, home)
            drift = file_drift(root,old)
            print(json.dumps(dict(receipt=old, modified=drift, recoveryRequired=journal_path(home,root).exists())))
            return 0 if not drift else 1
        if args.command == 'plan':
            raw = data(home / 'runtime-state.json')
            prepared = json.loads(raw) if raw else {}
            print(json.dumps(dict(changes=[c['path'] for c in plan(source,home,skills,args.operation,prepared)])))
            return 0
        with rt.lock((home / '.prepare.lock') if args.command == 'prepare' else root / LOCK):
            if args.command == 'recover': result = dict(recovered=recover(home,root))
            elif args.command == 'uninstall':
                changes = plan(source,home,skills,'uninstall',{})
                transact(home,root,changes)
                result = dict(changed=len(changes))
            else:
                if args.command != 'prepare':
                    # Owner identity is enough here. Plan target files once,
                    # after preparing bindings; the journal rechecks before-images.
                    receipt(root,home)
                python = rt.absolute(args.python if args.python is not None else os.environ.get('OMH_PYTHON', sys.executable))
                deployment = rt.safe_path(args.deployment_root or home / 'runtimes')
                if deployment == root or deployment.is_relative_to(root) or root.is_relative_to(deployment): rt.fail('Runtime deployment and skill targets must be separate')
                prepared = prepare_runtimes(source,home,python,deployment,args.external_venv,args.offline)
                if args.command == 'prepare': result = dict(runtimes=prepared)
                else:
                    changes = plan(source,home,skills,args.command,prepared)
                    transact(home,root,changes)
                    result = dict(changed=len(changes), runtimes=prepared)
        print(json.dumps(result))
        return 0
    except (rt.RuntimeFailure, OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps(dict(error=dict(code=getattr(error,'code','OMH_INVALID'),message=str(error)))))
        return 1

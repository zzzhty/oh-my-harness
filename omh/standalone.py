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
import shlex
import sys
import tomllib

SOURCE = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('omh_runtime', SOURCE / 'plugins/workflow/scripts/omh_runtime.py')
rt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rt)

OWNER = '.omh-owner.json'
LOCK = '.omh-owner.lock'

# ADR 0032: the harness global-instructions file is projected beside the skills
# root as an owned managed file. Shadowing files conflict with it. Grok Build
# scans several rule filenames in one directory; the non-case-variant siblings
# shadow our AGENTS.md (case variants are skipped for case-insensitive systems).
HARNESS_ROOTS = {'codex': '.codex', 'claude-code': '.claude', 'grok': '.grok'}
INSTRUCTIONS = {'codex': 'AGENTS.md', 'claude-code': 'CLAUDE.md', 'grok': 'AGENTS.md'}
SHADOWS = {'codex': ('AGENTS.override.md',), 'grok': ('Claude.md', 'AGENT.md')}
INSTRUCTIONS_SOURCE = 'agents/global-instructions.md'

# ADR 0033: a static POSIX launcher shim pointing at the installing source
# checkout and interpreter. It is a pointer, not a manager: no state, no
# self-update, no PATH search, no fallback when the checkout is gone.
SHIM_MARKER = '# oh-my-harness standalone launcher v1'
SHIM_NAME = 'omh'

# ADR 0034: the home keeps an index of targets it installed. The index is a
# hint for status; each target's receipt remains the truth and is verified live.
TARGETS_FILE = 'targets.json'
# Serializes home-index read-modify-write. Non-blocking, same as the target lock.
HOME_LOCK = '.omh-home.lock'
SHARED_ASSIGNMENT = re.compile(br'(?m)^OMH_SHARED_SCRIPTS[ \t]*=[ \t]*[^\r\n]+')

def load_targets(home):
    raw = data(home / TARGETS_FILE)
    return json.loads(raw) if raw else {}

def save_targets(home, value):
    if value: rt.atomic(home / TARGETS_FILE, rt.encode(value))
    else: (home / TARGETS_FILE).unlink(missing_ok=True)

def remember_target(home, root, harness, skills, installed):
    with rt.lock(home / HOME_LOCK):
        targets = load_targets(home)
        if installed: targets[str(root)] = dict(harness=harness, skillsRoot=str(skills))
        else: targets.pop(str(root), None)
        save_targets(home, targets)

def target_state(home, root):
    item = dict(target=str(root))
    raw = data(root / OWNER)
    if raw is None: return dict(item, state='missing')
    try:
        value = json.loads(raw)
        owner, manager = value['owner'], value['manager']
    except (ValueError, KeyError, TypeError):
        return dict(item, state='invalid-receipt')
    if owner != 'omh': return dict(item, state='foreign', owner=owner)
    if manager != str(home): return dict(item, state='other-home', manager=manager)
    try:
        drift = file_drift(root, value)
    except (KeyError, TypeError, ValueError):
        return dict(item, state='invalid-receipt')
    return dict(item, state='installed', owner=owner, harness=None,
                files=len(value.get('files', {})), sourceIdentity=str(value.get('sourceIdentity', ''))[:12],
                modified=drift, recoveryRequired=journal_path(home, root).exists())

def default_roots():
    yield Path.home() / '.codex', 'codex'
    yield Path.home() / '.claude', 'claude-code'
    yield Path.home() / '.grok', 'grok'

def overview(home):
    targets = {}
    for root, entry in load_targets(home).items():
        targets[root] = entry.get('harness')
    for root, harness in default_roots():
        if (root / OWNER).exists(): targets.setdefault(str(root), harness)
    return [dict(target_state(home, rt.safe_path(Path(root))), harness=harness or '?')
            for root, harness in sorted(targets.items())]

def clean(item):
    return item['state'] == 'installed' and not item['modified'] and not item['recoveryRequired']

def runtime_version(prepared):
    root = prepared.get('root') if isinstance(prepared, dict) else None
    if not root: return ''
    line = data(Path(root) / 'pyvenv.cfg')
    if not line: return ''
    for part in line.decode('utf-8', 'replace').splitlines():
        if part.startswith('version = '): return part[10:].strip()
    return ''

def runtime_entries(home):
    """Group id and pyvenv.cfg version. This is the machine form of the text summary."""
    raw = data(home / 'runtime-state.json')
    if raw is None: return []
    return [dict(id=group, version=runtime_version(prepared))
            for group, prepared in sorted(json.loads(raw).items())]

def runtime_summary(entries):
    return ' '.join(f"{item['id']}({item['version']})" if item['version'] else item['id'] for item in entries)

def error_line(code, message):
    # Errors belong on stderr so piped stdout stays a parseable result stream.
    print(json.dumps(dict(error=dict(code=code, message=message))), file=sys.stderr)

def progress(message):
    # TTY-gated: interactive terminals see life, logs and captures stay clean.
    if getattr(sys.stderr, 'isatty', lambda: False)():
        print(message, file=sys.stderr, flush=True)

def print_overview(home, items, as_json):
    entries = runtime_entries(home)
    shim = data(home / 'shim.json')
    if as_json:
        print(json.dumps(dict(home=str(home), launcher=json.loads(shim) if shim else None,
                              runtimes=entries, targets=items)))
        return
    print(f"omh home: {home}")
    if shim:
        record = json.loads(shim)
        print(f"launcher: {record['path']} → {record['source']}")
    runtimes = runtime_summary(entries)
    if runtimes: print(f"runtimes: {runtimes}")
    print()
    for item in items:
        label = item['target'] + (f" ({item['harness']})" if item.get('harness') else '')
        if item['state'] == 'installed':
            detail = f"{item['files']} files"
            if item.get('sourceIdentity'): detail += f" · source {item['sourceIdentity']}"
            if item['recoveryRequired']:
                hint = f"omh recover --harness {item['harness']}" if item.get('harness') and item['harness'] != '?' else 'omh recover'
                print(f"  ✗ {label} · {detail} · recovery pending → {hint}")
            elif item['modified']:
                names = ', '.join(list(item['modified'])[:4]) + (' …' if len(item['modified']) > 4 else '')
                print(f"  ! {label} · {detail} · {len(item['modified'])} modified/missing: {names} (full list: omh status --json)")
            else:
                print(f"  ✓ {label} · {detail} · clean")
        elif item['state'] == 'missing':
            print(f"  ! {label} · receipt missing (uninstalled elsewhere or never installed)")
        else:
            extra = f" · {item.get('owner') or item.get('manager') or 'unreadable'}" if item['state'] != 'invalid-receipt' else ''
            print(f"  ! {label} · {item['state']}{extra}")
    if not items: print('no installed targets recorded')
    abnormal = [i for i in items if not clean(i)]
    print(f"\nsummary: {len(items)} target{'s' if len(items) != 1 else ''}, "
          + ('all clean' if not abnormal else f"{len(abnormal)} need attention"))

def shim_target(bin_dir):
    return (rt.safe_path(bin_dir if bin_dir is not None else Path.home() / '.local' / 'bin')) / SHIM_NAME

def shim_owned(content):
    return content is not None and content.split(b'\n', 2)[1:2] == [SHIM_MARKER.encode()]

def shim_script(source, python):
    # shlex.quote keeps Unicode literal and stops `$()` / quotes from being shell syntax.
    return ('#!/bin/sh\n' + SHIM_MARKER + '\n'
            + f'export PYTHONPATH={shlex.quote(str(source))}\n'
            + f'exec {shlex.quote(str(python))} -B -m omh "$@"\n').encode()

def shim_preflight(bin_dir):
    if os.name == 'nt': return
    current = data(shim_target(bin_dir))
    if current is not None and not shim_owned(current):
        rt.fail(f'Unowned {SHIM_NAME} launcher exists in the bin directory', 'HARNESS_CONFLICT')

def write_shim(home, bin_dir, source, python):
    if os.name == 'nt': return
    path = shim_target(bin_dir)
    script = shim_script(source, python)
    if data(path) != script:
        path.parent.mkdir(parents=True, exist_ok=True)
        rt.atomic(path, script)
        os.chmod(path, 0o755)
    rt.atomic(home / 'shim.json', rt.encode(dict(binDir=str(path.parent), path=str(path),
        source=str(source), python=str(python))))

def remove_shim(home):
    raw = data(home / 'shim.json')
    if raw is None: return
    path = rt.safe_path(Path(json.loads(raw)['path']))
    if shim_owned(data(path)): path.unlink()
    (home / 'shim.json').unlink(missing_ok=True)

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
        if not re.fullmatch(r'[0-9a-f]{64}', fingerprint) or not any(
                name.startswith(slot + '/') or name == slot for slot in item['slots']): rt.fail('Invalid ownership inventory')
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
    groups = manifest(source)['runtimeGroups']
    for index, spec in enumerate(groups, 1):
        progress(f"[{index}/{len(groups)}] preparing runtime '{spec['id']}' ...")
        result[spec['id']] = rt.prepare(dict(protocol=1, spec=spec, bundleRoot=str(source),
            python=str(python), deploymentRoot=str(deployment), externalVenv=str(external) if external else None,
            wheelCache=str(home / 'cache/wheels'), offline=offline))
        progress(f"[{index}/{len(groups)}] runtime '{spec['id']}' ready")
    # This is standalone configuration, never emitted by the runtime provider itself.
    # The lock covers the publish only; venv creation stays outside it.
    with rt.lock(home / HOME_LOCK):
        rt.atomic(home / 'runtime-state.json', rt.encode(result))
    return result

def bind_shared_scripts(content, support):
    """Rewrite the one OMH_SHARED_SCRIPTS assignment to the installed support directory.

    The constant is the contract. The repository expression may change shape;
    a missing or repeated assignment fails closed instead of shipping a stale path.
    """
    if b'OMH_SHARED_SCRIPTS' not in content: return content
    assignment = ('OMH_SHARED_SCRIPTS = Path(' + json.dumps(str(support)) + ')').encode()
    # A string replacement would treat \U in C:\Users as a unicode escape.
    updated, count = SHARED_ASSIGNMENT.subn(lambda _match: assignment, content)
    if count != 1: rt.fail('Helper shared-script binding must be a single assignment', 'OMH_INVALID')
    return updated

def projected(source, skills, prepared, harness):
    root = skills.parent
    value = manifest(source)
    output, slots, names = {}, set(), set()
    instructions = INSTRUCTIONS[harness]
    content = data(source / relative(INSTRUCTIONS_SOURCE))
    if content is None: rt.fail(f'Missing instructions source: {INSTRUCTIONS_SOURCE}', 'OMH_INVALID')
    output[instructions] = content
    slots.add(instructions)
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
            support = root / '.omh-support' / name
            for suffix, content in tree(skill).items():
                if '__pycache__' in Path(suffix).parts or suffix.endswith('.pyc'): continue
                if suffix.endswith('.py'): content = bind_shared_scripts(content, support)
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

def plan(source, home, skills, operation, prepared, harness):
    root = skills.parent
    old = receipt(root, home)
    if old is None and operation != 'uninstall':
        # A native plugin configuration is evidence of an existing installation.
        # An inert cache or marketplace entry alone is not an installation owner.
        config = data(root / 'config.toml')
        coordinates = {'oh-my-harness'}
        if config and any(name.encode() in config for name in coordinates):
            native = tomllib.loads(config.decode('utf-8'))
            if any(key.rsplit('@', 1)[-1] in coordinates for key in native.get('plugins', {})):
                rt.fail('Existing native OMH configuration needs explicit owner handoff', 'HARNESS_OWNER_CONFLICT')
    if operation != 'uninstall':
        for shadow in SHADOWS.get(harness, ()):
            if rt.safe_path(root / shadow).exists():
                rt.fail(f'Shadowing file conflicts with managed instructions: {shadow}', 'HARNESS_CONFLICT')
    if journal_path(home, root).exists(): rt.fail('Recovery required', 'HARNESS_RECOVERY_REQUIRED')
    desired, slots = ({}, []) if operation == 'uninstall' else projected(source, skills, prepared, harness)
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

EXIT_CODES = '''exit codes: 0 success (status: every target clean), 1 runtime error or a
target needing attention, 2 command-line usage error'''

def shared_flags(sub):
    # Placement bridge (ADR 0035): --source/--home parse before or after the
    # command. SUPPRESS keeps a subparser default from clobbering a value the
    # main parser already parsed.
    sub.add_argument('--source', type=Path, default=argparse.SUPPRESS,
        help='content source checkout (default: the installing checkout; absolute)')
    sub.add_argument('--home', type=Path, default=argparse.SUPPRESS,
        help='manager state directory (default ~/.oh-my-harness; absolute)')

def harness_flag(sub):
    sub.add_argument('--harness', choices=['codex', 'claude-code', 'grok'],
        help='harness target to manage (default codex)')

def skills_flag(sub):
    sub.add_argument('--skills-root', type=Path,
        help='skills directory to manage (default <harness root>/skills; absolute; with status: single-target view)')

def runtime_flags(sub):
    sub.add_argument('--deployment-root', type=Path,
        help='runtime deployment directory (default ~/.oh-my-harness/runtimes; absolute)')
    sub.add_argument('--python', type=Path,
        help='absolute bootstrap interpreter (default $OMH_PYTHON, else the current interpreter)')
    sub.add_argument('--external-venv', type=Path,
        help='absolute venv root reused for runtimes (verified, never modified)')
    sub.add_argument('--offline', action='store_true',
        help='prepare runtimes from cached wheels only; no network')

def json_flag(sub):
    sub.add_argument('--json', action='store_true',
        help='machine-readable JSON output (default is a human summary)')

def shim_flag(sub):
    sub.add_argument('--bin-dir', type=Path, help='POSIX launcher shim directory (default ~/.local/bin; absolute)')

def operation_flag(sub):
    sub.add_argument('--operation', choices=['install', 'update', 'uninstall'], default='install',
        help='operation to preview (default install)')

def build_parser():
    # ADR 0035: each command owns its flags; irrelevant ones are usage errors.
    parser = argparse.ArgumentParser(prog='omh',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Install and manage OMH skills for codex, claude-code and grok.',
        epilog=EXIT_CODES)
    parser.add_argument('--source', type=Path, default=SOURCE,
        help='content source checkout (default: the installing checkout; absolute)')
    parser.add_argument('--home', type=Path, default=Path.home() / '.oh-my-harness',
        help='manager state directory (default ~/.oh-my-harness; absolute)')
    commands = parser.add_subparsers(dest='command', required=True)
    def command(name, description, *groups):
        sub = commands.add_parser(name, description=description, help=description)
        for group in groups: group(sub)
    command('prepare', 'prepare Python runtimes without installing skills',
        shared_flags, runtime_flags, json_flag)
    command('install', 'project skills and instructions into the harness target',
        shared_flags, harness_flag, skills_flag, runtime_flags, shim_flag, json_flag)
    command('update', 'refresh an installed target; restores missing files',
        shared_flags, harness_flag, skills_flag, runtime_flags, shim_flag, json_flag)
    command('uninstall', 'remove a managed target and the shared launcher shim',
        shared_flags, harness_flag, skills_flag, json_flag)
    command('status', 'show every installed target and its health',
        shared_flags, harness_flag, skills_flag, json_flag)
    command('plan', 'preview file changes without writing (see --operation)',
        shared_flags, harness_flag, skills_flag, operation_flag, json_flag)
    command('recover', 'roll back or finish an interrupted transaction',
        shared_flags, harness_flag, skills_flag, json_flag)
    return parser

def result_text(command, result, root, harness):
    label = f"{root} ({harness})" if harness else f"{root}"
    if command == 'prepare': return 'prepared runtimes: ' + ', '.join(result['runtimes'])
    if command == 'recover':
        return f"recovered an interrupted transaction on {label}" if result['recovered'] else f"nothing to recover on {label}"
    if command == 'uninstall': return f"removed {result['changed']} managed files from {label}"
    text = f"applied {result['changed']} file changes to {label}"
    return text if result['changed'] else text + ' (up to date)'

def default_target_hint(home, harness, skills_flag, as_json):
    # Read-only nudge (ADR 0035): --harness defaults to codex, which is
    # probably not what a multi-harness home means.
    default_root = Path.home() / '.codex'
    if harness != 'codex' or skills_flag is not None or as_json: return
    indexed = load_targets(home)
    if str(default_root) in indexed or (default_root / OWNER).exists(): return
    others = sorted({entry.get('harness') for entry in indexed.values()} - {None, 'codex'})
    if others:
        print(f"note: --harness defaults to codex; installed targets: {', '.join(others)}", file=sys.stderr)

def main(argv=None):
    args = build_parser().parse_args(argv)
    # Deterministic UTF-8 on real text streams, including Windows pipes.
    # In-process captures such as io.StringIO have no reconfigure method.
    for stream, name in ((sys.stdout, 'stdout'), (sys.stderr, 'stderr')):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is None: continue
        try:
            reconfigure(encoding='utf-8')
        except (ValueError, OSError) as error:
            error_line('OMH_INVALID', f'{name} encoding: {error}')
            return 1
    try:
        home, source = rt.safe_path(args.home), rt.safe_path(args.source)
        bin_dir = getattr(args, 'bin_dir', None)
        if bin_dir is not None: bin_dir = rt.safe_path(bin_dir)
        harness = getattr(args, 'harness', None) or 'codex'
        skills_root = getattr(args, 'skills_root', None)
        skills = rt.safe_path(skills_root or Path.home() / HARNESS_ROOTS[harness] / 'skills')
        root = skills.parent
        if home == root or home.is_relative_to(root): rt.fail('Manager and skill target must be separate')
        if args.command not in ('status', 'prepare'):
            default_target_hint(home, harness, skills_root, args.json)
        if args.command == 'status':
            if skills_root is None:
                items = overview(home)
                print_overview(home, items, args.json)
                return 0 if all(clean(item) for item in items) else 1
            item = target_state(home, root)
            item['harness'] = harness
            if item['state'] == 'installed':
                print_overview(home, [item], args.json)
                return 0 if clean(item) else 1
            print_overview(home, [item], args.json)
            return 1
        if args.command == 'plan':
            raw = data(home / 'runtime-state.json')
            prepared = json.loads(raw) if raw else {}
            changes = plan(source,home,skills,args.operation,prepared,harness)
            if args.json:
                print(json.dumps(dict(changes=[c['path'] for c in changes])))
            else:
                added = sum(change['before'] is None for change in changes)
                removed = sum(change['after'] is None for change in changes)
                print(f"{args.operation} into {root} ({harness}): {len(changes)} changes")
                print(f"  add {added} · update {len(changes)-added-removed} · remove {removed}")
            return 0
        with rt.lock((home / '.prepare.lock') if args.command == 'prepare' else root / LOCK):
            if args.command == 'recover': result = dict(recovered=recover(home,root))
            elif args.command == 'uninstall':
                changes = plan(source,home,skills,'uninstall',{},harness)
                transact(home,root,changes)
                remember_target(home,root,harness,skills,False)
                remove_shim(home)
                result = dict(changed=len(changes))
            else:
                if args.command != 'prepare':
                    # Owner identity is enough here. Plan target files once,
                    # after preparing bindings; the journal rechecks before-images.
                    receipt(root,home)
                    shim_preflight(bin_dir)
                python = rt.absolute(args.python if args.python is not None else os.environ.get('OMH_PYTHON', sys.executable))
                deployment = rt.safe_path(args.deployment_root or home / 'runtimes')
                if deployment == root or deployment.is_relative_to(root) or root.is_relative_to(deployment): rt.fail('Runtime deployment and skill targets must be separate')
                prepared = prepare_runtimes(source,home,python,deployment,args.external_venv,args.offline)
                if args.command == 'prepare': result = dict(runtimes=prepared)
                else:
                    changes = plan(source,home,skills,args.command,prepared,harness)
                    transact(home,root,changes)
                    remember_target(home,root,harness,skills,True)
                    write_shim(home,bin_dir,source,python)
                    result = dict(changed=len(changes), runtimes=prepared)
        if args.json: print(json.dumps(result))
        else: print(result_text(args.command, result, root, harness))
        return 0
    except (rt.RuntimeFailure, OSError, ValueError, KeyError, TypeError) as error:
        error_line(getattr(error, 'code', 'OMH_INVALID'), str(error))
        return 1

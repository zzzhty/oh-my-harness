#!/usr/bin/env python3
"""OMH runtime protocol 1. No skill installer or global installed state.

Owners supply deploymentRoot (venv storage), bundleRoot and an explicit Python;
standalone supplies defaults. Prepare is the only operation allowed to create a
venv or invoke pip. The JSON request/response protocol uses argv, never a shell.
"""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile

class RuntimeFailure(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)

def fail(message, code='HARNESS_RUNTIME_INVALID'):
    raise RuntimeFailure(code, message)

def absolute(raw):
    p = Path(raw)
    if not p.is_absolute() or '..' in p.parts or any(ord(c) < 32 for c in str(p)):
        fail('An absolute, control-free path is required', 'HARNESS_RUNTIME_SPEC')
    return p

def safe_path(raw):
    p = absolute(raw)
    for item in [p, *p.parents]:
        try: metadata = item.lstat()
        except FileNotFoundError: continue
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, 'st_file_attributes', 0) & 0x400:
            fail('Linked deployment paths are not supported', 'HARNESS_RUNTIME_SPEC')
    return p

def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()

def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()

def atomic(path, data):
    safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.omh-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        if os.name != 'nt':
            fd = os.open(path.parent, os.O_RDONLY)
            try: os.fsync(fd)
            finally: os.close(fd)
    finally:
        if os.path.exists(name): os.unlink(name)

@contextlib.contextmanager
def lock(path):
    safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and (not path.is_file() or path.stat().st_nlink != 1): fail('Unsafe lock file')
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'r+b') as stream:
        try:
            if os.name == 'nt':
                import msvcrt
                stream.seek(0)
                if not stream.read(1):
                    stream.write(b'0'); stream.flush()
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            fail('Runtime or target is busy', 'HARNESS_RUNTIME_BUSY')
        try: yield
        finally:
            if os.name == 'nt':
                stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else: fcntl.flock(stream, fcntl.LOCK_UN)

def requirements(spec, bundle_root=None, locked=None):
    if (not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', spec['id'])
            or len(spec['minimumPython']) != 2 or spec['minimumPython'][0] != 3
            or spec['minimumPython'][1] < 11
            or any(not re.fullmatch(r'[A-Za-z0-9_]+', n) for n in spec['imports'])):
        fail('Invalid runtime specification', 'HARNESS_RUNTIME_SPEC')
    relative = spec.get('requirementsLock')
    if locked is None:
        locked = ''
        if relative:
            if '\\' in relative or ':' in relative or any(x in ('', '.', '..') for x in relative.split('/')):
                fail('Invalid lock path', 'HARNESS_RUNTIME_SPEC')
            path = safe_path(absolute(bundle_root) / relative)
            if path.stat().st_size > 1024 * 1024: fail('Lock too large')
            locked = path.read_text(encoding='utf-8')
    packages = {}
    for line in locked.replace('\\\r\n', ' ').replace('\\\n', ' ').splitlines():
        line = line.strip()
        if not line or line.startswith('#'): continue
        words = line.split()
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!_-]+)', words[0])
        if not match or len(words) < 2 or any(not re.fullmatch(r'--hash=sha256:[0-9a-fA-F]{64}', w) for w in words[1:]):
            fail('Only fully hashed, pinned requirements are supported', 'HARNESS_RUNTIME_SPEC')
        name, version = match.groups()
        if name in packages: fail('Duplicate package', 'HARNESS_RUNTIME_SPEC')
        packages[name] = version
    return locked, packages

PROBE = '''import importlib.util, importlib.metadata, json, sys
names, modules = json.loads(sys.argv[1])
distributions = {}
for name in names:
    try: distributions[name] = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError: distributions[name] = ''
print(json.dumps({'version': list(sys.version_info[:2]), 'prefix': sys.prefix, 'basePrefix': sys.base_prefix, 'distributions': distributions, 'modules': {name: importlib.util.find_spec(name) is not None for name in modules}}))
'''

def process_environment():
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV', 'PIP_TARGET', 'PIP_PREFIX', 'PIP_USER')}
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    # pip --isolated still reads explicit/global/site configuration. Disabling
    # all config prevents an inherited target/prefix from escaping this venv.
    env['PIP_CONFIG_FILE'] = os.devnull
    return env

class WindowsJob:
    """A kill-on-close job also covers children of venv/pip on Windows."""
    def __init__(self, process):
        self.handle = None
        if os.name != 'nt': return
        import ctypes
        from ctypes import wintypes
        class Basic(ctypes.Structure):
            _fields_ = [('processTime', ctypes.c_int64), ('jobTime', ctypes.c_int64), ('flags', wintypes.DWORD),
                        ('minimum', ctypes.c_size_t), ('maximum', ctypes.c_size_t), ('active', wintypes.DWORD),
                        ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in ('readOps','writeOps','otherOps','readBytes','writeBytes','otherBytes')]
        class Extended(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', IO), ('processMemory', ctypes.c_size_t), ('jobMemory', ctypes.c_size_t),
                        ('peakProcess', ctypes.c_size_t), ('peakJob', ctypes.c_size_t)]
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateJobObjectW.restype = wintypes.HANDLE
        kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.CreateJobObjectW(None, None)
        info = Extended(); info.basic.flags = 0x2000
        if not handle or not kernel.SetInformationJobObject(handle, 9, ctypes.byref(info), ctypes.sizeof(info)) or not kernel.AssignProcessToJobObject(handle, wintypes.HANDLE(int(process._handle))):
            if handle: kernel.CloseHandle(handle)
            process.kill(); process.wait()
            fail('Cannot isolate the runtime process job')
        self.kernel, self.handle = kernel, handle
    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle); self.handle = None

def process_tail(raw, limit=2000):
    text = (raw or b'').decode('utf-8', 'replace').strip()
    if len(text) <= limit: return text
    return text[-limit:]

def run_process(python, args, timeout=30, failure_code='HARNESS_RUNTIME_INVALID'):
    python = absolute(python)
    if not python.is_file(): fail('Explicit Python is missing', 'HARNESS_PYTHON_REQUIRED')
    try:
        process = subprocess.Popen([str(python), *map(str, args)], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=process_environment(), start_new_session=(os.name != 'nt'))
    except OSError:
        fail('Cannot execute explicit Python', 'HARNESS_PYTHON_REQUIRED')
    job = WindowsJob(process)
    try:
        try: output, err = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as expired:
            if os.name != 'nt': os.killpg(process.pid, signal.SIGKILL)
            else: process.kill()
            job.close()
            process.wait()
            chunks = []
            if expired.stderr and expired.stderr.strip(): chunks.append(b'stderr:\n' + expired.stderr)
            if expired.stdout and expired.stdout.strip(): chunks.append(b'stdout:\n' + expired.stdout)
            detail = process_tail(b'\n'.join(chunks))
            fail('Runtime process timed out' + (f': {detail}' if detail else ''), 'HARNESS_RUNTIME_TIMEOUT')
        if process.returncode:
            # venv writes ensurepip failures to stdout; pip uses stderr. Keep both.
            chunks = []
            if err and err.strip(): chunks.append(b'stderr:\n' + err)
            if output and output.strip(): chunks.append(b'stdout:\n' + output)
            detail = process_tail(b'\n'.join(chunks))
            fail('Runtime process failed' + (f': {detail}' if detail else ''), failure_code)
        if len(output) > 65536: fail('Runtime process output exceeds the protocol limit')
        return output
    finally: job.close()

def probe(python, spec, packages, root=None):
    value = json.loads(run_process(python, ['-I', '-B', '-c', PROBE, json.dumps([list(packages), spec['imports']])]))
    if (value['version'][0] != 3 or value['version'] < spec['minimumPython']
            or value['distributions'] != packages or not all(value['modules'].get(n) for n in spec['imports'])):
        fail('Interpreter version or dependencies do not match the content')
    if root is not None and (Path(value['prefix']).resolve() != Path(root).resolve() or value['prefix'] == value['basePrefix']):
        fail('The interpreter is not in the selected venv')
    return value

def venv_python(root, windows=None):
    return Path(root) / ('Scripts/python.exe' if (os.name == 'nt' if windows is None else windows) else 'bin/python')

def pip_arguments(path, wheels, offline):
    args = ['-I', '-m', 'pip', '--isolated', '--disable-pip-version-check', 'install', '--no-input', '--require-hashes', '--only-binary=:all:', '--no-cache-dir', '--no-compile']
    if offline: args += ['--no-index', '--find-links', str(wheels)]
    return args + ['--requirement', str(path)]

def verify_python(spec, prepared, packages):
    root = absolute(prepared['root'])
    if prepared['id'] != spec['id']: fail('Runtime binding does not match the selected group')
    # Actual venv membership and requirements are authoritative. Old manager
    # markers, identity encodings and interpreter aliases do not affect execution.
    probe(prepared['python'], spec, packages, root)
    return prepared

def verify(spec, prepared, locked):
    return verify_python(spec, prepared, requirements(spec, locked=locked)[1])

def preparation_links(root, interpreter, version, with_packages):
    """Check only the trees venv/pip may rewrite during a managed retry."""
    names = ('pyvenv.cfg', 'Scripts', 'Lib', 'Include') if os.name == 'nt' else ('pyvenv.cfg', 'bin', 'lib', 'lib64', 'include')
    # Wheel data can address the whole prefix; stdlib-only preparation rewrites
    # just venv's own trees and leaves unrelated root entries alone.
    pending = list(root.iterdir()) if with_packages else [root / name for name in names]
    python_links = []
    python_names = {'python', 'python3', f'python3.{version[1]}', interpreter.resolve().name}
    while pending:
        path = pending.pop()
        try: metadata = path.lstat()
        except FileNotFoundError: continue
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, 'st_file_attributes', 0) & 0x400:
            # lib64 is the standard internal alias; inspect its real lib tree.
            if path == root / 'lib64' and path.resolve() == root / 'lib': continue
            if (os.name != 'nt' and path.parent == root / 'bin'
                    and path.name in python_names
                    and path.resolve() == interpreter.resolve()):
                python_links.append(path)
                continue
            fail(f'Preparation would write through a link: {path}')
        if stat.S_ISDIR(metadata.st_mode): pending.extend(path.iterdir())
        elif metadata.st_nlink > 1: fail(f'Preparation would overwrite a shared file: {path}')
    return python_links

def prepare(request):
    spec = request['spec']
    locked, packages = requirements(spec, request['bundleRoot'])
    interpreter = absolute(request['python'])
    if not interpreter.is_file(): fail('Explicit Python is missing', 'HARNESS_PYTHON_REQUIRED')
    if request.get('externalVenv'):
        # The bootstrap runs the protocol; the external interpreter runs helpers.
        # Its helper minimum need not apply to the bootstrap itself.
        probe(interpreter, {**spec, 'minimumPython': [3,11], 'imports': []}, {})
        root = absolute(request['externalVenv']).resolve(strict=True)
        prepared = dict(id=spec['id'], identity=digest([spec, locked, str(root)]), root=str(root), python=str(venv_python(root)), external=True)
        return verify_python(spec, prepared, packages)
    deployment = safe_path(request['deploymentRoot'])
    identity = digest([spec, locked, str(interpreter.resolve()), hashlib.sha256(interpreter.read_bytes()).hexdigest()])
    root = deployment / spec['id'] / identity
    prepared = dict(id=spec['id'], identity=identity, root=str(root), python=str(venv_python(root)), external=False, deploymentRoot=str(deployment))
    descriptor = {'prepared': prepared, 'spec': spec, 'lock': locked}
    base_checked = not root.exists()
    if base_checked: base = probe(interpreter, {**spec, 'imports': []}, {})
    with lock(root.parent / '.prepare.lock'):
        safe_path(root)
        marker = root / '.omh-runtime.json'
        if root.exists():
            try: return verify_python(spec, prepared, packages)
            except RuntimeFailure as error:
                if error.code not in ('HARNESS_RUNTIME_INVALID', 'HARNESS_PYTHON_REQUIRED'): raise
            try: recorded = json.loads(safe_path(marker).read_bytes())
            except (FileNotFoundError, ValueError): recorded = {}
            owned = isinstance(recorded, dict) and all(recorded.get(k) == v for k,v in descriptor.items())
            if not owned and any(root.iterdir()):
                fail('Existing incompatible directory is not an OMH preparation; choose another deployment root')
            if not base_checked: base = probe(interpreter, {**spec, 'imports': []}, {})
        else: root.mkdir()
        # Record ownership before building. Explicit prepare can resume this
        # same final path after interruption without deleting or moving a venv.
        python_links = preparation_links(root, interpreter, base['version'], bool(packages))
        atomic(marker, encode(descriptor))
        for path in python_links: path.unlink()  # Replace ordinary venv aliases with private copies.
        # Final path, never a staged directory. Stdlib-only groups skip ensurepip.
        # ADR 0037: private executable copies stay the default; relocated builds
        # (uv-managed CPython) seed copies that cannot locate the standard
        # library, so the executables are removed and a symlinked seeding is
        # verified in its place — never a silently broken environment.
        seed = '--copies'
        for strategy in ('--copies', '--symlinks'):
            if strategy == '--symlinks':
                # venv silently falls back to copying when an executable already
                # exists; remove them so the symlinked seeding can take hold.
                binaries = root / ('Scripts' if os.name == 'nt' else 'bin')
                if binaries.is_dir():
                    for executable in binaries.glob('python*'): executable.unlink()
            venv_args = ['-I', '-B', '-m', 'venv', strategy]
            if not packages: venv_args.append('--without-pip')
            run_process(interpreter, [*venv_args, str(root)], 120)
            try:
                probe(prepared['python'], {**spec, 'imports': []}, {}, root)
                seed = strategy
                break
            except RuntimeFailure:
                if strategy == '--symlinks': raise
        atomic(marker, encode({**descriptor, 'seed': seed}))
        if packages:
            lock_path = root / 'requirements.lock'
            atomic(lock_path, locked.encode())
            wheels = safe_path(request['wheelCache'])
            run_process(prepared['python'], pip_arguments(lock_path, wheels, request['offline']), 300,
                failure_code='HARNESS_RUNTIME_OFFLINE_MISSING' if request['offline'] else 'HARNESS_RUNTIME_INVALID')
        return verify_python(spec, prepared, packages)

def binding_files(spec, prepared, bundle_root):
    locked, _ = requirements(spec, bundle_root)
    files = {f'{spec["id"]}.json': encode({'protocol': 1, 'spec': spec, 'prepared': prepared, 'lock': locked}),
             f'{spec["id"]}.python': ((prepared['python'] if prepared else '') + '\n').encode()}
    for name in ('omh_runtime.py', 'run.sh', 'run.ps1'):
        files[name] = (Path(__file__).parent / name).read_bytes()
    return files

def launch(binding, argv):
    value = json.loads(safe_path(binding).read_text(encoding='utf-8'))
    if value['protocol'] != 1: fail('Unsupported binding protocol')
    spec, prepared, locked = value['spec'], value['prepared'], value['lock']
    if 'OMH_PYTHON' in os.environ:
        python = absolute(os.environ['OMH_PYTHON'])
        _, packages = requirements(spec, locked=locked)
        result = probe(python, spec, packages)
        if result['prefix'] == result['basePrefix']: fail('OMH_PYTHON must select a venv')
    else:
        if not prepared: fail('Prepare this runtime before running helpers', 'HARNESS_PYTHON_REQUIRED')
        verify(spec, prepared, locked)
        python = Path(prepared['python'])
    if not argv: fail('Provide a helper script and its arguments')
    # Helper exit status and stdout are the caller's result. No pip on this path.
    return subprocess.call([str(python), '-E', '-s', '-B', *argv], env=process_environment())

def main():
    parser = argparse.ArgumentParser(prog='omh_runtime',
        description='OMH shared runtime provider: JSON request/response protocol over argv, never a shell.')
    parser.add_argument('operation', choices=['prepare', 'verify', 'run'],
        help='prepare: build or reuse a runtime from a JSON --request; verify: validate one; run: launch a bound helper')
    parser.add_argument('--request', help='JSON request object (required for prepare/verify)')
    parser.add_argument('--binding', type=Path, help='binding file from .omh-runtime (required for run)')
    args, argv = parser.parse_known_args()
    # Only run forwards helper argv (after --); prepare/verify are closed protocols,
    # so leftover arguments mean a typo that must not masquerade as a protocol error.
    if args.operation == 'run':
        if args.binding is None: parser.error('--binding is required for run')
    else:
        if argv: parser.error(f'unrecognized arguments: {" ".join(argv)}')
        if args.request is None: parser.error(f'--request is required for {args.operation}')
    try:
        if args.operation == 'run':
            return launch(args.binding, argv[1:] if argv[:1] == ['--'] else argv)
        request = json.loads(args.request)
        if request['protocol'] != 1: fail('Unsupported runtime protocol')
        result = prepare(request) if args.operation == 'prepare' else verify(request['spec'], request['prepared'], requirements(request['spec'], request['bundleRoot'])[0])
        print(json.dumps({'ok': result}))
        return 0
    except (RuntimeFailure, OSError, ValueError, KeyError, TypeError) as error:
        envelope = json.dumps({'error': {'code': getattr(error, 'code', 'HARNESS_RUNTIME_INVALID'), 'message': str(error)}})
        # ADR 0030: prepare/verify answer on stdout and exit zero so an
        # integration reads the error code. run preserves the helper's stdout
        # as the caller's result, so its startup failures go to stderr.
        if args.operation == 'run': print(envelope, file=sys.stderr)
        else: print(envelope)
        return 1 if args.operation == 'run' else 0

if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Dependency-free launcher and recovery entry point, outside the managed checkout."""
from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path

MINIMUM_PYTHON_VERSION = (3, 11)
_REQUIRED_FILES = ("scripts/omh.py", "scripts/bootstrap_tooling_env.py", "requirements.txt")


def _require_supported_python() -> None:
    current = sys.version_info[:3]
    if current[:2] < MINIMUM_PYTHON_VERSION:
        raise SystemExit(
            f"Python 3.11 or newer is required; found Python {'.'.join(map(str, current))} "
            f"at {sys.executable}. Set OH_MY_HARNESS_BOOTSTRAP_PYTHON to a supported interpreter."
        )


def _ordinary(path: Path, *, directory: bool = False) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    reparse = getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    expected = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if reparse or not expected:
        raise SystemExit(f"refusing non-ordinary {'directory' if directory else 'file'}: {path}")


def _state_root(home: Path) -> Path:
    _ordinary(home, directory=True)
    _ordinary(home / "state", directory=True)
    return home / "state"


def _load_json(path: Path) -> dict[str, object] | None:
    _ordinary(path)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"unreadable state; preserved without resetting: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"state must be an object: {path}")
    return payload


def _recorded_source(home: Path) -> tuple[str, str]:
    root = _state_root(home)
    state = _load_json(root / "manager.json")
    if state is None:
        state = _load_json(root / "install.json")
    if state is None:
        raise SystemExit("manager source state is unavailable; restore the state receipt from a backup or install into a new manager home")
    if state.get("product") != "oh-my-harness":
        raise SystemExit("source receipt does not belong to oh-my-harness; no files were replaced")
    repository, revision = state.get("repository"), state.get("revision")
    if not isinstance(repository, str) or not repository.strip():
        raise SystemExit("manager source state has no repository")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", revision):
        raise SystemExit("manager source state has no full Git revision")
    return repository, revision


def _is_manager_repair(arguments: list[str]) -> bool:
    return bool(arguments) and (arguments[0] == "repair" or arguments[:2] == ["manager", "repair"])


def _is_help_request(arguments: list[str]) -> bool:
    for argument in arguments:
        if argument == "--":
            break
        if argument in {"-h", "--help", "-Help"}:
            return True
    return False


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "--no-optional-locks", "-C", str(repo), *args], text=True, capture_output=True, check=check)


@contextmanager
def _mutation_lock(home: Path):
    """Use the same OS lock as manager_state, including before venv/checkout repair."""
    root = _state_root(home)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "manager.lock"
    _ordinary(path)
    with path.open("a+b") as handle:
        handle.seek(0)
        handle.write(b"\0")
        handle.flush()
        try:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise SystemExit(f"another oh-my-harness mutation is already running: {path}") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _repair_checkout(home: Path, *, force: bool = False, dry_run: bool = False) -> None:
    repository, revision = _recorded_source(home)
    repo = home / "repo"
    _ordinary(repo, directory=True)
    _ordinary(repo / ".git", directory=True)
    operations = home / "state" / "operations"
    _ordinary(operations, directory=True)
    operation = _load_json(operations / "current.json")
    allowed_revisions = {revision}
    if operation is not None:
        if operation.get("command") != "update":
            raise SystemExit("unsupported interrupted operation; journal preserved for inspection")
        before, target = operation.get("before"), operation.get("target")
        if not isinstance(before, dict) or not isinstance(target, dict):
            raise SystemExit("interrupted update has invalid transition state")
        for item in (before, target):
            value = item.get("revision")
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", value):
                raise SystemExit("interrupted update has an invalid revision")
            allowed_revisions.add(value)
        # A missing checkout must first regain the journaled rollback version.
        revision = str(before["revision"])
    valid_git = (repo / ".git").is_dir()
    if valid_git and not force:
        head = _git(repo, "rev-parse", "--verify", "HEAD", check=False)
        status = _git(repo, "status", "--porcelain", check=False)
        remote = _git(repo, "config", "--get", "remote.origin.url", check=False)
        if (head.returncode == status.returncode == remote.returncode == 0
                and head.stdout.strip() in allowed_revisions and not status.stdout.strip()
                and remote.stdout.strip() == repository
                and all((repo / name).is_file() for name in _REQUIRED_FILES)):
            print("managed checkout is healthy; no clone required")
            return
    if dry_run:
        print(f"would restore checkout at {revision[:12]}; preserve the replaced checkout under state/repair-backups")
        return
    if shutil.which("git") is None:
        raise SystemExit("Git is required to restore the managed checkout")
    local_source = False
    if valid_git and not force:
        local_source = _git(repo, "cat-file", "-e", f"{revision}^{{commit}}", check=False).returncode == 0
    staging = home / f".repo.repair-{uuid.uuid4().hex}"
    backups = home / "state" / "repair-backups"
    _ordinary(backups, directory=True)
    backups.mkdir(parents=True, exist_ok=True)
    backup = backups / f"repo-{uuid.uuid4().hex}"
    try:
        source = str(repo) if local_source else repository
        subprocess.run(["git", "clone", "--no-hardlinks", "--no-checkout", "--", source, str(staging)], check=True)
        if local_source:
            _git(staging, "remote", "set-url", "origin", repository)
        _git(staging, "checkout", "--detach", revision)
        missing = [name for name in _REQUIRED_FILES if not (staging / name).is_file()]
        if missing:
            raise SystemExit("restored revision is missing manager entry points: " + ", ".join(missing))
        if repo.exists():
            repo.rename(backup)
        try:
            staging.rename(repo)
        except BaseException:
            if backup.exists() and not repo.exists():
                backup.rename(repo)
            raise
    finally:
        if staging.is_dir() and not staging.is_symlink():
            shutil.rmtree(staging)
    print(f"restored managed checkout at {revision[:12]} ({'local Git objects' if local_source else 'recorded repository'})")
    if backup.exists():
        print(f"previous checkout preserved: {backup}")


def _venv_python(home: Path) -> Path:
    return home / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _fallback_help() -> None:
    print("""omh install [HARNESS ...]    Install harness distributions
omh update [main|stable|REF] Update using the saved channel, or select a target
omh repair [HARNESS ...]     Repair the recorded installation and managed outputs
  --rebuild                 Rebuild the tooling venv
  --reclone                 Restore checkout from the recorded remote (keep a backup)
  --dry-run                 Show recovery steps without writing
omh status / doctor         Inspect state / validate distributions
omh manager repair          Compatibility spelling of omh repair
Runtime is not bootstrapped for help. Run omh repair to restore it.""")


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) < 2 or arguments[0] != "--home":
        raise SystemExit("bootstrap shim requires --home <absolute-path>")
    selected_home = arguments[1]
    command_arguments = arguments[2:]
    # A caller may override the launcher home using the public global option.
    while command_arguments:
        if command_arguments[0] == "--home":
            if len(command_arguments) < 2:
                raise SystemExit("--home requires an absolute path")
            selected_home = command_arguments[1]
            command_arguments = command_arguments[2:]
        elif command_arguments[0].startswith("--home="):
            selected_home = command_arguments.pop(0).split("=", 1)[1]
        else:
            break
    home = Path(selected_home).expanduser()
    if not home.is_absolute():
        raise SystemExit(f"manager home must be absolute: {home}")
    home = Path(os.path.abspath(home))
    repo = home / "repo"
    cli = repo / "scripts" / "omh.py"
    bootstrap = repo / "scripts" / "bootstrap_tooling_env.py"
    tooling_python = _venv_python(home)
    help_request = _is_help_request(command_arguments)
    if help_request:
        if cli.is_file() and tooling_python.is_file():
            completed = subprocess.run([
                str(tooling_python), str(cli), "--home", str(home),
                *("--help" if arg == "-Help" else arg for arg in command_arguments),
            ])
            return completed.returncode
        _fallback_help()
        return 0
    _require_supported_python()
    repair = _is_manager_repair(command_arguments)
    dry_run = "--dry-run" in command_arguments
    if repair and dry_run:
        _repair_checkout(home, force="--reclone" in command_arguments, dry_run=True)
        print("would check/rebuild tooling, restore launchers and user PATH, recover an interrupted update, then repair and check selected harnesses")
        return 0
    if dry_run:
        # A preview must not run pip, create a venv, or acquire a creating lock.
        executable = tooling_python if tooling_python.is_file() else Path(sys.executable)
        return subprocess.run([str(executable), str(cli), "--home", str(home), *command_arguments]).returncode
    with _mutation_lock(home):
        if repair:
            _repair_checkout(home, force="--reclone" in command_arguments)
        elif not cli.is_file() or not bootstrap.is_file():
            raise SystemExit("managed checkout is unavailable; run `omh repair` or rerun the external installer")
        command = [sys.executable, str(bootstrap), "--venv", str(home / "venv")]
        if repair and "--rebuild" in command_arguments:
            command.append("--rebuild")
        subprocess.run(command, check=True)
    if not tooling_python.is_file():
        raise SystemExit(f"tooling Python is unavailable after bootstrap: {tooling_python}")
    env = dict(os.environ)
    if repair:
        env["OH_MY_HARNESS_REPAIR_BOOTSTRAPPED"] = str(home)
        if command_arguments[0] == "repair":
            command_arguments = ["manager", "repair", *command_arguments[1:]]
        command_arguments = [arg for arg in command_arguments if arg not in {"--rebuild", "--reclone"}]
    completed = subprocess.run([str(tooling_python), str(cli), "--home", str(home), *command_arguments], env=env)
    return completed.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip() if isinstance(exc.stderr, str) else ""
        print(f"bootstrap command failed ({exc.returncode}): {detail or exc.cmd}", file=sys.stderr)
        raise SystemExit(exc.returncode if exc.returncode > 0 else 1) from exc
    except OSError as exc:
        raise SystemExit(f"bootstrap failure: {exc}") from exc

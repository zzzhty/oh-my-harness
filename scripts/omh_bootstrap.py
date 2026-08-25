#!/usr/bin/env python3
"""Stable manager-home bootstrap shim for the public omh launcher."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


MINIMUM_PYTHON_VERSION = (3, 11)


def _require_supported_python() -> None:
    current = sys.version_info[:3]
    if current[:2] >= MINIMUM_PYTHON_VERSION:
        return
    required = ".".join(str(component) for component in MINIMUM_PYTHON_VERSION)
    found = ".".join(str(component) for component in current)
    executable = Path(sys.executable).expanduser().resolve(strict=False)
    raise SystemExit(
        f"Python {required} or newer is required; found Python {found} at {executable}. "
        "Use a supported interpreter directly, or set OH_MY_HARNESS_BOOTSTRAP_PYTHON "
        "for the installer and omh launchers."
    )


def _load_json(path: Path) -> dict[str, object] | None:
    if not path.is_file() or path.is_symlink():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _recorded_source(home: Path) -> tuple[str, str]:
    state = _load_json(home / "state" / "manager.json")
    if state is None:
        state = _load_json(home / "state" / "install.json")
    if state is None:
        raise SystemExit("manager source state is unavailable; rerun the external installer")
    repository = state.get("repository")
    revision = state.get("revision")
    if not isinstance(repository, str) or not repository:
        raise SystemExit("manager source state has no repository")
    if not isinstance(revision, str) or not revision:
        raise SystemExit("manager source state has no revision")
    return repository, revision


def _is_manager_repair(arguments: list[str]) -> bool:
    stripped = [arg for arg in arguments if not arg.startswith("--home")]
    return len(stripped) >= 2 and stripped[0] == "manager" and stripped[1] == "repair"


def _is_help_request(arguments: list[str]) -> bool:
    return bool(arguments) and arguments[0] in {"-h", "--help", "-Help"}


def _repair_checkout(home: Path) -> None:
    repository, revision = _recorded_source(home)
    repo = home / "repo"
    if repo.is_symlink():
        raise SystemExit(f"refusing linked manager repository root: {repo}")
    staging = home / f".repo.repair-{uuid.uuid4().hex}"
    backup = home / f".repo.backup-{uuid.uuid4().hex}"
    if staging.exists():
        raise SystemExit(f"manager repair staging path already exists: {staging}")
    try:
        subprocess.run(
            ["git", "clone", "--no-checkout", "--", repository, str(staging)],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(staging), "checkout", "--detach", revision],
            check=True,
        )
        if repo.exists():
            if not repo.is_dir():
                raise SystemExit(f"manager repository root is not a directory: {repo}")
            repo.rename(backup)
        staging.rename(repo)
    except BaseException:
        if staging.is_dir():
            shutil.rmtree(staging, ignore_errors=True)
        if backup.exists() and not repo.exists():
            backup.rename(repo)
        raise
    if backup.is_dir():
        shutil.rmtree(backup)
    print(f"restored managed checkout at revision {revision[:12]}")


def _venv_python(home: Path) -> Path:
    if os.name == "nt":
        return home / "venv" / "Scripts" / "python.exe"
    return home / "venv" / "bin" / "python"


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) < 2 or arguments[0] != "--home":
        raise SystemExit("bootstrap shim requires --home <absolute-path>")
    home = Path(arguments[1]).expanduser()
    if not home.is_absolute():
        raise SystemExit(f"manager home must be absolute: {home}")
    command_arguments = arguments[2:]
    repo = home / "repo"
    cli = repo / "scripts" / "omh.py"
    bootstrap = repo / "scripts" / "bootstrap_tooling_env.py"

    help_request = _is_help_request(command_arguments)
    if not help_request:
        _require_supported_python()

    manager_repair = _is_manager_repair(command_arguments)
    if manager_repair:
        _repair_checkout(home)
        cli = repo / "scripts" / "omh.py"
        bootstrap = repo / "scripts" / "bootstrap_tooling_env.py"
    elif not cli.is_file() or not bootstrap.is_file():
        raise SystemExit(
            "managed checkout is unavailable; run `omh manager repair` or rerun "
            "the external installer if manager state is missing"
        )

    if help_request:
        completed = subprocess.run(
            [sys.executable, str(cli), "--home", str(home), "--help"]
        )
        return completed.returncode

    subprocess.run(
        [
            sys.executable,
            str(bootstrap),
            "--venv",
            str(home / "venv"),
        ],
        check=True,
    )
    tooling_python = _venv_python(home)
    if not tooling_python.is_file():
        raise SystemExit(f"tooling Python is unavailable after bootstrap: {tooling_python}")
    completed = subprocess.run(
        [
            str(tooling_python),
            str(cli),
            "--home",
            str(home),
            *command_arguments,
        ]
    )
    return completed.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc
    except OSError as exc:
        raise SystemExit(f"bootstrap failure: {exc}") from exc

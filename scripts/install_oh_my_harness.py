#!/usr/bin/env python3
"""Initialize one managed oh-my-harness installation."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import uuid
from pathlib import Path

from manager_paths import (
    PRODUCT_NAME,
    bin_path,
    expand_path,
    manager_home,
    repo_path,
    state_path,
    venv_path,
    venv_python,
)
from terminal_output import write_stderr


SOURCE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REF = "main"


def command_text(command: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(command)
    return shlex.join(command)


def run(command: list[str], *, dry_run: bool = False, cwd: Path | None = None) -> None:
    print("+ " + command_text(command), flush=True)
    if dry_run:
        return
    subprocess.run(command, cwd=cwd, check=True)


def bootstrap_python() -> Path:
    raw = getattr(sys, "_base_executable", None) or sys.executable
    try:
        resolved = Path(raw).expanduser().resolve(strict=True)
    except OSError as exc:
        raise SystemExit(f"bootstrap Python cannot be resolved: {raw}: {exc}") from exc
    if not resolved.is_file():
        raise SystemExit(f"bootstrap Python is not a file: {resolved}")
    return resolved


def repository_from_checkout(source_root: Path = SOURCE_ROOT) -> str:
    result = subprocess.run(
        ["git", "-C", str(source_root), "config", "--get", "remote.origin.url"],
        capture_output=True,
        text=True,
    )
    repository = result.stdout.strip() if result.returncode == 0 else ""
    if not repository:
        raise SystemExit(
            "repository source is required; pass --repository or run the installer "
            "from a checkout with remote.origin.url"
        )
    return repository


def validate_install_root(
    home: Path,
    *,
    adopted_repo: Path | None = None,
    allowed_existing: frozenset[Path] = frozenset(),
) -> None:
    if home.is_symlink():
        raise SystemExit(f"manager home must not be a symlink: {home}")
    if home.exists() and not home.is_dir():
        raise SystemExit(f"manager home is not a directory: {home}")
    managed_paths = (repo_path(home), venv_path(home), bin_path(home), state_path(home))
    occupied = []
    for path in managed_paths:
        if not (path.exists() or path.is_symlink()):
            continue
        if (
            adopted_repo is not None
            and path == repo_path(home)
            and path.resolve(strict=True) == adopted_repo.resolve(strict=True)
        ):
            continue
        if path in allowed_existing:
            continue
        occupied.append(path)
    if occupied:
        raise SystemExit(
            "refusing to initialize over existing manager-owned paths: "
            + ", ".join(str(path) for path in occupied)
        )


def clone_repository(
    repository: str,
    *,
    ref: str,
    home: Path,
    dry_run: bool,
) -> Path:
    target = repo_path(home)
    temporary = home / f".repo.install-{uuid.uuid4().hex}"
    command = [
        "git",
        "clone",
        "--branch",
        ref,
        "--single-branch",
        "--",
        repository,
        str(temporary),
    ]
    if dry_run:
        run(command, dry_run=True)
        print(f"would activate managed checkout: {temporary} -> {target}")
        return target

    home.mkdir(parents=True, exist_ok=True)
    try:
        run(command)
        temporary.rename(target)
    except BaseException:
        if temporary.is_dir() and not temporary.is_symlink():
            shutil.rmtree(temporary)
        raise
    return target


def launcher_paths(home: Path) -> tuple[Path, Path]:
    root = bin_path(home)
    if os.name == "nt":
        return root / "oh-my-harness.cmd", root / "omh.cmd"
    return root / "oh-my-harness", root / "omh"


def launcher_help_invocation(platform_name: str) -> str:
    return "omh -Help" if platform_name == "nt" else "omh --help"


def posix_launcher(*, home: Path, repo: Path) -> str:
    wrapper = repo / "scripts" / "upgrade_oh_my_harness.sh"
    return (
        "#!/usr/bin/env sh\n"
        "set -eu\n"
        f"exec {shlex.quote(str(wrapper))} --home {shlex.quote(str(home))} \"$@\"\n"
    )


def windows_launcher(*, home: Path, repo: Path) -> str:
    wrapper = repo / "scripts" / "upgrade_oh_my_harness.ps1"
    return (
        "@echo off\r\n"
        "powershell.exe -NoProfile -ExecutionPolicy Bypass "
        f'-File "{wrapper}" -ManagerHome "{home}" %*\r\n'
    )


def expected_launcher_content(*, home: Path, repo: Path) -> str:
    if os.name == "nt":
        return windows_launcher(home=home, repo=repo)
    return posix_launcher(home=home, repo=repo)


def write_launchers(*, home: Path, repo: Path, dry_run: bool) -> tuple[Path, Path]:
    paths = launcher_paths(home)
    content = expected_launcher_content(home=home, repo=repo)
    for path in paths:
        print(f"{'would write' if dry_run else 'write'} launcher: {path}")
        if dry_run:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.parent / f".{path.name}.install-{uuid.uuid4().hex}"
        temporary.write_text(content, encoding="utf-8", newline="")
        if os.name != "nt":
            temporary.chmod(
                temporary.stat().st_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH
            )
        os.replace(temporary, path)
    return paths


def installed_revision(repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise SystemExit(f"managed checkout revision is unavailable: {repo}")
    return result.stdout.strip()


def validate_revision_fast_forward(
    *,
    repo: Path,
    repository: str,
    ref: str,
    previous_revision: str,
    current_revision: str,
) -> None:
    for label, revision in (
        ("recorded", previous_revision),
        ("current", current_revision),
    ):
        if len(revision) not in {40, 64} or any(
            character not in "0123456789abcdefABCDEF" for character in revision
        ):
            raise SystemExit(
                f"incomplete installation {label} revision is not a full Git object id"
            )

    status = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    if status.returncode != 0:
        raise SystemExit("managed checkout status is unavailable for fast-forward resume")
    if status.stdout.strip():
        raise SystemExit(
            "managed checkout has uncommitted changes; refusing fast-forward resume"
        )

    actual_repository = repository_from_checkout(repo)
    if actual_repository != repository:
        raise SystemExit(
            "managed checkout remote does not match the recorded installation repository"
        )

    remote_ref = f"refs/remotes/origin/{ref}"
    remote = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", remote_ref],
        capture_output=True,
        text=True,
    )
    remote_revision = remote.stdout.strip() if remote.returncode == 0 else ""
    if not remote_revision:
        raise SystemExit(
            f"managed checkout remote tracking ref is unavailable: {remote_ref}"
        )
    if remote_revision != current_revision:
        raise SystemExit(
            "managed checkout HEAD is not the published requested ref; "
            f"expected {remote_ref} at {current_revision}, found {remote_revision}"
        )

    ancestor = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "merge-base",
            "--is-ancestor",
            previous_revision,
            current_revision,
        ],
        capture_output=True,
        text=True,
    )
    if ancestor.returncode == 1:
        raise SystemExit(
            "managed checkout revision did not fast-forward from the incomplete "
            "installation revision"
        )
    if ancestor.returncode != 0:
        raise SystemExit(
            "managed checkout ancestry is unavailable for fast-forward resume"
        )


def validate_incomplete_adoption(
    *,
    home: Path,
    repo: Path,
    repository: str,
    ref: str,
    harness: str,
    resume_fast_forward: bool = False,
) -> frozenset[Path]:
    target = state_path(home) / "install.json"
    if not target.exists() and not target.is_symlink():
        return frozenset()
    if target.is_symlink() or not target.is_file():
        raise SystemExit(f"incomplete installation state must be a regular file: {target}")
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"incomplete installation state is unreadable: {target}: {exc}") from exc
    expected_keys = {
        "product",
        "status",
        "repository",
        "ref",
        "revision",
        "harness",
        "paths",
    }
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise SystemExit(f"incomplete installation state has an unsupported shape: {target}")
    expected_paths = {
        "home": str(home),
        "repo": str(repo),
        "venv": str(venv_path(home)),
        "python": str(venv_python(venv_path(home))),
        "launchers": [str(path) for path in launcher_paths(home)],
    }
    expected = {
        "product": PRODUCT_NAME,
        "status": "installing",
        "repository": repository,
        "ref": ref,
        "revision": installed_revision(repo),
        "harness": harness,
        "paths": expected_paths,
    }
    mismatched = sorted(key for key in expected if payload[key] != expected[key])
    if mismatched:
        if mismatched == ["revision"] and resume_fast_forward:
            previous_revision = payload["revision"]
            if not isinstance(previous_revision, str):
                raise SystemExit(
                    "incomplete installation recorded revision must be a string"
                )
            validate_revision_fast_forward(
                repo=repo,
                repository=repository,
                ref=ref,
                previous_revision=previous_revision,
                current_revision=expected["revision"],
            )
            print(
                "validated incomplete installation fast-forward: "
                f"{previous_revision[:12]} -> {expected['revision'][:12]}"
            )
        else:
            mismatched_fields = ", ".join(mismatched)
            raise SystemExit(
                "refusing to resume installation because install.json does not match "
                "the exact current request; mismatched fields: "
                f"{mismatched_fields}: {target}"
            )

    state_entries = set(state_path(home).iterdir())
    if state_entries != {target}:
        raise SystemExit(
            "refusing to resume installation with unexpected state entries: "
            + ", ".join(str(path) for path in sorted(state_entries))
        )
    expected_launchers = set(launcher_paths(home))
    launcher_root = bin_path(home)
    if launcher_root.is_symlink() or not launcher_root.is_dir():
        raise SystemExit(f"managed launcher root is not an ordinary directory: {launcher_root}")
    launcher_entries = set(launcher_root.iterdir())
    if launcher_entries != expected_launchers:
        raise SystemExit(
            "refusing to resume installation with unexpected launcher entries: "
            + ", ".join(str(path) for path in sorted(launcher_entries))
        )
    expected_content = expected_launcher_content(home=home, repo=repo)
    for launcher in expected_launchers:
        if launcher.is_symlink() or not launcher.is_file():
            raise SystemExit(f"managed launcher is not an ordinary file: {launcher}")
        if launcher.read_bytes() != expected_content.encode("utf-8"):
            raise SystemExit(f"managed launcher content changed after failed install: {launcher}")

    managed_venv = venv_path(home)
    if managed_venv.exists() or managed_venv.is_symlink():
        if managed_venv.is_symlink() or not managed_venv.is_dir():
            raise SystemExit(f"managed venv is not an ordinary directory: {managed_venv}")
    print(f"resume exact incomplete installation: {target}")
    return frozenset({venv_path(home), bin_path(home), state_path(home)})


def write_install_state(
    *,
    home: Path,
    repository: str,
    ref: str,
    repo: Path,
    harness: str,
    launchers: tuple[Path, Path],
    status: str,
) -> None:
    target = state_path(home) / "install.json"
    payload = {
        "product": PRODUCT_NAME,
        "status": status,
        "repository": repository,
        "ref": ref,
        "revision": installed_revision(repo),
        "harness": harness,
        "paths": {
            "home": str(home),
            "repo": str(repo),
            "venv": str(venv_path(home)),
            "python": str(venv_python(venv_path(home))),
            "launchers": [str(path) for path in launchers],
        },
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".{target.name}.install-{uuid.uuid4().hex}"
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, target)


def invoke_refresh(
    *,
    home: Path,
    repo: Path,
    harness: str,
    codex_home: Path | None,
    assume_yes: bool,
    migrate_marketplace: bool,
    migrate_from_repo: Path | None,
) -> None:
    if os.name == "nt":
        command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(repo / "scripts" / "upgrade_oh_my_harness.ps1"),
            "-ManagerHome",
            str(home),
            "-Harness",
            harness,
        ]
        if codex_home is not None:
            command.extend(["-CodexHome", str(codex_home)])
        if assume_yes:
            command.append("-Yes")
        if migrate_marketplace:
            command.append("-MigrateMarketplace")
        if migrate_from_repo is not None:
            command.extend(["-MigrateFromRepo", str(migrate_from_repo)])
    else:
        command = [
            str(repo / "scripts" / "upgrade_oh_my_harness.sh"),
            "--home",
            str(home),
            "--harness",
            harness,
            "--bootstrap-python",
            str(bootstrap_python()),
        ]
        if codex_home is not None:
            command.extend(["--codex-home", str(codex_home)])
        if assume_yes:
            command.append("--yes")
        if migrate_marketplace:
            command.append("--migrate-marketplace")
        if migrate_from_repo is not None:
            command.extend(["--migrate-from-repo", str(migrate_from_repo)])
    run(command)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clone and initialize one managed oh-my-harness installation."
    )
    parser.add_argument(
        "--home",
        help="Manager home (default: OH_MY_HARNESS_HOME or ~/.oh-my-harness).",
    )
    parser.add_argument(
        "--repository",
        help="Git repository source. Defaults to this checkout's remote.origin.url.",
    )
    parser.add_argument("--ref", default=DEFAULT_REF, help="Git branch to install.")
    parser.add_argument("--harness", default="codex", help="Initial harness distribution.")
    parser.add_argument("--codex-home", help="Explicit Codex harness home.")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--migrate-marketplace", action="store_true")
    parser.add_argument(
        "--migrate-from-repo",
        help=(
            "Former checkout root used only to migrate its exact managed Codex "
            "AGENTS.md symlink."
        ),
    )
    parser.add_argument(
        "--adopt-current-checkout",
        action="store_true",
        help=(
            "Explicitly initialize manager-owned state after the current checkout "
            "has been moved to <home>/repo; exact interrupted installs auto-resume "
            "from the managed repo even when invoked from another checkout."
        ),
    )
    parser.add_argument(
        "--resume-fast-forward",
        action="store_true",
        help=(
            "Explicitly resume an incomplete installation after its clean managed "
            "checkout fast-forwards to the published requested ref."
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        home = manager_home(args.home).resolve(strict=False)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    repository = args.repository or repository_from_checkout()
    if not repository.strip():
        raise SystemExit("repository source must not be empty")
    if not args.ref.strip():
        raise SystemExit("Git ref must not be empty")
    if not args.harness.strip():
        raise SystemExit("harness must not be empty")
    migrate_from_repo: Path | None = None
    if args.migrate_from_repo:
        migrate_from_repo = expand_path(args.migrate_from_repo)
        if not migrate_from_repo.is_absolute():
            raise SystemExit(
                "--migrate-from-repo must be an absolute path: "
                f"{args.migrate_from_repo!r}"
            )
        migrate_from_repo = migrate_from_repo.resolve(strict=False)

    source_root = SOURCE_ROOT.resolve(strict=True)
    expected_repo = repo_path(home).resolve(strict=False)
    install_state = state_path(home) / "install.json"
    resume_incomplete_install = install_state.exists() or install_state.is_symlink()
    if args.resume_fast_forward and not resume_incomplete_install:
        raise SystemExit(
            "--resume-fast-forward requires an incomplete installation state"
        )
    if args.adopt_current_checkout and source_root != expected_repo:
        raise SystemExit(
            "--adopt-current-checkout requires this checkout to be located at "
            f"{expected_repo}; found {source_root}"
        )
    adopted_repo = (
        expected_repo
        if resume_incomplete_install
        else SOURCE_ROOT if args.adopt_current_checkout else None
    )
    allowed_existing = (
        validate_incomplete_adoption(
            home=home,
            repo=adopted_repo,
            repository=repository,
            ref=args.ref,
            harness=args.harness,
            resume_fast_forward=args.resume_fast_forward,
        )
        if adopted_repo is not None
        else frozenset()
    )
    validate_install_root(
        home,
        adopted_repo=adopted_repo,
        allowed_existing=allowed_existing,
    )
    if adopted_repo is None:
        repo = clone_repository(
            repository,
            ref=args.ref,
            home=home,
            dry_run=args.dry_run,
        )
    else:
        repo = adopted_repo
        action = "resume" if resume_incomplete_install else "adopt"
        print(f"{action} managed checkout: {repo}")
    launchers = write_launchers(home=home, repo=repo, dry_run=args.dry_run)
    if args.dry_run:
        print("dry-run only; no installation state written")
        return

    write_install_state(
        home=home,
        repository=repository,
        ref=args.ref,
        repo=repo,
        harness=args.harness,
        launchers=launchers,
        status="installing",
    )
    invoke_refresh(
        home=home,
        repo=repo,
        harness=args.harness,
        codex_home=(Path(args.codex_home).expanduser() if args.codex_home else None),
        assume_yes=args.yes,
        migrate_marketplace=args.migrate_marketplace,
        migrate_from_repo=migrate_from_repo,
    )
    write_install_state(
        home=home,
        repository=repository,
        ref=args.ref,
        repo=repo,
        harness=args.harness,
        launchers=launchers,
        status="ready",
    )
    print(f"installation complete: {home}")
    print(
        f"add {bin_path(home)} to PATH, then run "
        f"`{launcher_help_invocation(os.name)}`"
    )


def cli() -> int:
    try:
        main()
    except SystemExit as exc:
        if exc.code is None:
            return 0
        if isinstance(exc.code, int):
            return exc.code
        write_stderr(f"error: {exc.code}")
        return 1
    except subprocess.CalledProcessError as exc:
        command = (
            command_text([str(part) for part in exc.cmd])
            if isinstance(exc.cmd, (list, tuple))
            else str(exc.cmd)
        )
        write_stderr(
            f"error: command failed with exit code {exc.returncode}: {command}"
        )
        return exc.returncode if exc.returncode > 0 else 1
    except OSError as exc:
        write_stderr(f"error: installation filesystem or process failure: {exc}")
        return 1
    except Exception as exc:
        write_stderr(
            f"error: unexpected installer failure ({type(exc).__name__}): {exc}"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())

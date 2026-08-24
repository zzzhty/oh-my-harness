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
from dataclasses import dataclass
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
_REPARSE_POINT_FLAG = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)


@dataclass(frozen=True)
class ValidatedRecovery:
    allowed_existing: frozenset[Path]
    revision: str


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


def resolve_owned_leaf(path: Path) -> Path:
    """Normalize the requested manager path without erasing link identity."""

    return Path(os.path.abspath(path))


def path_metadata(path: Path, *, label: str) -> os.stat_result | None:
    try:
        return path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise SystemExit(f"{label} cannot be inspected: {path}: {exc}") from exc


def metadata_is_reparse_point(metadata: os.stat_result) -> bool:
    return bool(
        _REPARSE_POINT_FLAG
        and getattr(metadata, "st_file_attributes", 0) & _REPARSE_POINT_FLAG
    )


def is_ordinary_directory(path: Path, *, label: str = "path") -> bool:
    metadata = path_metadata(path, label=label)
    return bool(
        metadata is not None
        and stat.S_ISDIR(metadata.st_mode)
        and not metadata_is_reparse_point(metadata)
    )


def is_ordinary_file(path: Path, *, label: str = "path") -> bool:
    metadata = path_metadata(path, label=label)
    return bool(
        metadata is not None
        and stat.S_ISREG(metadata.st_mode)
        and not metadata_is_reparse_point(metadata)
    )


def path_exists_without_following(path: Path, *, label: str = "path") -> bool:
    return path_metadata(path, label=label) is not None


def require_ordinary_directory(path: Path, *, label: str) -> None:
    if not is_ordinary_directory(path, label=label):
        raise SystemExit(f"{label} must be an ordinary directory: {path}")


def validate_manager_home(home: Path) -> None:
    if not path_exists_without_following(home, label="manager home"):
        return
    require_ordinary_directory(home, label="manager home")


def validate_install_root(
    home: Path,
    *,
    adopted_repo: Path | None = None,
    allowed_existing: frozenset[Path] = frozenset(),
) -> None:
    validate_manager_home(home)
    managed_paths = (repo_path(home), venv_path(home), bin_path(home), state_path(home), home / "bootstrap")
    occupied = []
    for path in managed_paths:
        if not path_exists_without_following(path, label="manager-owned path"):
            continue
        if adopted_repo is not None and path == repo_path(home):
            require_ordinary_directory(path, label="managed repository root")
            try:
                same_repo = path.resolve(strict=True) == adopted_repo.resolve(strict=True)
            except OSError as exc:
                raise SystemExit(
                    f"managed repository root cannot be resolved: {path}: {exc}"
                ) from exc
            if same_repo:
                continue
        if path in allowed_existing:
            require_ordinary_directory(path, label="manager-owned recovery path")
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
    require_ordinary_directory(home, label="manager home")
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
    return "omh --help"


def _bootstrap_script_path(home: Path) -> Path:
    return home / "bootstrap" / "omh_bootstrap.py"


def write_bootstrap(*, home: Path, repo: Path, dry_run: bool) -> Path:
    source = repo / "scripts" / "omh_bootstrap.py"
    target = _bootstrap_script_path(home)
    print(f"{'would write' if dry_run else 'write'} bootstrap: {target}")
    if dry_run:
        return target
    if not source.is_file() or source.is_symlink():
        raise SystemExit(f"manager bootstrap source must be an ordinary file: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    require_ordinary_directory(target.parent, label="manager bootstrap root")
    temporary = target.parent / f".{target.name}.install-{uuid.uuid4().hex}"
    temporary.write_bytes(source.read_bytes())
    os.replace(temporary, target)
    return target


def posix_launcher(*, home: Path, repo: Path) -> str:
    bootstrap = _bootstrap_script_path(home)
    return (
        "#!/usr/bin/env sh\n"
        "set -eu\n"
        "if [ -n \"${OH_MY_HARNESS_BOOTSTRAP_PYTHON:-}\" ]; then\n"
        "    bootstrap_python=$OH_MY_HARNESS_BOOTSTRAP_PYTHON\n"
        "elif command -v python3 >/dev/null 2>&1; then\n"
        "    bootstrap_python=$(command -v python3)\n"
        "elif command -v python >/dev/null 2>&1; then\n"
        "    bootstrap_python=$(command -v python)\n"
        "else\n"
        "    echo \"error: Bootstrap Python not found. Set OH_MY_HARNESS_BOOTSTRAP_PYTHON or install python3.\" >&2\n"
        "    exit 1\n"
        "fi\n"
        f"exec \"$bootstrap_python\" {shlex.quote(str(bootstrap))} --home {shlex.quote(str(home))} \"$@\"\n"
    )


def windows_launcher(*, home: Path, repo: Path) -> str:
    bootstrap = _bootstrap_script_path(home)
    return (
        "@echo off\r\n"
        "setlocal\r\n"
        "if defined OH_MY_HARNESS_BOOTSTRAP_PYTHON (\r\n"
        "  set \"OHM_PY=%OH_MY_HARNESS_BOOTSTRAP_PYTHON%\"\r\n"
        "  goto :run\r\n"
        ")\r\n"
        "where python >nul 2>nul && (\r\n"
        "  set \"OHM_PY=python\"\r\n"
        "  goto :run\r\n"
        ")\r\n"
        "where py >nul 2>nul && (\r\n"
        "  set \"OHM_PY=py\"\r\n"
        "  goto :run\r\n"
        ")\r\n"
        "echo error: Bootstrap Python not found. Set OH_MY_HARNESS_BOOTSTRAP_PYTHON or install Python. 1>&2\r\n"
        "exit /b 1\r\n"
        ":run\r\n"
        f"\"%OHM_PY%\" \"{bootstrap}\" --home \"{home}\" %*\r\n"
        "exit /b %ERRORLEVEL%\r\n"
    )


def expected_launcher_content(*, home: Path, repo: Path) -> str:
    if os.name == "nt":
        return windows_launcher(home=home, repo=repo)
    return posix_launcher(home=home, repo=repo)


def write_launchers(*, home: Path, repo: Path, dry_run: bool) -> tuple[Path, Path]:
    write_bootstrap(home=home, repo=repo, dry_run=dry_run)
    paths = launcher_paths(home)
    content = expected_launcher_content(home=home, repo=repo)
    for path in paths:
        print(f"{'would write' if dry_run else 'write'} launcher: {path}")
        if dry_run:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        require_ordinary_directory(path.parent, label="managed launcher root")
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


def validate_checkout_clean_and_remote(
    *,
    repo: Path,
    repository: str,
    context: str,
) -> None:
    status = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    if status.returncode != 0:
        raise SystemExit(f"managed checkout status is unavailable for {context}")
    if status.stdout.strip():
        raise SystemExit(
            f"managed checkout has uncommitted changes; refusing {context}"
        )

    actual_repository = repository_from_checkout(repo)
    if actual_repository != repository:
        raise SystemExit(
            "managed checkout remote does not match the recorded installation repository"
        )


def assert_checkout_snapshot(
    *,
    repo: Path,
    repository: str,
    revision: str,
    phase: str,
) -> None:
    current_revision = installed_revision(repo)
    if current_revision != revision:
        raise SystemExit(
            f"managed checkout revision changed {phase}; "
            f"expected {revision}, found {current_revision}"
        )
    validate_checkout_clean_and_remote(
        repo=repo,
        repository=repository,
        context=f"installation recovery {phase}",
    )


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

    validate_checkout_clean_and_remote(
        repo=repo,
        repository=repository,
        context="fast-forward resume",
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
) -> ValidatedRecovery | None:
    state_root = state_path(home)
    require_ordinary_directory(state_root, label="managed state root")
    require_ordinary_directory(repo, label="managed repository root")
    target = state_root / "install.json"
    if not path_exists_without_following(target, label="incomplete installation state"):
        return None
    if not is_ordinary_file(target, label="incomplete installation state"):
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
    current_revision = installed_revision(repo)
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
        "revision": current_revision,
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
                current_revision=current_revision,
            )
            print(
                "validated incomplete installation fast-forward: "
                f"{previous_revision[:12]} -> {current_revision[:12]}"
            )
        else:
            mismatched_fields = ", ".join(mismatched)
            raise SystemExit(
                "refusing to resume installation because install.json does not match "
                "the exact current request; mismatched fields: "
                f"{mismatched_fields}: {target}"
            )
    else:
        validate_checkout_clean_and_remote(
            repo=repo,
            repository=repository,
            context="incomplete installation recovery",
        )

    state_entries = set(state_root.iterdir())
    allowed_state_names = {
        "install.json",
        "manager.json",
        "desired.json",
        "harnesses",
        "operations",
        "manager.lock",
    }
    unexpected_state = sorted(
        path for path in state_entries if path.name not in allowed_state_names
    )
    if unexpected_state:
        raise SystemExit(
            "refusing to resume installation with unexpected state entries: "
            + ", ".join(str(path) for path in unexpected_state)
        )
    expected_launchers = set(launcher_paths(home))
    launcher_root = bin_path(home)
    require_ordinary_directory(launcher_root, label="managed launcher root")
    launcher_entries = set(launcher_root.iterdir())
    if launcher_entries != expected_launchers:
        raise SystemExit(
            "refusing to resume installation with unexpected launcher entries: "
            + ", ".join(str(path) for path in sorted(launcher_entries))
        )
    expected_content = expected_launcher_content(home=home, repo=repo)
    for launcher in expected_launchers:
        if not is_ordinary_file(launcher, label="managed launcher"):
            raise SystemExit(f"managed launcher is not an ordinary file: {launcher}")
        if launcher.read_bytes() != expected_content.encode("utf-8"):
            raise SystemExit(f"managed launcher content changed after failed install: {launcher}")

    managed_venv = venv_path(home)
    if path_exists_without_following(managed_venv, label="managed venv"):
        require_ordinary_directory(managed_venv, label="managed venv")
    print(f"resume exact incomplete installation: {target}")
    return ValidatedRecovery(
        allowed_existing=frozenset(
            {venv_path(home), bin_path(home), state_path(home), home / "bootstrap"}
        ),
        revision=current_revision,
    )


def write_install_state(
    *,
    home: Path,
    repository: str,
    ref: str,
    repo: Path,
    harness: str,
    launchers: tuple[Path, Path],
    status: str,
    revision: str | None = None,
) -> None:
    state_root = state_path(home)
    state_root.mkdir(parents=True, exist_ok=True)
    require_ordinary_directory(state_root, label="managed state root")
    target = state_root / "install.json"
    payload = {
        "product": PRODUCT_NAME,
        "status": status,
        "repository": repository,
        "ref": ref,
        "revision": revision if revision is not None else installed_revision(repo),
        "harness": harness,
        "paths": {
            "home": str(home),
            "repo": str(repo),
            "venv": str(venv_path(home)),
            "python": str(venv_python(venv_path(home))),
            "launchers": [str(path) for path in launchers],
        },
    }
    temporary = state_root / f".{target.name}.install-{uuid.uuid4().hex}"
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
    command = [
        str(bootstrap_python()),
        str(_bootstrap_script_path(home)),
        "--home",
        str(home),
        "install",
        harness,
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
        home = resolve_owned_leaf(manager_home(args.home))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    validate_manager_home(home)
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
        migrate_from_repo = Path(os.path.abspath(migrate_from_repo))

    source_root = SOURCE_ROOT.resolve(strict=True)
    expected_repo = repo_path(home)
    state_root = state_path(home)
    if path_exists_without_following(state_root, label="managed state root"):
        require_ordinary_directory(state_root, label="managed state root")
    install_state = state_root / "install.json"
    resume_incomplete_install = path_exists_without_following(
        install_state,
        label="incomplete installation state",
    )
    if args.resume_fast_forward and not resume_incomplete_install:
        raise SystemExit(
            "--resume-fast-forward requires an incomplete installation state"
        )
    if args.adopt_current_checkout:
        require_ordinary_directory(expected_repo, label="managed repository root")
        try:
            resolved_expected_repo = expected_repo.resolve(strict=True)
        except OSError as exc:
            raise SystemExit(
                f"managed repository root cannot be resolved: {expected_repo}: {exc}"
            ) from exc
        if source_root != resolved_expected_repo:
            raise SystemExit(
                "--adopt-current-checkout requires this checkout to be located at "
                f"{expected_repo}; found {source_root}"
            )
    adopted_repo = (
        expected_repo
        if resume_incomplete_install
        else SOURCE_ROOT if args.adopt_current_checkout else None
    )
    recovery = (
        validate_incomplete_adoption(
            home=home,
            repo=adopted_repo,
            repository=repository,
            ref=args.ref,
            harness=args.harness,
            resume_fast_forward=args.resume_fast_forward,
        )
        if adopted_repo is not None and resume_incomplete_install
        else None
    )
    if resume_incomplete_install and recovery is None:
        raise SystemExit("incomplete installation state disappeared during validation")
    allowed_existing = recovery.allowed_existing if recovery is not None else frozenset()
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

    validated_revision = recovery.revision if recovery is not None else None
    write_install_state(
        home=home,
        repository=repository,
        ref=args.ref,
        repo=repo,
        harness=args.harness,
        launchers=launchers,
        status="installing",
        revision=validated_revision,
    )
    if validated_revision is not None:
        assert_checkout_snapshot(
            repo=repo,
            repository=repository,
            revision=validated_revision,
            phase="before refresh",
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
    if validated_revision is not None:
        assert_checkout_snapshot(
            repo=repo,
            repository=repository,
            revision=validated_revision,
            phase="after refresh",
        )
    write_install_state(
        home=home,
        repository=repository,
        ref=args.ref,
        repo=repo,
        harness=args.harness,
        launchers=launchers,
        status="ready",
        revision=validated_revision,
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

#!/usr/bin/env python3
"""Unified lifecycle manager for oh-my-harness."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import uuid
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable, Sequence

from harness_registry import (
    INSTRUCTIONS_MIGRATION_ORIENTATION,
    INSTRUCTIONS_MIGRATION_ID,
    INSTRUCTIONS_MIGRATION_STAGES,
)
from manager_paths import (
    PRODUCT_NAME,
    bin_path,
    lexical_absolute,
    manager_home,
    repo_path,
    state_path,
    venv_path,
    venv_python,
)
from manager_state import (
    ManagerLock,
    begin_operation,
    desired_harnesses,
    finish_operation,
    load_current_operation,
    load_or_initialize,
    remove_harness_receipt,
    update_operation,
    write_desired,
    write_harness_receipt,
    write_manager,
)
from plugin_package_identity import require_repository_identity

REPO_ROOT = Path(__file__).resolve().parents[1]
KNOWN_COMMANDS = {
    "install",
    "refresh",
    "remove",
    "update",
    "manager",
    "status",
    "check",
    "doctor",
    "recover",
    "version",
    "_resume-update",
    "_resume-rollback",
}
SEMVER_TAG = re.compile(r"^v([0-9]+)\.([0-9]+)\.([0-9]+)$")
INSTRUCTION_REGISTRY_PATH = ".agents/harnesses/registry.json"
INSTRUCTION_MIGRATION_STAGE_ORDER = {
    stage: index for index, stage in enumerate(INSTRUCTIONS_MIGRATION_STAGES)
}
GIT_REVISION = re.compile(r"^[0-9a-f]{40}$")


def _base_python() -> Path:
    return Path(getattr(sys, "_base_executable", None) or sys.executable).resolve(strict=True)


def _run(
    command: Sequence[str | Path],
    *,
    cwd: Path | None = None,
    capture: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    rendered = [str(item) for item in command]
    print("+ " + subprocess.list2cmdline(rendered), flush=True)
    return subprocess.run(
        rendered,
        cwd=cwd,
        text=True,
        capture_output=capture,
        check=check,
    )


def _git(repo: Path, *args: str, capture: bool = True, check: bool = True) -> subprocess.CompletedProcess[str]:
    return _run(["git", "-C", repo, *args], capture=capture, check=check)


def _git_text(repo: Path, *args: str) -> str:
    result = _git(repo, *args)
    return result.stdout.strip()


def _git_blob(repo: Path, revision: str, relative_path: str) -> bytes:
    object_name = f"{revision}:{relative_path}"
    try:
        tree = subprocess.run(
            ["git", "-C", str(repo), "ls-tree", revision, "--", relative_path],
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise SystemExit(f"cannot inspect update revision {revision[:12]}: {exc}") from exc
    if tree.returncode != 0:
        detail = tree.stderr.decode("utf-8", errors="replace").strip()
        raise SystemExit(
            f"cannot inspect update revision {revision[:12]} at {relative_path}: {detail}"
        )
    try:
        mode = tree.stdout.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise SystemExit(
            f"update revision {revision[:12]} has a non-UTF-8 tree entry at {relative_path}"
        ) from exc
    if not mode or mode.split(maxsplit=1)[0] not in {"100644", "100755"}:
        raise SystemExit(
            f"update revision {revision[:12]} has no regular file at {relative_path}"
        )
    try:
        blob = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "blob", object_name],
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise SystemExit(
            f"cannot read update revision {revision[:12]} at {relative_path}: {exc}"
        ) from exc
    if blob.returncode != 0:
        detail = blob.stderr.decode("utf-8", errors="replace").strip()
        raise SystemExit(
            f"cannot read update revision {revision[:12]} at {relative_path}: {detail}"
        )
    return blob.stdout


def _instruction_relative_path(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"{label} must be a non-empty relative path")
    raw = value.strip()
    posix = PurePosixPath(raw)
    windows = PureWindowsPath(raw)
    parts = raw.split("/")
    if (
        "\\" in raw
        or posix.is_absolute()
        or windows.is_absolute()
        or bool(windows.drive)
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise SystemExit(f"{label} must be a normalized repository-relative path")
    return raw


def _instruction_source_at_revision(repo: Path, revision: str) -> dict[str, object]:
    try:
        registry_text = _git_blob(
            repo,
            revision,
            INSTRUCTION_REGISTRY_PATH,
        ).decode("utf-8", errors="strict")
        payload = json.loads(registry_text)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SystemExit(
            f"update revision {revision[:12]} has an invalid harness registry: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise SystemExit(
            f"update revision {revision[:12]} harness registry must be an object"
        )
    sources = payload.get("sources")
    if not isinstance(sources, dict):
        raise SystemExit(
            f"update revision {revision[:12]} harness registry has no sources object"
        )
    instructions = sources.get("instructions")
    migration_record: dict[str, object] | None = None
    if isinstance(instructions, str):
        current = _instruction_relative_path(
            instructions,
            label="legacy registry instructions source",
        )
    elif isinstance(instructions, dict):
        if set(instructions) != {"current", "migration"}:
            raise SystemExit(
                f"update revision {revision[:12]} has unsupported instruction source fields"
            )
        current = _instruction_relative_path(
            instructions.get("current"),
            label="registry instructions current source",
        )
        migration = instructions.get("migration")
        if not isinstance(migration, dict):
            raise SystemExit("registry instruction migration must be an object")
        allowed = {"id", "stage", "peer", "requiredPredecessorRevision"}
        if set(migration) - allowed or not {"id", "stage", "peer"} <= set(migration):
            raise SystemExit("registry instruction migration fields are invalid")
        migration_id = migration.get("id")
        stage = migration.get("stage")
        if migration_id != INSTRUCTIONS_MIGRATION_ID:
            raise SystemExit(
                f"registry instruction migration id must be {INSTRUCTIONS_MIGRATION_ID!r}"
            )
        if stage not in INSTRUCTION_MIGRATION_STAGE_ORDER:
            raise SystemExit(f"registry instruction migration stage is invalid: {stage!r}")
        peer = _instruction_relative_path(
            migration.get("peer"),
            label="registry instruction migration peer",
        )
        if peer == current:
            raise SystemExit("registry instruction current source and peer must differ")
        expected_current, expected_peer = INSTRUCTIONS_MIGRATION_ORIENTATION[stage]
        if current != expected_current or peer != expected_peer:
            raise SystemExit(
                "registry instruction paths do not match the "
                f"{stage} migration orientation: current={expected_current!r}, "
                f"peer={expected_peer!r}"
            )
        predecessor = migration.get("requiredPredecessorRevision")
        if predecessor is not None and (
            not isinstance(predecessor, str) or not GIT_REVISION.fullmatch(predecessor)
        ):
            raise SystemExit(
                "registry instruction required predecessor must be a lowercase 40-character Git SHA"
            )
        if stage == "bridge-ready" and predecessor is not None:
            raise SystemExit("bridge-ready instruction migration cannot require a predecessor")
        if stage != "bridge-ready" and predecessor is None:
            raise SystemExit(f"{stage} instruction migration requires a predecessor")
        peer_blob = _git_blob(repo, revision, peer)
        current_blob = _git_blob(repo, revision, current)
        if stage in {"bridge-ready", "source-switched"} and current_blob != peer_blob:
            raise SystemExit(
                f"instruction sources are not byte-identical during {stage}"
            )
        migration_record = {
            "id": migration_id,
            "stage": stage,
            "peer": peer,
            "peerSha256": hashlib.sha256(peer_blob).hexdigest(),
        }
        if predecessor is not None:
            migration_record["requiredPredecessorRevision"] = predecessor
    else:
        raise SystemExit(
            f"update revision {revision[:12]} has an invalid instructions source"
        )
    source_blob = _git_blob(repo, revision, current)
    record: dict[str, object] = {
        "path": current,
        "sha256": hashlib.sha256(source_blob).hexdigest(),
    }
    if migration_record is not None:
        record["migration"] = migration_record
    return record


def _validate_instruction_transition(
    repo: Path,
    *,
    before_revision: str,
    target_revision: str,
    before_source: dict[str, object],
    target_source: dict[str, object],
) -> None:
    before_migration = before_source.get("migration")
    target_migration = target_source.get("migration")
    if isinstance(target_migration, dict):
        predecessor = target_migration.get("requiredPredecessorRevision")
        if isinstance(predecessor, str):
            predecessor_source = _instruction_source_at_revision(repo, predecessor)
            predecessor_migration = predecessor_source.get("migration")
            if not isinstance(predecessor_migration, dict):
                raise SystemExit(
                    "instruction source migration predecessor has no migration contract"
                )
            if predecessor_migration.get("id") != target_migration.get("id"):
                raise SystemExit(
                    "instruction source migration predecessor has a different migration id"
                )
            target_stage = target_migration.get("stage")
            predecessor_stage = predecessor_migration.get("stage")
            assert isinstance(target_stage, str)
            expected_index = INSTRUCTION_MIGRATION_STAGE_ORDER[target_stage] - 1
            if expected_index < 0 or predecessor_stage != INSTRUCTIONS_MIGRATION_STAGES[expected_index]:
                raise SystemExit(
                    "instruction source migration predecessor is not the exact previous stage"
                )
            target_ancestry = _git(
                repo,
                "merge-base",
                "--is-ancestor",
                predecessor,
                target_revision,
                check=False,
            )
            if target_ancestry.returncode == 1:
                raise SystemExit(
                    "instruction source migration predecessor is not an ancestor "
                    "of the target revision"
                )
            if target_ancestry.returncode != 0:
                detail = (target_ancestry.stderr or target_ancestry.stdout).strip()
                raise SystemExit(
                    "cannot validate instruction source migration target ancestry: "
                    f"git exited {target_ancestry.returncode}: {detail or 'no detail'}"
                )
            current_ancestry = _git(
                repo,
                "merge-base",
                "--is-ancestor",
                predecessor,
                before_revision,
                check=False,
            )
            if current_ancestry.returncode == 1:
                raise SystemExit(
                    "instruction source migration requires the bridge checkpoint first; "
                    f"run `omh update --to {predecessor}`"
                )
            if current_ancestry.returncode != 0:
                detail = (current_ancestry.stderr or current_ancestry.stdout).strip()
                raise SystemExit(
                    "cannot validate instruction source migration current ancestry: "
                    f"git exited {current_ancestry.returncode}: {detail or 'no detail'}"
                )
    if isinstance(before_migration, dict) and isinstance(target_migration, dict):
        if before_migration.get("id") != target_migration.get("id"):
            raise SystemExit("instruction source migration id changed across update")
        before_stage = before_migration.get("stage")
        target_stage = target_migration.get("stage")
        assert isinstance(before_stage, str) and isinstance(target_stage, str)
        if abs(
            INSTRUCTION_MIGRATION_STAGE_ORDER[target_stage]
            - INSTRUCTION_MIGRATION_STAGE_ORDER[before_stage]
        ) > 1:
            raise SystemExit(
                "instruction source migration checkpoints must be traversed in order"
            )
    elif isinstance(before_migration, dict):
        before_stage = before_migration.get("stage")
        if (
            isinstance(before_stage, str)
            and INSTRUCTION_MIGRATION_STAGE_ORDER[before_stage]
            >= INSTRUCTION_MIGRATION_STAGE_ORDER["source-switched"]
        ):
            raise SystemExit(
                "cannot leave an active instruction source migration after source cutover"
            )


def _instruction_transition(
    repo: Path,
    before_revision: str,
    target_revision: str,
) -> tuple[dict[str, object], dict[str, object]]:
    before_source = _instruction_source_at_revision(repo, before_revision)
    target_source = _instruction_source_at_revision(repo, target_revision)
    _validate_instruction_transition(
        repo,
        before_revision=before_revision,
        target_revision=target_revision,
        before_source=before_source,
        target_source=target_source,
    )
    return before_source, target_source


def _journal_instruction_transition(
    home: Path,
    operation: dict,
) -> dict:
    before = operation.get("before")
    target = operation.get("target")
    if not isinstance(before, dict) or not isinstance(target, dict):
        raise SystemExit("update operation journal has invalid transition state")
    before_revision = before.get("revision")
    target_revision = target.get("revision")
    if not isinstance(before_revision, str) or not isinstance(target_revision, str):
        raise SystemExit("update operation journal has invalid transition revisions")
    before_source, target_source = _instruction_transition(
        REPO_ROOT,
        before_revision,
        target_revision,
    )
    for label, side, source in (
        ("before", before, before_source),
        ("target", target, target_source),
    ):
        recorded = side.get("instructionsSource")
        if recorded is not None and recorded != source:
            raise SystemExit(
                f"journaled {label} instruction source changed after update preflight"
            )
        side["instructionsSource"] = source
    return update_operation(
        home,
        phase=str(operation.get("phase", "prepared")),
        before=before,
        target=target,
    )


def _repository(repo: Path) -> str:
    value = _git_text(repo, "config", "--get", "remote.origin.url")
    if not value:
        raise SystemExit(f"managed checkout has no remote.origin.url: {repo}")
    return value


def _revision(repo: Path) -> str:
    value = _git_text(repo, "rev-parse", "--verify", "HEAD")
    if not value:
        raise SystemExit(f"managed checkout HEAD is unavailable: {repo}")
    return value


def _worktree_clean(repo: Path) -> bool:
    return not _git_text(repo, "status", "--porcelain")


def _distribution(repo: Path) -> tuple[str, str]:
    payload = require_repository_identity(repo)
    release = payload.get("releaseVersion")
    bundle = payload.get("bundleIdentity")
    if not isinstance(release, str) or not release:
        raise SystemExit("distribution identity has no releaseVersion")
    if not isinstance(bundle, str) or not bundle:
        raise SystemExit("distribution identity has no bundleIdentity")
    return release, bundle


def _load_registry():
    from harness_registry import load_harness_registry

    return load_harness_registry(repo_root=REPO_ROOT)


def _resolve_plan(harness: str, *, codex_home: Path | None = None):
    from harness_registry import resolve_harness_plan

    environment = dict(os.environ)
    if codex_home is not None:
        environment["CODEX_HOME"] = str(codex_home)
    return resolve_harness_plan(
        _load_registry(),
        harness,
        repo_root=REPO_ROOT,
        environ=environment,
    )


def _state_context(
    home: Path,
    *,
    persist: bool,
    allow_manager_drift: bool = False,
    allow_degraded: bool = False,
    allow_active_operation: bool = False,
) -> tuple[dict, dict]:
    repo = repo_path(home)
    if repo.resolve(strict=False) != REPO_ROOT.resolve(strict=False):
        raise SystemExit(
            f"omh must run from the managed checkout {repo}; found {REPO_ROOT}"
        )
    repository = _repository(repo)
    revision = _revision(repo)
    release, bundle = _distribution(repo)
    manager, desired = load_or_initialize(
        home,
        repository=repository,
        revision=revision,
        release_version=release,
        bundle_identity=bundle,
        persist=persist,
    )
    active_operation = load_current_operation(home)
    if active_operation is not None and not allow_active_operation:
        raise SystemExit(
            "an interrupted manager operation is active; run `omh status` and "
            "`omh recover` before starting another lifecycle mutation: "
            f"{active_operation.get('command')} / {active_operation.get('phase')} "
            f"({active_operation.get('operationId')})"
        )
    if manager.get("status") == "degraded" and not allow_degraded:
        raise SystemExit(
            "manager lifecycle is degraded; run `omh status` and `omh recover` before "
            "starting another mutation"
        )
    if not allow_manager_drift:
        expected = {
            "repository": repository,
            "revision": revision,
            "releaseVersion": release,
            "bundleIdentity": bundle,
        }
        mismatched = [
            field for field, value in expected.items() if manager.get(field) != value
        ]
        if mismatched:
            raise SystemExit(
                "managed checkout differs from manager lifecycle state; "
                "do not move the checkout outside `omh update`: mismatched fields: "
                + ", ".join(mismatched)
                + "; run `omh manager repair` to restore the recorded revision or "
                "`omh recover` if an update operation is active"
            )
    return manager, desired


def _validate_targets(targets: Iterable[str]) -> tuple[str, ...]:
    registry = _load_registry()
    selected = tuple(dict.fromkeys(targets))
    unknown = sorted(set(selected) - set(registry.choices))
    if unknown:
        raise SystemExit(
            "unknown harness target(s): "
            + ", ".join(unknown)
            + "; expected one of: "
            + ", ".join(registry.choices)
        )
    return selected


def _target_set(
    args: argparse.Namespace,
    *,
    desired: tuple[str, ...],
    mode: str,
) -> tuple[str, ...]:
    registry = _load_registry()
    explicit = list(getattr(args, "targets", []) or [])
    legacy = getattr(args, "harness", None)
    if legacy:
        explicit.append(legacy)
    if getattr(args, "all", False):
        if explicit:
            raise SystemExit("do not combine explicit harness targets with --all")
        if mode == "install":
            return registry.choices
        return desired
    if explicit:
        return _validate_targets(explicit)
    if mode == "install":
        return (registry.default_harness,)
    if mode == "remove":
        return ()
    return desired


def _common_refresh_args(args: argparse.Namespace, *, home: Path, harness: str) -> list[str]:
    command = [
        str(sys.executable),
        str(REPO_ROOT / "scripts" / "refresh_harness.py"),
        "--home",
        str(home),
        "--harness",
        harness,
        "--venv",
        str(venv_path(home)),
        "--python",
        str(sys.executable),
        "--skip-bootstrap",
    ]
    if getattr(args, "codex_home", None):
        command.extend(["--codex-home", str(Path(args.codex_home).expanduser())])
    if getattr(args, "codex", None):
        command.extend(["--codex", args.codex])
    if getattr(args, "yes", False):
        command.append("--yes")
    if getattr(args, "dry_run", False):
        command.append("--dry-run")
    if getattr(args, "repair", False):
        command.append("--repair")
    if getattr(args, "migrate_marketplace", False):
        command.append("--migrate-marketplace")
    if getattr(args, "migrate_from_repo", None):
        command.extend(["--migrate-from-repo", args.migrate_from_repo])
    if getattr(args, "operation_id", None):
        command.extend(["--operation-id", args.operation_id])
    return command


def _check_args(args: argparse.Namespace, *, home: Path, harness: str, strict: bool = False) -> list[str]:
    command = [
        str(sys.executable),
        str(REPO_ROOT / "scripts" / "check_harness.py"),
        "--home",
        str(home),
        "--harness",
        harness,
        "--venv",
        str(venv_path(home)),
        "--python",
        str(sys.executable),
    ]
    if getattr(args, "codex_home", None):
        command.extend(["--codex-home", str(Path(args.codex_home).expanduser())])
    if getattr(args, "codex", None):
        command.extend(["--codex", args.codex])
    if strict:
        command.append("--strict-warnings")
    return command


def _refresh_one(
    args: argparse.Namespace,
    *,
    home: Path,
    harness: str,
    check_after: bool,
) -> None:
    _run(_common_refresh_args(args, home=home, harness=harness))
    if not getattr(args, "dry_run", False) and check_after:
        _run(_check_args(args, home=home, harness=harness))


def _write_harness_state(home: Path, harness: str) -> None:
    release, bundle = _distribution(REPO_ROOT)
    plan = _resolve_plan(harness)
    write_harness_receipt(
        home,
        harness=harness,
        manager_revision=_revision(REPO_ROOT),
        release_version=release,
        bundle_identity=bundle,
        root=str(plan.root),
    )


def command_install(args: argparse.Namespace) -> int:
    home = lexical_absolute(manager_home(args.home))
    with ManagerLock(home):
        manager, desired_state = _state_context(home, persist=not args.dry_run)
        desired = list(desired_harnesses(desired_state))
        targets = _target_set(args, desired=tuple(desired), mode="install")
        for harness in targets:
            _refresh_one(
                args,
                home=home,
                harness=harness,
                check_after=not args.no_check,
            )
            if args.dry_run:
                continue
            if harness not in desired:
                desired.append(harness)
            write_desired(home, desired)
            _write_harness_state(home, harness)
        if not targets:
            print("no harness distributions selected")
    return 0


def command_refresh(args: argparse.Namespace) -> int:
    home = lexical_absolute(manager_home(args.home))
    with ManagerLock(home):
        _manager, desired_state = _state_context(home, persist=not args.dry_run)
        targets = _target_set(
            args,
            desired=desired_harnesses(desired_state),
            mode="refresh",
        )
        if not targets:
            print("no installed harness distributions to refresh")
            return 0
        for harness in targets:
            _refresh_one(
                args,
                home=home,
                harness=harness,
                check_after=not args.no_check,
            )
            if not args.dry_run:
                _write_harness_state(home, harness)
    return 0


def _remove_one(args: argparse.Namespace, *, home: Path, harness: str) -> None:
    command = [
        str(sys.executable),
        str(REPO_ROOT / "scripts" / "remove_harness.py"),
        "--harness",
        harness,
        "--home",
        str(home),
        "--python",
        str(sys.executable),
    ]
    if getattr(args, "codex_home", None):
        command.extend(["--codex-home", args.codex_home])
    if getattr(args, "codex", None):
        command.extend(["--codex", args.codex])
    if getattr(args, "dry_run", False):
        command.append("--dry-run")
    if getattr(args, "yes", False):
        command.append("--yes")
    _run(command)


def command_remove(args: argparse.Namespace) -> int:
    home = lexical_absolute(manager_home(args.home))
    with ManagerLock(home):
        _manager, desired_state = _state_context(home, persist=not args.dry_run)
        desired = list(desired_harnesses(desired_state))
        targets = _target_set(args, desired=tuple(desired), mode="remove")
        if not targets:
            raise SystemExit("remove requires an installed harness target or --all")
        not_installed = sorted(set(targets) - set(desired))
        if not_installed:
            raise SystemExit(
                "harness target is not installed according to desired state: "
                + ", ".join(not_installed)
            )
        for harness in targets:
            _remove_one(args, home=home, harness=harness)
            if args.dry_run:
                continue
            desired.remove(harness)
            write_desired(home, desired)
            remove_harness_receipt(home, harness)
    return 0


def command_check(args: argparse.Namespace, *, strict: bool = False) -> int:
    home = lexical_absolute(manager_home(args.home))
    _manager, desired_state = _state_context(
        home,
        persist=False,
        allow_manager_drift=True,
        allow_degraded=True,
        allow_active_operation=True,
    )
    targets = _target_set(
        args,
        desired=desired_harnesses(desired_state),
        mode="check",
    )
    if not targets:
        print("no installed harness distributions to check")
        return 0
    for harness in targets:
        _run(_check_args(args, home=home, harness=harness, strict=strict))
    return 0


def command_status(args: argparse.Namespace) -> int:
    home = lexical_absolute(manager_home(args.home))
    manager, desired = _state_context(
        home,
        persist=False,
        allow_manager_drift=True,
        allow_degraded=True,
        allow_active_operation=True,
    )
    current_op = load_current_operation(home)
    payload = {
        "product": PRODUCT_NAME,
        "home": str(home),
        "manager": manager,
        "desiredHarnesses": list(desired_harnesses(desired)),
        "worktreeClean": _worktree_clean(REPO_ROOT),
        "operation": current_op,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(f"{PRODUCT_NAME} {manager['releaseVersion']}")
    print(f"home: {home}")
    print(f"revision: {manager['revision']}")
    print(f"bundle: {manager['bundleIdentity']}")
    print(f"channel: {manager['channel']}")
    print("desired harnesses: " + (", ".join(payload["desiredHarnesses"]) or "<none>"))
    print(f"worktree: {'clean' if payload['worktreeClean'] else 'dirty'}")
    if current_op:
        print(
            "operation: "
            f"{current_op.get('command')} / {current_op.get('phase')} "
            f"({current_op.get('operationId')})"
        )
    else:
        print("operation: none")
    return 0


def command_version(args: argparse.Namespace) -> int:
    release, bundle = _distribution(REPO_ROOT)
    payload = {
        "product": PRODUCT_NAME,
        "releaseVersion": release,
        "revision": _revision(REPO_ROOT),
        "bundleIdentity": bundle,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{PRODUCT_NAME} {release}")
        print(f"revision: {payload['revision']}")
        print(f"bundle: {bundle}")
    return 0


def _latest_stable_tag(repo: Path) -> str:
    result = _git_text(repo, "tag", "--list", "v*", "--sort=-v:refname")
    for line in result.splitlines():
        tag = line.strip()
        if SEMVER_TAG.fullmatch(tag):
            return tag
    raise SystemExit("no stable vX.Y.Z release tag is available from origin")


def _target_revision(repo: Path, *, channel: str, requested: str | None) -> tuple[str, str]:
    if requested:
        ref = requested
    elif channel == "main":
        ref = "origin/main"
    else:
        ref = _latest_stable_tag(repo)
    result = _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}", check=False)
    if result.returncode != 0 or not result.stdout.strip():
        detail = (result.stderr or result.stdout).strip()
        raise SystemExit(f"update target cannot be resolved: {ref}: {detail}")
    return ref, result.stdout.strip()


def _validate_update_target(repo: Path, target_revision: str) -> tuple[str, str]:
    staging = repo.parent / f".update-validate-{uuid.uuid4().hex}"
    _git(repo, "worktree", "add", "--detach", str(staging), target_revision, capture=False)
    try:
        checker = staging / "scripts" / "check_plugin_generations.py"
        if not checker.is_file():
            raise SystemExit(f"update target has no distribution identity checker: {checker}")
        _run([str(_base_python()), str(checker)], cwd=staging)
        version = (staging / "VERSION").read_text(encoding="utf-8").strip()
        identity = json.loads(
            (staging / ".agents" / "plugins" / "distribution-identity.json").read_text(
                encoding="utf-8"
            )
        )
        if identity.get("releaseVersion") != version:
            raise SystemExit(
                "update target VERSION and distribution identity disagree: "
                f"{version!r} vs {identity.get('releaseVersion')!r}"
            )
        bundle = identity.get("bundleIdentity")
        if not isinstance(bundle, str) or not bundle:
            raise SystemExit("update target distribution identity has no bundleIdentity")
        return version, bundle
    finally:
        _git(repo, "worktree", "remove", "--force", str(staging), capture=False, check=False)


def _bootstrap_tooling(home: Path) -> None:
    _run(
        [
            str(_base_python()),
            str(REPO_ROOT / "scripts" / "bootstrap_tooling_env.py"),
            "--venv",
            str(venv_path(home)),
        ]
    )


def _invoke_internal(repo: Path, home: Path, command: str, *extra: str) -> subprocess.CompletedProcess[str]:
    python = venv_python(venv_path(home))
    cli = repo / "scripts" / "omh.py"
    return _run(
        [
            str(python),
            str(cli),
            "--home",
            str(home),
            command,
            *extra,
        ],
        check=False,
    )


def command_update(args: argparse.Namespace) -> int:
    home = lexical_absolute(manager_home(args.home))
    repo = repo_path(home)
    with ManagerLock(home):
        manager, desired = _state_context(home, persist=not args.check)
        if not _worktree_clean(repo):
            raise SystemExit("managed checkout has uncommitted changes; refusing update")
        recorded_repository = manager["repository"]
        actual_repository = _repository(repo)
        if actual_repository != recorded_repository:
            raise SystemExit(
                "managed checkout remote differs from manager state; "
                f"expected {recorded_repository!r}, found {actual_repository!r}"
            )
        _git(repo, "fetch", "--prune", "--prune-tags", "--tags", "origin", capture=False)
        channel = args.channel or desired["updatePolicy"]["channel"]
        requested_ref, target = _target_revision(
            repo,
            channel=channel,
            requested=args.to,
        )
        old = _revision(repo)
        release, bundle = _validate_update_target(repo, target)
        print("Update plan:")
        print(f"  channel:  {manager['channel']} -> {channel}")
        print(f"  release:  {manager['releaseVersion']} -> {release}")
        print(f"  revision: {old} -> {target}")
        print(f"  bundle:   {manager['bundleIdentity']} -> {bundle}")
        if old == target:
            print("manager checkout is already at the selected update target")
            if args.check:
                return 0
            write_manager(
                home,
                repository=recorded_repository,
                revision=old,
                release_version=release,
                bundle_identity=bundle,
                channel=channel,
                requested_ref=requested_ref,
            )
            write_desired(home, desired_harnesses(desired), channel=channel)
            return 0

        if not args.allow_downgrade:
            ancestor = _git(
                repo,
                "merge-base",
                "--is-ancestor",
                old,
                target,
                check=False,
            )
            if ancestor.returncode != 0:
                raise SystemExit(
                    "update target is not a fast-forward descendant of the current revision; "
                    "use --allow-downgrade only after reviewing the requested transition"
                )
        before_source, target_source = _instruction_transition(repo, old, target)
        if args.check:
            return 0

        before = dict(manager)
        before["instructionsSource"] = before_source
        target_payload = {
            "repository": recorded_repository,
            "revision": target,
            "releaseVersion": release,
            "bundleIdentity": bundle,
            "channel": channel,
            "requestedRef": requested_ref,
            "instructionsSource": target_source,
        }
        operation = begin_operation(
            home,
            command="update",
            before=before,
            target=target_payload,
        )
        try:
            _git(repo, "checkout", "--detach", target, capture=False)
            update_operation(home, phase="checkout-switched")
            _bootstrap_tooling(home)
            update_operation(home, phase="tooling-ready")
            result = _invoke_internal(
                repo,
                home,
                "_resume-update",
                "--operation-id",
                operation["operationId"],
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"new manager revision failed with exit code {result.returncode}"
                )
            return 0
        except BaseException as update_error:
            print(f"update failed; rolling back to {old}: {update_error}", file=sys.stderr)
            try:
                _git(repo, "checkout", "--detach", old, capture=False)
                _bootstrap_tooling(home)
                rollback = _invoke_internal(
                    repo,
                    home,
                    "_resume-rollback",
                    "--operation-id",
                    operation["operationId"],
                    "--detail",
                    str(update_error),
                )
                if rollback.returncode != 0:
                    raise RuntimeError(
                        f"rollback manager revision failed with exit code {rollback.returncode}"
                    )
            except BaseException as rollback_error:
                update_operation(
                    home,
                    phase="degraded",
                    updateError=str(update_error),
                    rollbackError=str(rollback_error),
                )
                write_manager(
                    home,
                    repository=manager["repository"],
                    revision=manager["revision"],
                    release_version=manager["releaseVersion"],
                    bundle_identity=manager["bundleIdentity"],
                    channel=manager["channel"],
                    requested_ref=manager.get("requestedRef", "main"),
                    status="degraded",
                )
                raise SystemExit(
                    f"update failed and rollback failed: {rollback_error}; run `omh recover`"
                ) from update_error
            raise SystemExit(f"update failed and was rolled back: {update_error}") from update_error


def command_resume_update(args: argparse.Namespace) -> int:
    home = lexical_absolute(manager_home(args.home))
    operation = load_current_operation(home)
    if operation is None or operation.get("operationId") != args.operation_id:
        raise SystemExit("update operation journal does not match the resume request")
    if operation.get("command") != "update":
        raise SystemExit("current operation is not an update")
    operation = _journal_instruction_transition(home, operation)
    target = operation["target"]
    if _revision(REPO_ROOT) != target["revision"]:
        raise SystemExit("managed checkout does not match the journaled update target")
    release, bundle = _distribution(REPO_ROOT)
    if release != target["releaseVersion"] or bundle != target["bundleIdentity"]:
        raise SystemExit("live update target identity changed after validation")

    _manager, desired = _state_context(
        home,
        persist=True,
        allow_manager_drift=True,
        allow_active_operation=True,
    )
    write_manager(
        home,
        repository=target["repository"],
        revision=target["revision"],
        release_version=release,
        bundle_identity=bundle,
        channel=target["channel"],
        requested_ref=target["requestedRef"],
    )
    write_desired(
        home,
        desired_harnesses(desired),
        channel=target["channel"],
    )
    update_operation(home, phase="refreshing-harnesses")
    refresh_args = argparse.Namespace(
        home=str(home),
        targets=[],
        harness=None,
        all=True,
        repair=False,
        codex_home=None,
        codex=None,
        yes=True,
        dry_run=False,
        no_check=False,
        migrate_marketplace=False,
        migrate_from_repo=None,
        operation_id=args.operation_id,
    )
    targets = desired_harnesses(desired)
    for harness in targets:
        _refresh_one(refresh_args, home=home, harness=harness, check_after=True)
        _write_harness_state(home, harness)
    finish_operation(home, outcome="success")
    print(f"updated oh-my-harness to {release} ({target['revision'][:12]})")
    return 0


def command_resume_rollback(args: argparse.Namespace) -> int:
    home = lexical_absolute(manager_home(args.home))
    operation = load_current_operation(home)
    if operation is None or operation.get("operationId") != args.operation_id:
        raise SystemExit("update operation journal does not match the rollback request")
    operation = _journal_instruction_transition(home, operation)
    before = operation["before"]
    if _revision(REPO_ROOT) != before["revision"]:
        raise SystemExit("managed checkout does not match the journaled rollback revision")
    release, bundle = _distribution(REPO_ROOT)
    write_manager(
        home,
        repository=before["repository"],
        revision=before["revision"],
        release_version=release,
        bundle_identity=bundle,
        channel=before["channel"],
        requested_ref=before.get("requestedRef", "main"),
    )
    _manager, desired = _state_context(
        home,
        persist=True,
        allow_active_operation=True,
    )
    refresh_args = argparse.Namespace(
        home=str(home),
        targets=[],
        harness=None,
        all=True,
        repair=False,
        codex_home=None,
        codex=None,
        yes=True,
        dry_run=False,
        no_check=False,
        migrate_marketplace=False,
        migrate_from_repo=None,
        operation_id=args.operation_id,
    )
    for harness in desired_harnesses(desired):
        _refresh_one(refresh_args, home=home, harness=harness, check_after=True)
        _write_harness_state(home, harness)
    finish_operation(home, outcome="rolled-back", detail=args.detail)
    print(f"restored oh-my-harness revision {before['revision'][:12]}")
    return 0


def command_recover(args: argparse.Namespace) -> int:
    home = lexical_absolute(manager_home(args.home))
    with ManagerLock(home):
        operation = load_current_operation(home)
        if operation is None:
            print("no interrupted manager operation")
            return 0
        if operation.get("command") != "update":
            raise SystemExit(
                f"unsupported interrupted operation {operation.get('command')!r}; "
                "manual inspection is required"
            )
        before = operation.get("before")
        if not isinstance(before, dict) or not isinstance(before.get("revision"), str):
            raise SystemExit("update operation journal has no rollback revision")
        repo = repo_path(home)
        _git(repo, "checkout", "--detach", before["revision"], capture=False)
        _bootstrap_tooling(home)
        result = _invoke_internal(
            repo,
            home,
            "_resume-rollback",
            "--operation-id",
            str(operation["operationId"]),
            "--detail",
            "explicit recovery",
        )
        if result.returncode != 0:
            raise SystemExit(
                f"recovery rollback failed with exit code {result.returncode}"
            )
    return 0


def command_manager_repair(args: argparse.Namespace) -> int:
    home = lexical_absolute(manager_home(args.home))
    with ManagerLock(home):
        _manager, desired = _state_context(home, persist=True)
        _bootstrap_tooling(home)
        from install_oh_my_harness import write_launchers

        write_launchers(home=home, repo=REPO_ROOT, dry_run=False)
        refresh_args = argparse.Namespace(
            home=str(home),
            targets=[],
            harness=None,
            all=True,
            repair=False,
            codex_home=None,
            codex=None,
            yes=True,
            dry_run=False,
            no_check=False,
            migrate_marketplace=False,
            migrate_from_repo=None,
            operation_id=None,
        )
        for harness in desired_harnesses(desired):
            _refresh_one(refresh_args, home=home, harness=harness, check_after=True)
            _write_harness_state(home, harness)
        print("manager repair complete")
    return 0


def _cleanup_helper_text() -> str:
    return textwrap.dedent(
        """\
        import os
        import shutil
        import sys
        import time
        from pathlib import Path

        pid = int(sys.argv[1])
        home = Path(sys.argv[2])
        for _ in range(600):
            try:
                os.kill(pid, 0)
            except OSError:
                break
            time.sleep(0.1)
        for _ in range(600):
            if not home.exists():
                break
            try:
                shutil.rmtree(home)
            except OSError:
                time.sleep(0.1)
            else:
                break
        shutil.rmtree(Path(__file__).parent, ignore_errors=True)
        """
    )


def _schedule_self_delete(home: Path) -> None:
    helper_dir = Path(tempfile.mkdtemp(prefix="oh-my-harness-uninstall-"))
    helper = helper_dir / "cleanup.py"
    helper.write_text(_cleanup_helper_text(), encoding="utf-8")
    kwargs: dict[str, object] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = (
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(
        [str(_base_python()), str(helper), str(os.getpid()), str(home)],
        **kwargs,
    )


def command_manager_uninstall(args: argparse.Namespace) -> int:
    home = lexical_absolute(manager_home(args.home))
    with ManagerLock(home):
        _manager, desired = _state_context(home, persist=True)
        installed = list(desired_harnesses(desired))
        if installed and not args.with_harnesses:
            raise SystemExit(
                "manager uninstall requires an empty desired harness set; "
                "run `omh remove --all` first or pass --with-harnesses"
            )
        if installed:
            remove_args = argparse.Namespace(
                home=str(home),
                targets=[],
                harness=None,
                all=True,
                codex_home=None,
                codex=None,
                yes=True,
                dry_run=False,
            )
            for harness in list(installed):
                _remove_one(remove_args, home=home, harness=harness)
                installed.remove(harness)
                write_desired(home, installed)
                remove_harness_receipt(home, harness)
        if not args.yes:
            try:
                answer = input(f"Uninstall oh-my-harness manager at {home} [y/N] ")
            except (EOFError, OSError):
                answer = ""
            if answer.strip() not in {"y", "Y", "yes", "YES", "Yes"}:
                raise SystemExit("manager uninstall was not confirmed")
        allowed = {"repo", "venv", "bin", "state", "bootstrap"}
        unknown = sorted(
            path.name
            for path in home.iterdir()
            if path.name not in allowed
        )
        if unknown and not args.purge_unknown:
            raise SystemExit(
                "manager home contains unknown entries; refusing uninstall: "
                + ", ".join(unknown)
                + "; inspect them or pass --purge-unknown"
            )
        _schedule_self_delete(home)
        print(f"manager uninstall scheduled after current process exits: {home}")
    return 0


def _normalize_argv(argv: list[str]) -> list[str]:
    if not argv:
        return ["refresh"]
    prefix: list[str] = []
    rest = list(argv)
    while rest:
        token = rest[0]
        if token == "--home" and len(rest) >= 2:
            prefix.extend(rest[:2])
            rest = rest[2:]
            continue
        if token.startswith("--home="):
            prefix.append(token)
            rest = rest[1:]
            continue
        break
    if rest and rest[0] == "-Help":
        rest[0] = "--help"
    if rest and rest[0] in {"-h", "--help"}:
        return [*prefix, *rest]
    if not rest or rest[0] not in KNOWN_COMMANDS:
        rest.insert(0, "refresh")
    return [*prefix, *rest]


def _add_harness_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("targets", nargs="*")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--harness", help=argparse.SUPPRESS)
    parser.add_argument("--codex-home")
    parser.add_argument("--codex")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--dry-run", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="omh",
        description="Manage the complete oh-my-harness lifecycle.",
    )
    parser.add_argument("--home", help="Manager home (default: ~/.oh-my-harness).")
    sub = parser.add_subparsers(dest="command", required=True)

    install = sub.add_parser("install", help="Install one or more harness distributions.")
    _add_harness_common(install)
    install.add_argument("--no-check", action="store_true")
    install.add_argument("--migrate-marketplace", action="store_true")
    install.add_argument("--migrate-from-repo")
    install.set_defaults(func=command_install)

    refresh = sub.add_parser("refresh", help="Reconcile installed harnesses with the current release.")
    _add_harness_common(refresh)
    refresh.add_argument("--repair", action="store_true", help="Force current-version re-materialization.")
    refresh.add_argument("--no-check", action="store_true")
    refresh.add_argument("--migrate-marketplace", action="store_true")
    refresh.add_argument("--migrate-from-repo")
    refresh.set_defaults(func=command_refresh)

    remove = sub.add_parser("remove", help="Remove manager-owned resources from harnesses.")
    _add_harness_common(remove)
    remove.set_defaults(func=command_remove)

    update = sub.add_parser("update", help="Update manager source and refresh installed harnesses.")
    update.add_argument("--check", action="store_true", help="Show the available transition without changing state.")
    update.add_argument("--channel", choices=("stable", "main"))
    update.add_argument("--to", help="Explicit Git ref/tag/commit target.")
    update.add_argument("--allow-downgrade", action="store_true")
    update.set_defaults(func=command_update)

    manager = sub.add_parser("manager", help="Repair or uninstall the manager instance.")
    manager_sub = manager.add_subparsers(dest="manager_command", required=True)
    repair = manager_sub.add_parser("repair", help="Rebuild manager runtime and launchers.")
    repair.set_defaults(func=command_manager_repair)
    uninstall = manager_sub.add_parser("uninstall", help="Uninstall the manager instance.")
    uninstall.add_argument("--with-harnesses", action="store_true")
    uninstall.add_argument("--purge-unknown", action="store_true")
    uninstall.add_argument("--yes", action="store_true")
    uninstall.set_defaults(func=command_manager_uninstall)

    status = sub.add_parser("status", help="Show manager and desired harness state.")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=command_status)

    check = sub.add_parser("check", help="Perform read-only closure validation.")
    _add_harness_common(check)
    check.set_defaults(func=lambda args: command_check(args, strict=False))

    doctor = sub.add_parser("doctor", help="Run strict lifecycle diagnostics.")
    _add_harness_common(doctor)
    doctor.set_defaults(func=lambda args: command_check(args, strict=True))

    version = sub.add_parser("version", help="Show release and distribution identity.")
    version.add_argument("--json", action="store_true")
    version.set_defaults(func=command_version)

    recover = sub.add_parser("recover", help="Roll back an interrupted manager update.")
    recover.set_defaults(func=command_recover)

    resume = sub.add_parser("_resume-update", help=argparse.SUPPRESS)
    resume.add_argument("--operation-id", required=True)
    resume.set_defaults(func=command_resume_update)

    rollback = sub.add_parser("_resume-rollback", help=argparse.SUPPRESS)
    rollback.add_argument("--operation-id", required=True)
    rollback.add_argument("--detail")
    rollback.set_defaults(func=command_resume_rollback)

    return parser


def main(argv: list[str] | None = None) -> int:
    normalized = _normalize_argv(list(sys.argv[1:] if argv is None else argv))
    parser = build_parser()
    args = parser.parse_args(normalized)
    return int(args.func(args) or 0)


def cli() -> int:
    try:
        return main()
    except subprocess.CalledProcessError as exc:
        return exc.returncode if exc.returncode > 0 else 1
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        if exc.code:
            print(f"error: {exc.code}", file=sys.stderr)
        return 1
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(cli())

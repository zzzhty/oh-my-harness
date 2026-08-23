#!/usr/bin/env python3
"""Preflight, materialize, and check one harness's global instructions file."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from harness_registry import (
    REGISTRY_FILE,
    HarnessPlan,
    HarnessRegistryError,
    load_harness_registry,
    resolve_harness_plan,
)
from repo_skill_catalog import REPO_ROOT
from sync_agents_skills import is_junction


Input = Callable[[str], str]
Output = Callable[[str], None]


@dataclass(frozen=True)
class TargetSnapshot:
    kind: str
    digest: str | None = None
    link_target: Path | None = None


@dataclass(frozen=True)
class PreparedInstructionSync:
    plan: HarnessPlan
    action: str
    snapshot: TargetSnapshot
    source_digest: str | None
    approved: bool


def _lexists(path: Path) -> bool:
    return os.path.lexists(path)


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _is_reparse_point(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    attributes = getattr(metadata, "st_file_attributes", 0)
    return bool(flag and attributes & flag)


def _snapshot(path: Path) -> TargetSnapshot:
    if path.is_symlink():
        return TargetSnapshot(
            kind="symlink",
            link_target=path.resolve(strict=False),
        )
    if is_junction(path):
        return TargetSnapshot(kind="junction", link_target=path.resolve(strict=False))
    if not _lexists(path):
        return TargetSnapshot(kind="missing")
    if _is_reparse_point(path):
        return TargetSnapshot(kind="reparse-point")
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise SystemExit(f"cannot inspect instructions target: {path}: {exc}") from exc
    if stat.S_ISDIR(metadata.st_mode):
        return TargetSnapshot(kind="directory")
    if not stat.S_ISREG(metadata.st_mode):
        return TargetSnapshot(kind="non-file")
    try:
        digest = _digest(path)
    except OSError as exc:
        raise SystemExit(f"cannot read instructions target: {path}: {exc}") from exc
    return TargetSnapshot(kind="file", digest=digest)


def _validate_source(plan: HarnessPlan) -> None:
    source = plan.instructions_source
    if source.is_symlink() or not source.is_file():
        raise SystemExit(f"canonical instructions source must be a regular file: {source}")


def _validated_source_digest(plan: HarnessPlan) -> str:
    _validate_source(plan)
    try:
        return _digest(plan.instructions_source)
    except OSError as exc:
        raise SystemExit(
            f"cannot read canonical instructions source: {plan.instructions_source}: {exc}"
        ) from exc


def _inspect(
    plan: HarnessPlan,
    *,
    managed_retired_sources: tuple[Path, ...] = (),
) -> PreparedInstructionSync:
    source_digest = _validated_source_digest(plan)
    for shadow in plan.instruction_shadow_paths:
        if _lexists(shadow):
            raise SystemExit(
                f"managed instructions would be shadowed for harness {plan.harness_id}: {shadow}"
            )

    target = plan.instructions_target
    materialization = plan.instructions_materialization
    assert materialization in {"copy", "symlink"}
    snapshot = _snapshot(target)

    if snapshot.kind in {"junction", "reparse-point", "directory", "non-file"}:
        raise SystemExit(
            f"refusing unsupported instructions target type {snapshot.kind}: {target}"
        )
    if snapshot.kind == "missing":
        return PreparedInstructionSync(plan, "create", snapshot, source_digest, False)
    if snapshot.kind == "symlink":
        current_source = plan.instructions_source.resolve(strict=False)
        retired_sources = {
            source.resolve(strict=False) for source in managed_retired_sources
        }
        if (
            snapshot.link_target != current_source
            and snapshot.link_target not in retired_sources
        ):
            raise SystemExit(
                "refusing unmanaged instructions symlink: "
                f"{target} -> {snapshot.link_target}"
            )
        if snapshot.link_target == current_source and materialization == "symlink":
            return PreparedInstructionSync(plan, "current", snapshot, source_digest, True)
        return PreparedInstructionSync(plan, "replace", snapshot, source_digest, False)
    if materialization == "copy" and snapshot.digest == source_digest:
        return PreparedInstructionSync(plan, "current", snapshot, source_digest, True)
    return PreparedInstructionSync(plan, "replace", snapshot, source_digest, False)


def _confirm(prompt: str, *, input_fn: Input) -> bool:
    try:
        answer = input_fn(f"{prompt} [y/N] ")
    except (EOFError, OSError):
        return False
    return answer.strip() in {"y", "Y", "yes", "YES", "Yes"}


def prepare_instruction_sync(
    plan: HarnessPlan,
    *,
    dry_run: bool,
    assume_yes: bool,
    managed_retired_sources: tuple[Path, ...] = (),
    input_fn: Input = input,
    output: Output = print,
) -> PreparedInstructionSync:
    prepared = _inspect(
        plan,
        managed_retired_sources=managed_retired_sources,
    )
    target = plan.instructions_target
    if prepared.action == "current":
        output(f"instructions already current: {target}")
        return prepared

    output(f"InstructionsHarness={plan.harness_id}")
    output(f"InstructionsSource={plan.instructions_source}")
    output(f"InstructionsTarget={target}")
    output(f"InstructionsTargetType={prepared.snapshot.kind}")
    output(f"InstructionsMaterialization={plan.instructions_materialization}")
    if prepared.snapshot.digest is not None:
        output(f"InstructionsTargetSHA256={prepared.snapshot.digest}")
        output(f"InstructionsSourceSHA256={prepared.source_digest}")
    if (
        prepared.snapshot.kind == "symlink"
        and prepared.snapshot.link_target
        in {source.resolve(strict=False) for source in managed_retired_sources}
    ):
        output(
            "InstructionsRetiredManagedSource="
            f"{prepared.snapshot.link_target}"
        )
    if dry_run:
        output(f"would {prepared.action} harness instructions: {target}")
        return PreparedInstructionSync(
            plan,
            prepared.action,
            prepared.snapshot,
            prepared.source_digest,
            True,
        )

    if prepared.action == "create":
        approved = assume_yes or _confirm(
            f"Create {plan.harness_id} global instructions",
            input_fn=input_fn,
        )
        if assume_yes:
            output(f"Create {plan.harness_id} global instructions [auto-confirmed]")
    else:
        output(
            "Existing instructions replacement requires a live confirmation; "
            "--yes does not authorize replacement."
        )
        approved = _confirm(
            f"Replace existing {plan.harness_id} global instructions",
            input_fn=input_fn,
        )
    if not approved:
        raise SystemExit(f"{plan.harness_id} instructions sync was not confirmed")
    return PreparedInstructionSync(
        plan,
        prepared.action,
        prepared.snapshot,
        prepared.source_digest,
        True,
    )


def _revalidate(prepared: PreparedInstructionSync) -> None:
    source_digest = _validated_source_digest(prepared.plan)
    if source_digest != prepared.source_digest:
        raise SystemExit(
            "canonical instructions source changed after preflight; refusing write: "
            f"{prepared.plan.instructions_source}"
        )
    target = prepared.plan.instructions_target
    current = _snapshot(target)
    if current != prepared.snapshot:
        raise SystemExit(
            "instructions target changed after preflight; refusing replacement: "
            f"{target}: expected {prepared.snapshot}, found {current}"
        )


def _atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.oh-my-harness-",
        dir=target.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copyfile(source, temporary)
        shutil.copymode(source, temporary)
        os.replace(temporary, target)
    finally:
        if _lexists(temporary):
            temporary.unlink()


def _atomic_symlink(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".{target.name}.oh-my-harness-{os.getpid()}"
    if _lexists(temporary):
        raise SystemExit(f"temporary instructions link already exists: {temporary}")
    try:
        temporary.symlink_to(source)
        os.replace(temporary, target)
    finally:
        if _lexists(temporary):
            temporary.unlink()


def apply_instruction_sync(prepared: PreparedInstructionSync, *, dry_run: bool) -> None:
    if prepared.action == "current" or dry_run:
        return
    if not prepared.approved:
        raise SystemExit("instructions mutation was not approved during preflight")
    _revalidate(prepared)
    plan = prepared.plan
    target = plan.instructions_target
    if plan.instructions_materialization == "copy":
        _atomic_copy(plan.instructions_source, target)
    elif plan.instructions_materialization == "symlink":
        _atomic_symlink(plan.instructions_source, target)
    else:  # pragma: no cover - registry validation owns this branch
        raise SystemExit(
            f"unsupported instructions materialization: {plan.instructions_materialization!r}"
        )
    issues = check_instruction_sync(plan)
    if issues:
        raise SystemExit("instructions closure failed after sync: " + "; ".join(issues))
    print(f"instructions synced for {plan.harness_id}: {target}")


def check_instruction_sync(plan: HarnessPlan) -> list[str]:
    try:
        prepared = _inspect(plan)
    except SystemExit as exc:
        return [str(exc)]
    if prepared.action == "current":
        return []
    target = plan.instructions_target
    if prepared.action == "create":
        return [f"global instructions are missing for {plan.harness_id}: {target}"]
    return [
        f"global instructions differ for {plan.harness_id}: "
        f"{target} ({prepared.snapshot.kind})"
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage global instructions for one harness.")
    parser.add_argument(
        "--harness",
        help="Registry harness id (default: registry-owned).",
    )
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--registry", default=str(REGISTRY_FILE))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve(strict=False)
    registry_path = Path(args.registry).expanduser().resolve(strict=False)
    try:
        registry = load_harness_registry(registry_path, repo_root=repo_root)
        plan = resolve_harness_plan(registry, args.harness, repo_root=repo_root)
    except HarnessRegistryError as exc:
        raise SystemExit(str(exc)) from exc
    if args.check:
        issues = check_instruction_sync(plan)
        if issues:
            for issue in issues:
                print(f"FAIL {issue}")
            return 1
        print(f"OK instructions are current for {plan.harness_id}")
        return 0
    prepared = prepare_instruction_sync(
        plan,
        dry_run=args.dry_run,
        assume_yes=args.yes,
    )
    apply_instruction_sync(prepared, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

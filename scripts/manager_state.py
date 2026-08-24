#!/usr/bin/env python3
"""Persistent manager lifecycle state and cross-process mutation locking."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from manager_paths import PRODUCT_NAME, state_path

STATE_SCHEMA_VERSION = "2026-08-24"
MANAGER_FILE = "manager.json"
DESIRED_FILE = "desired.json"
HARNESS_STATE_DIR = "harnesses"
OPERATIONS_DIR = "operations"
CURRENT_OPERATION_FILE = "current.json"
HISTORY_DIR = "history"
LOCK_FILE = "manager.lock"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_object(path: Path, *, label: str, required: bool = True) -> dict[str, Any] | None:
    if not path.exists():
        if required:
            raise SystemExit(f"{label} is missing: {path}")
        return None
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"{label} must be an ordinary file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"{label} is unreadable: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} must contain a JSON object: {path}")
    return payload


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise SystemExit(f"state parent must be an ordinary directory: {path.parent}")
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def install_receipt(home: Path) -> dict[str, Any]:
    path = state_path(home) / "install.json"
    payload = _load_object(path, label="initial installation receipt")
    assert payload is not None
    if payload.get("product") != PRODUCT_NAME:
        raise SystemExit(f"initial installation receipt belongs to another product: {path}")
    if payload.get("status") not in {"installing", "ready"}:
        raise SystemExit(f"initial installation receipt has unsupported status: {path}")
    return payload


def state_root(home: Path) -> Path:
    return state_path(home)


def manager_file(home: Path) -> Path:
    return state_root(home) / MANAGER_FILE


def desired_file(home: Path) -> Path:
    return state_root(home) / DESIRED_FILE


def harness_file(home: Path, harness: str) -> Path:
    return state_root(home) / HARNESS_STATE_DIR / f"{harness}.json"


def current_operation_file(home: Path) -> Path:
    return state_root(home) / OPERATIONS_DIR / CURRENT_OPERATION_FILE


def operation_history_dir(home: Path) -> Path:
    return state_root(home) / OPERATIONS_DIR / HISTORY_DIR


def _validate_manager_payload(payload: dict[str, Any], *, path: Path) -> None:
    if payload.get("schemaVersion") != STATE_SCHEMA_VERSION:
        raise SystemExit(f"manager state schema is unsupported: {path}")
    if payload.get("product") != PRODUCT_NAME:
        raise SystemExit(f"manager state belongs to another product: {path}")
    if payload.get("status") not in {"ready", "degraded"}:
        raise SystemExit(f"manager state status is unsupported: {path}")
    for field in ("repository", "revision", "releaseVersion", "bundleIdentity", "channel"):
        value = payload.get(field)
        if not isinstance(value, str) or not value:
            raise SystemExit(f"manager state field {field!r} is invalid: {path}")


def _validate_desired_payload(payload: dict[str, Any], *, path: Path) -> None:
    if payload.get("schemaVersion") != STATE_SCHEMA_VERSION:
        raise SystemExit(f"desired state schema is unsupported: {path}")
    harnesses = payload.get("harnesses")
    if (
        not isinstance(harnesses, list)
        or not all(isinstance(item, str) and item for item in harnesses)
        or harnesses != sorted(set(harnesses))
    ):
        raise SystemExit(f"desired harness set is invalid: {path}")
    policy = payload.get("updatePolicy")
    if not isinstance(policy, dict) or policy.get("channel") not in {"stable", "main"}:
        raise SystemExit(f"desired update policy is invalid: {path}")


def derive_initial_state(
    home: Path,
    *,
    repository: str,
    revision: str,
    release_version: str,
    bundle_identity: str,
    persist: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    receipt = install_receipt(home)
    recorded_repository = receipt.get("repository")
    if isinstance(recorded_repository, str) and recorded_repository:
        repository = recorded_repository
    initial_harness = receipt.get("harness")
    harnesses: list[str] = []
    if receipt.get("status") == "ready" and isinstance(initial_harness, str) and initial_harness:
        harnesses = [initial_harness]
    manager = {
        "schemaVersion": STATE_SCHEMA_VERSION,
        "product": PRODUCT_NAME,
        "status": "ready",
        "repository": repository,
        "channel": "stable",
        "requestedRef": receipt.get("ref") if isinstance(receipt.get("ref"), str) else "main",
        "revision": revision,
        "releaseVersion": release_version,
        "bundleIdentity": bundle_identity,
        "updatedAt": _now(),
    }
    desired = {
        "schemaVersion": STATE_SCHEMA_VERSION,
        "harnesses": sorted(set(harnesses)),
        "updatePolicy": {"channel": "stable"},
        "updatedAt": _now(),
    }
    if persist:
        atomic_write_json(manager_file(home), manager)
        atomic_write_json(desired_file(home), desired)
    return manager, desired


def load_or_initialize(
    home: Path,
    *,
    repository: str,
    revision: str,
    release_version: str,
    bundle_identity: str,
    persist: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manager_path = manager_file(home)
    desired_path = desired_file(home)
    manager = _load_object(manager_path, label="manager state", required=False)
    desired = _load_object(desired_path, label="desired harness state", required=False)
    if manager is None and desired is None:
        return derive_initial_state(
            home,
            repository=repository,
            revision=revision,
            release_version=release_version,
            bundle_identity=bundle_identity,
            persist=persist,
        )
    if manager is None or desired is None:
        raise SystemExit(
            "manager lifecycle state is incomplete; both manager.json and desired.json "
            "must exist or both must be absent"
        )
    _validate_manager_payload(manager, path=manager_path)
    _validate_desired_payload(desired, path=desired_path)
    return manager, desired


def desired_harnesses(desired: dict[str, Any]) -> tuple[str, ...]:
    return tuple(desired["harnesses"])


def write_desired(home: Path, harnesses: Iterable[str], *, channel: str | None = None) -> dict[str, Any]:
    current = _load_object(desired_file(home), label="desired harness state")
    assert current is not None
    _validate_desired_payload(current, path=desired_file(home))
    selected_channel = channel or current["updatePolicy"]["channel"]
    if selected_channel not in {"stable", "main"}:
        raise SystemExit(f"unsupported update channel: {selected_channel}")
    payload = {
        "schemaVersion": STATE_SCHEMA_VERSION,
        "harnesses": sorted(set(harnesses)),
        "updatePolicy": {"channel": selected_channel},
        "updatedAt": _now(),
    }
    atomic_write_json(desired_file(home), payload)
    return payload


def write_manager(
    home: Path,
    *,
    repository: str,
    revision: str,
    release_version: str,
    bundle_identity: str,
    channel: str,
    requested_ref: str,
    status: str = "ready",
) -> dict[str, Any]:
    if channel not in {"stable", "main"}:
        raise SystemExit(f"unsupported update channel: {channel}")
    if status not in {"ready", "degraded"}:
        raise SystemExit(f"unsupported manager status: {status}")
    payload = {
        "schemaVersion": STATE_SCHEMA_VERSION,
        "product": PRODUCT_NAME,
        "status": status,
        "repository": repository,
        "channel": channel,
        "requestedRef": requested_ref,
        "revision": revision,
        "releaseVersion": release_version,
        "bundleIdentity": bundle_identity,
        "updatedAt": _now(),
    }
    atomic_write_json(manager_file(home), payload)
    return payload


def write_harness_receipt(
    home: Path,
    *,
    harness: str,
    manager_revision: str,
    release_version: str,
    bundle_identity: str,
    root: str,
) -> None:
    payload = {
        "schemaVersion": STATE_SCHEMA_VERSION,
        "harness": harness,
        "status": "ready",
        "managerRevision": manager_revision,
        "releaseVersion": release_version,
        "bundleIdentity": bundle_identity,
        "root": root,
        "updatedAt": _now(),
    }
    atomic_write_json(harness_file(home, harness), payload)


def remove_harness_receipt(home: Path, harness: str) -> None:
    path = harness_file(home, harness)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise SystemExit(f"harness receipt is not an ordinary file: {path}")
        path.unlink()


def load_current_operation(home: Path) -> dict[str, Any] | None:
    return _load_object(
        current_operation_file(home),
        label="current manager operation",
        required=False,
    )


def begin_operation(home: Path, *, command: str, before: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    path = current_operation_file(home)
    if path.exists():
        raise SystemExit(
            f"an interrupted manager operation already exists: {path}; run `omh recover`"
        )
    operation_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    payload = {
        "schemaVersion": STATE_SCHEMA_VERSION,
        "operationId": operation_id,
        "command": command,
        "phase": "prepared",
        "before": before,
        "target": target,
        "startedAt": _now(),
    }
    atomic_write_json(path, payload)
    return payload


def update_operation(home: Path, *, phase: str, **fields: Any) -> dict[str, Any]:
    path = current_operation_file(home)
    payload = _load_object(path, label="current manager operation")
    assert payload is not None
    payload["phase"] = phase
    payload["updatedAt"] = _now()
    payload.update(fields)
    atomic_write_json(path, payload)
    return payload


def finish_operation(home: Path, *, outcome: str, detail: str | None = None) -> None:
    path = current_operation_file(home)
    payload = _load_object(path, label="current manager operation")
    assert payload is not None
    payload["outcome"] = outcome
    payload["finishedAt"] = _now()
    if detail:
        payload["detail"] = detail
    history = operation_history_dir(home)
    history.mkdir(parents=True, exist_ok=True)
    target = history / f"{payload['operationId']}.json"
    atomic_write_json(target, payload)
    path.unlink()


class ManagerLock(AbstractContextManager["ManagerLock"]):
    """Exclusive mutation lock shared by all lifecycle commands."""

    def __init__(self, home: Path) -> None:
        self.path = state_root(home) / LOCK_FILE
        self.handle: Any | None = None

    def __enter__(self) -> "ManagerLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b")
        self.handle.seek(0)
        self.handle.write(b"\0")
        self.handle.flush()
        try:
            if os.name == "nt":
                import msvcrt

                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            self.handle.close()
            self.handle = None
            raise SystemExit(
                f"another oh-my-harness mutation is already running: {self.path}"
            ) from exc
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self.handle is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None

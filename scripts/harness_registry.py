#!/usr/bin/env python3
"""Load and resolve the repository-owned harness distribution registry."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Mapping

from repo_skill_catalog import REPO_ROOT, SkillCatalog


REGISTRY_FILE = REPO_ROOT / ".agents" / "harnesses" / "registry.json"
REGISTRY_SCHEMA_VERSION = 1
HARNESS_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
ENVIRONMENT_NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")

SKILLS_DRIVERS = frozenset({"codex-marketplace", "directory-projection"})
INSTRUCTIONS_DRIVERS = frozenset({"managed-file", "settings-derived-file"})
EXTRAS = frozenset(
    {"codex-agent-support", "watcher-hooks", "watcher-doctor"}
)


class HarnessRegistryError(ValueError):
    """Raised when the registry or a resolved harness plan is invalid."""


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    payload: dict[str, object] = {}
    for key, value in pairs:
        if key in payload:
            raise HarnessRegistryError(f"harness registry contains duplicate JSON key: {key!r}")
        payload[key] = value
    return payload


@dataclass(frozen=True)
class RootCandidate:
    source: str
    append: Path
    environment: str | None = None


@dataclass(frozen=True)
class ExcludedSkillRootSpec:
    root_id: str
    root_candidates: tuple[RootCandidate, ...]
    relative_path: Path


@dataclass(frozen=True)
class ReconciliationSpec:
    prune_policy: str
    confirmation: str


@dataclass(frozen=True)
class SkillsSpec:
    driver: str
    reconciliation: ReconciliationSpec
    relative_path: Path | None = None
    posix_materialization: str | None = None
    windows_materialization: str | None = None
    marketplace_path: Path | None = None
    install_manifest_path: Path | None = None


@dataclass(frozen=True)
class InstructionsSpec:
    driver: str
    relative_path: Path | None = None
    settings_path: Path | None = None
    setting_path: tuple[str, ...] = ()
    default_relative_path: Path | None = None
    multiple_targets_policy: str | None = None
    posix_materialization: str | None = None
    windows_materialization: str | None = None
    create_confirmation: str | None = None
    replace_confirmation: str | None = None
    shadow_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class HarnessSpec:
    harness_id: str
    display_name: str
    root_candidates: tuple[RootCandidate, ...]
    skills: SkillsSpec
    instructions: InstructionsSpec
    extras: tuple[str, ...]


@dataclass(frozen=True)
class HarnessRegistry:
    path: Path
    default_harness: str
    instructions_source: Path
    excluded_skill_roots: Mapping[str, ExcludedSkillRootSpec]
    harnesses: Mapping[str, HarnessSpec]

    @property
    def choices(self) -> tuple[str, ...]:
        return tuple(sorted(self.harnesses))


@dataclass(frozen=True)
class HarnessPlan:
    registry_path: Path
    repo_root: Path
    harness: HarnessSpec
    root: Path
    skills_root: Path | None
    skills_materialization: str | None
    instructions_source: Path
    instructions_target: Path
    instructions_materialization: str
    instruction_shadow_paths: tuple[Path, ...]
    excluded_skill_roots: tuple[Path, ...]
    marketplace_path: Path | None
    install_manifest_path: Path | None

    @property
    def harness_id(self) -> str:
        return self.harness.harness_id


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise HarnessRegistryError(f"{label} must be an object")
    if not all(isinstance(key, str) for key in value):
        raise HarnessRegistryError(f"{label} keys must be strings")
    return value


def _keys(
    value: dict[str, object],
    *,
    label: str,
    required: set[str],
    optional: set[str] | None = None,
) -> None:
    allowed = required | set(optional or ())
    missing = sorted(required - set(value))
    extra = sorted(set(value) - allowed)
    if missing:
        raise HarnessRegistryError(f"{label} is missing required fields: {', '.join(missing)}")
    if extra:
        raise HarnessRegistryError(f"{label} has unsupported fields: {', '.join(extra)}")


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HarnessRegistryError(f"{label} must be a non-empty string")
    return value.strip()


def _relative_path(value: object, *, label: str, allow_empty: bool = False) -> Path:
    if not isinstance(value, str):
        raise HarnessRegistryError(f"{label} must be a string")
    raw = value.strip()
    if not raw:
        if allow_empty:
            return Path()
        raise HarnessRegistryError(f"{label} must be a non-empty relative path")
    if "\\" in raw:
        raise HarnessRegistryError(f"{label} must use portable forward-slash separators: {raw!r}")
    posix_path = PurePosixPath(raw)
    windows_path = PureWindowsPath(raw)
    raw_parts = raw.split("/")
    if (
        posix_path.is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or ".." in raw_parts
    ):
        raise HarnessRegistryError(f"{label} must not escape its owning root: {raw!r}")
    if any(part in {"", "."} for part in raw_parts):
        raise HarnessRegistryError(f"{label} must be normalized: {raw!r}")
    return Path(*posix_path.parts)


def _root_candidate(value: object, *, label: str) -> RootCandidate:
    payload = _object(value, label=label)
    _keys(
        payload,
        label=label,
        required={"source", "append"},
        optional={"name"},
    )
    source = _string(payload["source"], label=f"{label}.source")
    append = _relative_path(payload["append"], label=f"{label}.append", allow_empty=True)
    if source == "environment":
        environment = _string(payload.get("name"), label=f"{label}.name")
        if not ENVIRONMENT_NAME_PATTERN.fullmatch(environment):
            raise HarnessRegistryError(f"{label}.name is not a valid environment variable")
        return RootCandidate(source=source, append=append, environment=environment)
    if source == "user-home":
        if "name" in payload:
            raise HarnessRegistryError(f"{label}.name is valid only for environment roots")
        return RootCandidate(source=source, append=append)
    raise HarnessRegistryError(f"{label}.source is unsupported: {source!r}")


def _root_candidates(value: object, *, label: str) -> tuple[RootCandidate, ...]:
    payload = _object(value, label=label)
    _keys(payload, label=label, required={"candidates"})
    candidates_value = payload["candidates"]
    if not isinstance(candidates_value, list) or not candidates_value:
        raise HarnessRegistryError(f"{label}.candidates must be a non-empty array")
    return tuple(
        _root_candidate(entry, label=f"{label}.candidates[{index}]")
        for index, entry in enumerate(candidates_value)
    )


def _excluded_skill_root(root_id: str, value: object) -> ExcludedSkillRootSpec:
    label = f"excludedSkillRoots.{root_id}"
    if not HARNESS_ID_PATTERN.fullmatch(root_id):
        raise HarnessRegistryError(f"invalid excluded skill root id: {root_id!r}")
    payload = _object(value, label=label)
    _keys(payload, label=label, required={"root", "relativePath"})
    return ExcludedSkillRootSpec(
        root_id=root_id,
        root_candidates=_root_candidates(payload["root"], label=f"{label}.root"),
        relative_path=_relative_path(
            payload["relativePath"], label=f"{label}.relativePath"
        ),
    )


def _materialization(
    value: object,
    *,
    label: str,
    posix_allowed: set[str],
    windows_allowed: set[str],
) -> tuple[str, str]:
    payload = _object(value, label=label)
    _keys(payload, label=label, required={"posix", "windows"})
    posix = _string(payload["posix"], label=f"{label}.posix")
    windows = _string(payload["windows"], label=f"{label}.windows")
    if posix not in posix_allowed:
        raise HarnessRegistryError(f"{label}.posix is unsupported: {posix!r}")
    if windows not in windows_allowed:
        raise HarnessRegistryError(f"{label}.windows is unsupported: {windows!r}")
    return posix, windows


def _reconciliation(value: object, *, label: str) -> ReconciliationSpec:
    payload = _object(value, label=label)
    _keys(payload, label=label, required={"prunePolicy", "confirmation"})
    prune_policy = _string(payload["prunePolicy"], label=f"{label}.prunePolicy")
    confirmation = _string(payload["confirmation"], label=f"{label}.confirmation")
    if prune_policy != "managed-stale":
        raise HarnessRegistryError(f"{label}.prunePolicy is unsupported: {prune_policy!r}")
    if confirmation not in {"none", "when-nonempty"}:
        raise HarnessRegistryError(f"{label}.confirmation is unsupported: {confirmation!r}")
    return ReconciliationSpec(prune_policy=prune_policy, confirmation=confirmation)


def _skills(value: object, *, label: str) -> SkillsSpec:
    payload = _object(value, label=label)
    driver = _string(payload.get("driver"), label=f"{label}.driver")
    if driver not in SKILLS_DRIVERS:
        raise HarnessRegistryError(f"{label}.driver is unsupported: {driver!r}")
    if driver == "codex-marketplace":
        _keys(
            payload,
            label=label,
            required={"driver", "marketplacePath", "installManifestPath", "reconciliation"},
        )
        return SkillsSpec(
            driver=driver,
            marketplace_path=_relative_path(
                payload["marketplacePath"], label=f"{label}.marketplacePath"
            ),
            install_manifest_path=_relative_path(
                payload["installManifestPath"], label=f"{label}.installManifestPath"
            ),
            reconciliation=_reconciliation(
                payload["reconciliation"], label=f"{label}.reconciliation"
            ),
        )

    _keys(
        payload,
        label=label,
        required={"driver", "relativePath", "materialization", "reconciliation"},
    )
    posix, windows = _materialization(
        payload["materialization"],
        label=f"{label}.materialization",
        posix_allowed={"directory-symlink"},
        windows_allowed={"directory-junction"},
    )
    reconciliation = _reconciliation(
        payload["reconciliation"], label=f"{label}.reconciliation"
    )
    if reconciliation.confirmation != "none":
        raise HarnessRegistryError(
            f"{label}.reconciliation.confirmation must be 'none' for directory projection"
        )
    return SkillsSpec(
        driver=driver,
        relative_path=_relative_path(payload["relativePath"], label=f"{label}.relativePath"),
        posix_materialization=posix,
        windows_materialization=windows,
        reconciliation=reconciliation,
    )


def _confirmation(value: object, *, label: str) -> tuple[str, str]:
    payload = _object(value, label=label)
    _keys(payload, label=label, required={"create", "replace"})
    create = _string(payload["create"], label=f"{label}.create")
    replace = _string(payload["replace"], label=f"{label}.replace")
    if create != "assume-yes-or-interactive":
        raise HarnessRegistryError(f"{label}.create is unsupported: {create!r}")
    if replace != "interactive":
        raise HarnessRegistryError(f"{label}.replace is unsupported: {replace!r}")
    return create, replace


def _shadow_paths(value: object, *, label: str) -> tuple[Path, ...]:
    if not isinstance(value, list):
        raise HarnessRegistryError(f"{label} must be an array")
    paths = tuple(
        _relative_path(entry, label=f"{label}[{index}]")
        for index, entry in enumerate(value)
    )
    if len(set(paths)) != len(paths):
        raise HarnessRegistryError(f"{label} contains duplicate paths")
    return paths


def _instructions(value: object, *, label: str) -> InstructionsSpec:
    payload = _object(value, label=label)
    driver = _string(payload.get("driver"), label=f"{label}.driver")
    if driver not in INSTRUCTIONS_DRIVERS:
        raise HarnessRegistryError(f"{label}.driver is unsupported: {driver!r}")
    common_required = {"driver", "materialization", "confirmation", "shadowPaths"}
    if driver == "managed-file":
        _keys(payload, label=label, required=common_required | {"relativePath"})
        relative_path = _relative_path(
            payload["relativePath"], label=f"{label}.relativePath"
        )
        settings_path = None
        setting_path: tuple[str, ...] = ()
        default_relative_path = None
        multiple_targets_policy = None
    else:
        _keys(
            payload,
            label=label,
            required=common_required
            | {
                "settingsPath",
                "settingPath",
                "defaultRelativePath",
                "multipleTargetsPolicy",
            },
        )
        settings_path = _relative_path(payload["settingsPath"], label=f"{label}.settingsPath")
        raw_setting_path = payload["settingPath"]
        if not isinstance(raw_setting_path, list) or not raw_setting_path:
            raise HarnessRegistryError(f"{label}.settingPath must be a non-empty array")
        setting_path = tuple(
            _string(entry, label=f"{label}.settingPath[{index}]")
            for index, entry in enumerate(raw_setting_path)
        )
        default_relative_path = _relative_path(
            payload["defaultRelativePath"], label=f"{label}.defaultRelativePath"
        )
        multiple_targets_policy = _string(
            payload["multipleTargetsPolicy"], label=f"{label}.multipleTargetsPolicy"
        )
        if multiple_targets_policy != "reject":
            raise HarnessRegistryError(
                f"{label}.multipleTargetsPolicy is unsupported: {multiple_targets_policy!r}"
            )
        relative_path = None

    posix, windows = _materialization(
        payload["materialization"],
        label=f"{label}.materialization",
        posix_allowed={"copy", "symlink"},
        windows_allowed={"copy"},
    )
    create, replace = _confirmation(payload["confirmation"], label=f"{label}.confirmation")
    return InstructionsSpec(
        driver=driver,
        relative_path=relative_path,
        settings_path=settings_path,
        setting_path=setting_path,
        default_relative_path=default_relative_path,
        multiple_targets_policy=multiple_targets_policy,
        posix_materialization=posix,
        windows_materialization=windows,
        create_confirmation=create,
        replace_confirmation=replace,
        shadow_paths=_shadow_paths(payload["shadowPaths"], label=f"{label}.shadowPaths"),
    )


def _harness(harness_id: str, value: object) -> HarnessSpec:
    label = f"harnesses.{harness_id}"
    if not HARNESS_ID_PATTERN.fullmatch(harness_id):
        raise HarnessRegistryError(f"invalid harness id: {harness_id!r}")
    payload = _object(value, label=label)
    _keys(
        payload,
        label=label,
        required={
            "displayName",
            "root",
            "skills",
            "instructions",
            "extras",
        },
    )
    candidates = _root_candidates(payload["root"], label=f"{label}.root")
    extras_value = payload["extras"]
    if not isinstance(extras_value, list):
        raise HarnessRegistryError(f"{label}.extras must be an array")
    extras = tuple(_string(entry, label=f"{label}.extras") for entry in extras_value)
    if len(set(extras)) != len(extras):
        raise HarnessRegistryError(f"{label}.extras contains duplicate values")
    unsupported_extras = sorted(set(extras) - EXTRAS)
    if unsupported_extras:
        raise HarnessRegistryError(
            f"{label}.extras contains unsupported values: {', '.join(unsupported_extras)}"
        )

    skills = _skills(payload["skills"], label=f"{label}.skills")
    instructions = _instructions(payload["instructions"], label=f"{label}.instructions")
    if extras and harness_id != "codex":
        raise HarnessRegistryError(
            f"{label} cannot declare Codex-specific extras outside the codex harness"
        )
    if skills.driver == "codex-marketplace" and harness_id != "codex":
        raise HarnessRegistryError(
            f"{label} cannot use the Codex marketplace driver outside the codex harness"
        )
    return HarnessSpec(
        harness_id=harness_id,
        display_name=_string(payload["displayName"], label=f"{label}.displayName"),
        root_candidates=candidates,
        skills=skills,
        instructions=instructions,
        extras=extras,
    )


def load_harness_registry(
    path: Path = REGISTRY_FILE,
    *,
    repo_root: Path = REPO_ROOT,
) -> HarnessRegistry:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_object,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise HarnessRegistryError(f"harness registry is not valid readable JSON: {path}: {exc}") from exc
    root = _object(payload, label="registry")
    _keys(
        root,
        label="registry",
        required={
            "$schema",
            "schemaVersion",
            "defaults",
            "sources",
            "excludedSkillRoots",
            "harnesses",
        },
    )
    if root["$schema"] != "./registry.schema.json":
        raise HarnessRegistryError("registry.$schema must be './registry.schema.json'")
    if (
        type(root["schemaVersion"]) is not int
        or root["schemaVersion"] != REGISTRY_SCHEMA_VERSION
    ):
        raise HarnessRegistryError(
            f"registry.schemaVersion must be {REGISTRY_SCHEMA_VERSION}"
        )
    defaults = _object(root["defaults"], label="registry.defaults")
    _keys(defaults, label="registry.defaults", required={"harness"})
    default_harness = _string(defaults["harness"], label="registry.defaults.harness")
    sources = _object(root["sources"], label="registry.sources")
    _keys(sources, label="registry.sources", required={"instructions"})
    instructions_source = _relative_path(
        sources["instructions"], label="registry.sources.instructions"
    )
    excluded_payload = _object(
        root["excludedSkillRoots"], label="registry.excludedSkillRoots"
    )
    if not excluded_payload:
        raise HarnessRegistryError("registry.excludedSkillRoots must not be empty")
    excluded_skill_roots = {
        root_id: _excluded_skill_root(root_id, value)
        for root_id, value in excluded_payload.items()
    }
    harness_payload = _object(root["harnesses"], label="registry.harnesses")
    if not harness_payload:
        raise HarnessRegistryError("registry.harnesses must not be empty")
    harnesses = {
        harness_id: _harness(harness_id, value)
        for harness_id, value in harness_payload.items()
    }
    if default_harness not in harnesses:
        raise HarnessRegistryError(
            f"registry default harness does not exist: {default_harness!r}"
        )
    if "codex" not in harnesses or harnesses["codex"].skills.driver != "codex-marketplace":
        raise HarnessRegistryError("registry must define the codex marketplace harness")
    resolved_repo_root = repo_root.resolve(strict=False)
    return HarnessRegistry(
        path=path.resolve(strict=False),
        default_harness=default_harness,
        instructions_source=_repo_owned_path(
            resolved_repo_root,
            instructions_source,
            label="registry instructions source",
        ),
        excluded_skill_roots=excluded_skill_roots,
        harnesses=harnesses,
    )


def _resolve_root(
    candidates: tuple[RootCandidate, ...],
    *,
    label: str,
    environ: Mapping[str, str],
    user_home: Path,
) -> Path:
    if not user_home.is_absolute():
        raise HarnessRegistryError(f"user home must be absolute: {user_home}")
    for candidate in candidates:
        if candidate.source == "environment":
            assert candidate.environment is not None
            raw_root = environ.get(candidate.environment, "").strip()
            if not raw_root:
                continue
            base = Path(raw_root).expanduser()
            if not base.is_absolute():
                raise HarnessRegistryError(
                    f"{candidate.environment} must be an absolute path: {raw_root!r}"
                )
        else:
            base = user_home
        return (base / candidate.append).resolve(strict=False)
    raise HarnessRegistryError(f"{label} has no usable root candidate")


def _settings_value(settings: object, path: tuple[str, ...]) -> object | None:
    current = settings
    for field in path:
        if not isinstance(current, dict) or field not in current:
            return None
        current = current[field]
    return current


def _join_within(root: Path, relative: Path, *, label: str) -> Path:
    """Join lexically so an existing target symlink does not replace its managed path."""

    target = Path(os.path.abspath(os.path.join(root, relative)))
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise HarnessRegistryError(f"{label} escapes harness root: {target}") from exc
    return target


def _repo_owned_path(root: Path, relative: Path, *, label: str) -> Path:
    """Keep repository metadata lexical while rejecting an existing symlink escape."""

    target = _join_within(root, relative, label=label)
    resolved = target.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise HarnessRegistryError(f"{label} resolves outside repository root: {target}") from exc
    return target


def _settings_instruction_path(spec: InstructionsSpec, *, root: Path) -> Path:
    assert spec.settings_path is not None
    assert spec.default_relative_path is not None
    settings_file = root / spec.settings_path
    if settings_file.exists():
        if not settings_file.is_file() or settings_file.is_symlink():
            raise HarnessRegistryError(
                f"instructions settings path is not an inspectable file: {settings_file}"
            )
        try:
            settings = json.loads(settings_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HarnessRegistryError(
                f"instructions settings are not valid readable JSON: {settings_file}: {exc}"
            ) from exc
        raw_target = _settings_value(settings, spec.setting_path)
    else:
        raw_target = None

    if raw_target is None:
        relative = spec.default_relative_path
    elif isinstance(raw_target, str):
        relative = _relative_path(raw_target, label="configured instructions target")
    elif isinstance(raw_target, list):
        if spec.multiple_targets_policy == "reject" and len(raw_target) != 1:
            raise HarnessRegistryError(
                "configured instructions target lists multiple filenames; registry policy rejects duplicate distribution"
            )
        relative = _relative_path(raw_target[0], label="configured instructions target")
    else:
        raise HarnessRegistryError(
            "configured instructions target must be a string or a single-item string array"
        )
    return _join_within(root, relative, label="configured instructions target")


def resolve_harness_plan(
    registry: HarnessRegistry,
    harness_id: str | None = None,
    *,
    repo_root: Path = REPO_ROOT,
    environ: Mapping[str, str] | None = None,
    user_home: Path | None = None,
    os_name: str = os.name,
) -> HarnessPlan:
    selected = registry.default_harness if harness_id is None else harness_id
    harness = registry.harnesses.get(selected)
    if harness is None:
        raise HarnessRegistryError(
            f"unknown harness {selected!r}; expected one of: {', '.join(registry.choices)}"
        )
    environment = environ if environ is not None else os.environ
    home = (user_home or Path.home()).expanduser()
    root = _resolve_root(
        harness.root_candidates,
        label=f"harness {harness.harness_id!r}",
        environ=environment,
        user_home=home,
    )
    platform_materialization = "windows" if os_name == "nt" else "posix"

    skills = harness.skills
    if skills.driver == "directory-projection":
        assert skills.relative_path is not None
        skills_root = _join_within(
            root,
            skills.relative_path,
            label="resolved skills target",
        )
        skills_materialization = (
            skills.windows_materialization
            if platform_materialization == "windows"
            else skills.posix_materialization
        )
    else:
        skills_root = None
        skills_materialization = None

    instructions = harness.instructions
    if instructions.driver == "settings-derived-file":
        instructions_target = _settings_instruction_path(instructions, root=root)
    else:
        assert instructions.relative_path is not None
        instructions_target = _join_within(
            root,
            instructions.relative_path,
            label="resolved instructions target",
        )
    instructions_materialization = (
        instructions.windows_materialization
        if platform_materialization == "windows"
        else instructions.posix_materialization
    )
    assert instructions_materialization is not None
    shadow_paths = tuple(
        _join_within(root, path, label="resolved instruction shadow path")
        for path in instructions.shadow_paths
    )

    excluded_skill_roots = tuple(
        _join_within(
            _resolve_root(
                spec.root_candidates,
                label=f"excluded skill root {spec.root_id!r}",
                environ=environment,
                user_home=home,
            ),
            spec.relative_path,
            label=f"excluded skill root {spec.root_id!r}",
        )
        for spec in registry.excluded_skill_roots.values()
    )
    if len(set(excluded_skill_roots)) != len(excluded_skill_roots):
        raise HarnessRegistryError("excluded skill roots resolve to duplicate paths")
    if skills_root is not None and skills_root in excluded_skill_roots:
        raise HarnessRegistryError(
            f"harness {harness.harness_id!r} skills root is also excluded: {skills_root}"
        )

    resolved_repo_root = repo_root.resolve(strict=False)
    marketplace_path = (
        _repo_owned_path(
            resolved_repo_root,
            skills.marketplace_path,
            label="resolved marketplace metadata",
        )
        if skills.marketplace_path is not None
        else None
    )
    install_manifest_path = (
        _repo_owned_path(
            resolved_repo_root,
            skills.install_manifest_path,
            label="resolved install manifest",
        )
        if skills.install_manifest_path is not None
        else None
    )
    return HarnessPlan(
        registry_path=registry.path,
        repo_root=resolved_repo_root,
        harness=harness,
        root=root,
        skills_root=skills_root,
        skills_materialization=skills_materialization,
        instructions_source=registry.instructions_source,
        instructions_target=instructions_target,
        instructions_materialization=instructions_materialization,
        instruction_shadow_paths=shadow_paths,
        excluded_skill_roots=excluded_skill_roots,
        marketplace_path=marketplace_path,
        install_manifest_path=install_manifest_path,
    )


def ensure_codex_harness_covers_catalog(
    catalog: SkillCatalog,
    selectors: list[str] | tuple[str, ...],
    *,
    marketplace_name: str,
) -> None:
    selected_names: set[str] = set()
    for selector in selectors:
        name, separator, marketplace = selector.partition("@")
        if not separator or not name or marketplace != marketplace_name:
            raise SystemExit(
                f"Codex harness selector must target {marketplace_name!r}: {selector!r}"
            )
        selected_names.add(name)
    expected_names = set(catalog.plugin_names)
    missing = sorted(expected_names - selected_names)
    extra = sorted(selected_names - expected_names)
    if missing or extra:
        details = []
        if missing:
            details.append("missing skills-bearing plugins: " + ", ".join(missing))
        if extra:
            details.append("selected plugins without canonical skills: " + ", ".join(extra))
        raise SystemExit("Codex harness does not match repository catalog: " + "; ".join(details))

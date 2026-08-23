#!/usr/bin/env python3
"""Build the canonical skill catalog directly from repository source."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by the bootstrap contract
    raise SystemExit(
        "PyYAML is required. Run `python3 scripts/bootstrap_tooling_env.py`, then invoke "
        "this script with the oh-my-harness tooling Python."
    ) from exc


REPO_ROOT = Path(__file__).resolve().parents[1]
_FRONTMATTER = re.compile(
    r"\A---[ \t]*\r?\n(?P<body>.*?)(?:\r?\n)---[ \t]*(?:\r?\n|\Z)",
    re.DOTALL,
)
_CALLABLE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


@dataclass(frozen=True)
class SkillSource:
    plugin: str
    name: str
    path: Path
    directory_name: str


@dataclass(frozen=True)
class SkillCatalog:
    sources: tuple[SkillSource, ...]
    repo_root: Path
    plugins_root: Path

    @property
    def by_name(self) -> dict[str, SkillSource]:
        return {source.name: source for source in self.sources}

    @property
    def plugin_names(self) -> tuple[str, ...]:
        return tuple(sorted({source.plugin for source in self.sources}))


def _resolved_within(path: Path, root: Path, *, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise SystemExit(f"cannot resolve {label}: {path}: {exc}") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise SystemExit(f"{label} escapes repository authority: {path} -> {resolved}") from exc
    return resolved


def skill_frontmatter_name(skill_file: Path) -> str:
    """Return the validated bare catalog skill name from one SKILL.md file."""

    try:
        text = skill_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"cannot read skill file: {skill_file}: {exc}") from exc
    match = _FRONTMATTER.match(text)
    if match is None:
        raise SystemExit(f"skill file has no YAML frontmatter: {skill_file}")
    try:
        payload = yaml.safe_load(match.group("body"))
    except yaml.YAMLError as exc:
        raise SystemExit(f"skill frontmatter is invalid YAML: {skill_file}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"skill frontmatter must be a mapping: {skill_file}")
    name = payload.get("name")
    if not isinstance(name, str) or not name or name != name.strip():
        raise SystemExit(f"skill frontmatter name must be a non-empty trimmed string: {skill_file}")
    if _CALLABLE_NAME.fullmatch(name) is None:
        raise SystemExit(f"skill frontmatter name is not a portable bare catalog skill name: {name!r}: {skill_file}")
    return name


def load_repo_skill_catalog(repo_root: Path = REPO_ROOT) -> SkillCatalog:
    """Return the repository-authoritative skill catalog without marketplace reads."""

    try:
        resolved_repo = repo_root.resolve(strict=True)
    except OSError as exc:
        raise SystemExit(f"cannot resolve repository root: {repo_root}: {exc}") from exc
    plugins_root_path = resolved_repo / "plugins"
    if not plugins_root_path.is_dir():
        raise SystemExit(f"repository plugins directory does not exist: {plugins_root_path}")
    plugins_root = _resolved_within(plugins_root_path, resolved_repo, label="plugins directory")

    sources: list[SkillSource] = []
    for plugin_entry in sorted(plugins_root_path.iterdir(), key=lambda path: path.name):
        if not plugin_entry.is_dir():
            continue
        plugin_root = _resolved_within(plugin_entry, resolved_repo, label="plugin directory")
        skills_path = plugin_entry / "skills"
        if not skills_path.exists():
            continue
        if not skills_path.is_dir():
            raise SystemExit(f"plugin skills path is not a directory: {skills_path}")
        _resolved_within(skills_path, resolved_repo, label="plugin skills directory")

        for skill_entry in sorted(skills_path.iterdir(), key=lambda path: path.name):
            if skill_entry.name.startswith(".") and not skill_entry.is_dir():
                continue
            if not skill_entry.is_dir():
                raise SystemExit(f"malformed plugin skills entry is not a directory: {skill_entry}")
            skill_root = _resolved_within(skill_entry, resolved_repo, label="skill directory")
            skill_file_path = skill_entry / "SKILL.md"
            if not skill_file_path.is_file():
                raise SystemExit(f"malformed plugin skill directory (SKILL.md missing): {skill_entry}")
            skill_file = _resolved_within(skill_file_path, resolved_repo, label="skill file")
            name = skill_frontmatter_name(skill_file)
            sources.append(
                SkillSource(
                    plugin=plugin_root.name,
                    name=name,
                    path=skill_root,
                    directory_name=skill_entry.name,
                )
            )

    if not sources:
        raise SystemExit(f"no repository skills found under {plugins_root_path}/*/skills")

    owners: dict[str, list[SkillSource]] = {}
    for source in sources:
        owners.setdefault(source.name, []).append(source)
    collisions = {name: entries for name, entries in owners.items() if len(entries) > 1}
    if collisions:
        details = "; ".join(
            f"{name}: {', '.join(f'{entry.plugin}/{entry.directory_name}' for entry in entries)}"
            for name, entries in sorted(collisions.items())
        )
        raise SystemExit(f"duplicate catalog skill names in repository source: {details}")

    return SkillCatalog(
        sources=tuple(sorted(sources, key=lambda source: (source.name, source.plugin, source.directory_name))),
        repo_root=resolved_repo,
        plugins_root=plugins_root,
    )

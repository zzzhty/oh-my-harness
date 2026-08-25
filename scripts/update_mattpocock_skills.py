#!/usr/bin/env python3
"""Refresh the repo-local Matt Pocock plugin from an upstream release.

The published upstream skill directories, including their native Codex
``agents/openai.yaml`` metadata, are the content authority. This updater only
flattens the manifest paths into the local plugin layout and regenerates the
repo-owned wrapper metadata around that unchanged skill tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Iterable, Protocol

from plugin_package_identity import (
    require_repository_identity,
    update_repository_identity,
)


UPSTREAM_REPO = "https://github.com/mattpocock/skills.git"
UPSTREAM_MANIFEST = ".claude-plugin/plugin.json"
TARGET_PLUGIN_NAME = "mattpocock-skills"
UPSTREAM_LOCK_NAME = "upstream-lock.json"
UPSTREAM_LOCK_SCHEMA_VERSION = 1
CODEX_ONLY_VERSION_SUFFIX = re.compile(r"\+codex\..*$")
SEMVER_TAG = re.compile(r"^v(?P<version>\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)$")


def _require_yaml() -> Any:
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "PyYAML is required. Run `python3 scripts/bootstrap_tooling_env.py`, then invoke "
            "this updater with `${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python`."
        ) from exc
    return yaml


class Digest(Protocol):
    def update(self, data: bytes, /) -> None: ...

SKILL_WATCHER_ROLES = {
    "ask-matt": "entrypoint",
    "code-review": "specialized",
    "codebase-design": "discipline",
    "diagnosing-bugs": "discipline",
    "domain-modeling": "discipline",
    "grill-me": "wrapper",
    "grill-with-docs": "wrapper",
    "grilling": "discipline",
    "handoff": "specialized",
    "implement": "specialized",
    "improve-codebase-architecture": "wrapper",
    "prototype": "specialized",
    "research": "specialized",
    "resolving-merge-conflicts": "specialized",
    "setup-matt-pocock-skills": "specialized",
    "tdd": "specialized",
    "teach": "specialized",
    "to-questionnaire": "specialized",
    "to-spec": "specialized",
    "to-tickets": "specialized",
    "triage": "specialized",
    "wait-what": "specialized",
    "wayfinder": "specialized",
    "wizard": "specialized",
    "writing-for-agents": "discipline",
}
SKILL_WATCHER_SUPPORTING = {
    "grill-me": ["grilling"],
    "grill-with-docs": ["grilling", "domain-modeling"],
    "implement": ["tdd", "code-review"],
    "improve-codebase-architecture": ["codebase-design"],
    "wayfinder": ["grilling", "domain-modeling", "prototype", "research"],
}
SKILL_WATCHER_ALIASES = {
    "ask-matt": [("ask matt", "phrase", "phrase"), ("which matt pocock skill", "phrase", "phrase")],
    "code-review": [("code review", "phrase", "phrase"), ("review since", "phrase", "phrase")],
    "codebase-design": [("codebase design", "phrase", "phrase"), ("deep modules", "phrase", "phrase")],
    "diagnosing-bugs": [
        ("diagnose", "legacy", "token"),
        ("diagnose this", "phrase", "phrase"),
        ("debug this", "phrase", "phrase"),
    ],
    "domain-modeling": [("domain modeling", "phrase", "phrase"), ("domain model", "phrase", "phrase")],
    "grill-me": [("grill me", "phrase", "phrase")],
    "grill-with-docs": [("grill with docs", "phrase", "phrase")],
    "grilling": [("grilling session", "phrase", "phrase")],
    "handoff": [("handoff document", "phrase", "phrase")],
    "implement": [("implement tickets", "phrase", "phrase"), ("implement spec", "phrase", "phrase")],
    "improve-codebase-architecture": [
        ("improve codebase architecture", "phrase", "phrase"),
        ("improve architecture", "phrase", "phrase"),
        ("architecture review", "phrase", "phrase"),
    ],
    "prototype": [("prototype this", "phrase", "phrase"), ("throwaway prototype", "phrase", "phrase")],
    "research": [("research this", "phrase", "phrase"), ("primary source research", "phrase", "phrase")],
    "resolving-merge-conflicts": [
        ("resolve merge conflicts", "phrase", "phrase"),
        ("resolve rebase conflicts", "phrase", "phrase"),
    ],
    "setup-matt-pocock-skills": [("setup matt pocock skills", "phrase", "phrase")],
    "tdd": [("test-driven", "phrase", "phrase"), ("red-green-refactor", "phrase", "phrase")],
    "teach": [("teach me", "phrase", "phrase")],
    "to-questionnaire": [("to questionnaire", "phrase", "phrase")],
    "to-spec": [
        ("mattpocock-skills:to-prd", "legacy", "phrase"),
        ("to-prd", "legacy", "token"),
        ("to spec", "phrase", "phrase"),
        ("write spec", "phrase", "phrase"),
        ("to prd", "phrase", "phrase"),
        ("write PRD", "phrase", "phrase"),
    ],
    "to-tickets": [
        ("mattpocock-skills:to-issues", "legacy", "phrase"),
        ("to-issues", "legacy", "token"),
        ("to tickets", "phrase", "phrase"),
        ("break into tickets", "phrase", "phrase"),
        ("to issues", "phrase", "phrase"),
        ("break into issues", "phrase", "phrase"),
    ],
    "triage": [("triage issues", "phrase", "phrase")],
    "wait-what": [("wait what", "phrase", "phrase")],
    "wayfinder": [("wayfinding", "phrase", "token"), ("huge foggy effort", "phrase", "phrase")],
    "wizard": [("setup wizard", "phrase", "phrase"), ("interactive wizard", "phrase", "phrase")],
    "writing-for-agents": [
        ("mattpocock-skills:writing-great-skills", "legacy", "phrase"),
        ("writing-great-skills", "legacy", "token"),
        ("write-a-skill", "legacy", "token"),
        ("writing for agents", "phrase", "phrase"),
        ("write a skill", "phrase", "phrase"),
    ],
}

# Watcher uses these only to retain attribution for historical names. They do
# not create callable plugin aliases or alter the upstream skill tree.
SKILL_WATCHER_LEGACY_NAMES = {
    "mattpocock-skills:diagnose": "mattpocock-skills:diagnosing-bugs",
    "mattpocock-skills:to-issues": "mattpocock-skills:to-tickets",
    "mattpocock-skills:to-prd": "mattpocock-skills:to-spec",
    "mattpocock-skills:write-a-skill": "mattpocock-skills:writing-for-agents",
    "mattpocock-skills:writing-great-skills": "mattpocock-skills:writing-for-agents",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def target_plugin_root() -> Path:
    return repo_root() / "plugins" / TARGET_PLUGIN_NAME


def default_sources_dir() -> Path:
    return Path.home() / ".codex" / "sources"


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> str:
    rendered = subprocess.list2cmdline(command) if os.name == "nt" else " ".join(command)
    print("+ " + rendered, flush=True)
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        output = (result.stderr or result.stdout).strip()
        raise SystemExit(f"command failed with exit code {result.returncode}: {output}")
    return result.stdout.strip()


def ensure_inside(path: Path, parent: Path, *, label: str) -> Path:
    resolved = path.resolve()
    resolved_parent = parent.resolve()
    if resolved != resolved_parent and resolved_parent not in resolved.parents:
        raise SystemExit(
            f"{label} is outside expected parent: {resolved} not under {resolved_parent}"
        )
    return resolved


def latest_semver_tag() -> str:
    output = run(["git", "ls-remote", "--tags", UPSTREAM_REPO])
    versions: list[tuple[tuple[int, int, int], str]] = []
    for line in output.splitlines():
        if line.endswith("^{}"):
            continue
        _, ref = line.split("\t", 1)
        tag = ref.rsplit("/", 1)[-1]
        match = SEMVER_TAG.match(tag)
        if match is None:
            continue
        major, minor, patch = match.group("version").split(".", 2)
        patch_number = int(re.match(r"\d+", patch).group(0))  # type: ignore[union-attr]
        versions.append(((int(major), int(minor), patch_number), tag))
    if not versions:
        raise SystemExit(f"no semver tags found in {UPSTREAM_REPO}")
    return sorted(versions)[-1][1]


def clone_upstream(tag: str, sources_dir: Path) -> Path:
    sources_dir.mkdir(parents=True, exist_ok=True)
    base = sources_dir / f"mattpocock-skills-{tag.lstrip('v')}"
    destination = base
    if destination.exists():
        destination = sources_dir / f"{base.name}-{time.strftime('%Y%m%d%H%M%S', time.gmtime())}"
    run(["git", "clone", "--depth", "1", "--branch", tag, UPSTREAM_REPO, str(destination)])
    return destination


def upstream_commit(source_root: Path) -> str:
    return run(["git", "rev-parse", "HEAD"], cwd=source_root)


def version_from_tag(tag: str) -> str:
    match = SEMVER_TAG.match(tag)
    if match is None:
        raise SystemExit(f"expected semver tag like v1.2.3, got {tag!r}")
    return match.group("version")


def load_upstream_manifest(source_root: Path) -> dict[str, object]:
    manifest_path = source_root / UPSTREAM_MANIFEST
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"upstream manifest missing: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"upstream manifest is invalid JSON: {manifest_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"upstream manifest must be a JSON object: {manifest_path}")
    return payload


def load_upstream_skill_paths(source_root: Path) -> list[str]:
    manifest_path = source_root / UPSTREAM_MANIFEST
    skills = load_upstream_manifest(source_root).get("skills")
    if not isinstance(skills, list) or not skills:
        raise SystemExit(f"upstream manifest has no skills list: {manifest_path}")
    paths: list[str] = []
    for item in skills:
        if not isinstance(item, str) or not item.startswith("./skills/"):
            raise SystemExit(f"unexpected upstream skill path in {manifest_path}: {item!r}")
        paths.append(item)
    return paths


def validate_upstream_release(source_root: Path, tag: str) -> None:
    expected_version = version_from_tag(tag)
    actual_version = load_upstream_manifest(source_root).get("version")
    if actual_version != expected_version:
        raise SystemExit(
            "upstream manifest version does not match requested tag: "
            f"expected {expected_version!r}, got {actual_version!r}"
        )


def flattened_skill_names(skill_paths: Iterable[str]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for path in skill_paths:
        name = path.rstrip("/").rsplit("/", 1)[-1]
        if name in seen:
            raise SystemExit(f"duplicate flattened skill name: {name}")
        seen.add(name)
        names.append(name)
    return names


def tree_entries(root: Path) -> dict[Path, tuple[str, bytes | str | None]]:
    entries: dict[Path, tuple[str, bytes | str | None]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_symlink():
            entries[relative] = ("symlink", os.readlink(path))
        elif path.is_file():
            entries[relative] = ("file", path.read_bytes())
        elif path.is_dir():
            entries[relative] = ("directory", None)
    return entries


def update_digest_record(digest: Digest, value: bytes) -> None:
    digest.update(len(value).to_bytes(8, byteorder="big"))
    digest.update(value)


def canonical_digest_payload(payload: bytes) -> bytes:
    """Canonicalize Git's CRLF checkout form for UTF-8 text payloads."""
    if b"\0" in payload:
        return payload
    try:
        payload.decode("utf-8")
    except UnicodeDecodeError:
        return payload
    return payload.replace(b"\r\n", b"\n")


def skill_tree_sha256(skills_root: Path) -> str:
    """Hash case-sensitive POSIX paths and canonical repository payloads."""
    if not skills_root.is_dir():
        raise SystemExit(f"packaged skills directory is missing: {skills_root}")
    digest = hashlib.sha256()
    entries = tree_entries(skills_root)
    for relative in sorted(entries, key=lambda item: item.as_posix()):
        kind, payload = entries[relative]
        update_digest_record(digest, relative.as_posix().encode("utf-8"))
        update_digest_record(digest, kind.encode("ascii"))
        if payload is None:
            payload_bytes = b""
        elif isinstance(payload, str):
            payload_bytes = payload.encode("utf-8")
        else:
            payload_bytes = canonical_digest_payload(payload)
        update_digest_record(digest, payload_bytes)
    return digest.hexdigest()


def upstream_lock_path(plugin_root: Path) -> Path:
    return plugin_root / ".codex-plugin" / UPSTREAM_LOCK_NAME


def write_upstream_lock(
    plugin_root: Path,
    *,
    tag: str,
    commit: str,
    skill_names: Iterable[str],
) -> None:
    version_from_tag(tag)
    if not commit.strip():
        raise SystemExit("upstream commit must be non-empty")
    names = sorted(skill_names)
    payload = {
        "schema_version": UPSTREAM_LOCK_SCHEMA_VERSION,
        "upstream": {
            "repository": UPSTREAM_REPO,
            "tag": tag,
            "commit": commit,
        },
        "published_skills": names,
        "skill_tree_sha256": skill_tree_sha256(plugin_root / "skills"),
    }
    path = upstream_lock_path(plugin_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def upstream_mirror_drift(detail: str) -> SystemExit:
    return SystemExit(
        "Matt upstream mirror drift detected before replacement: "
        f"{detail}. Restore plugins/mattpocock-skills/skills from its recorded upstream "
        "release; do not edit the skill tree or rebaseline upstream-lock.json manually. "
        "Use scripts/update_mattpocock_skills.py for upstream updates."
    )


def validate_upstream_lock(plugin_root: Path) -> dict[str, object]:
    path = upstream_lock_path(plugin_root)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise upstream_mirror_drift(f"upstream lock is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise upstream_mirror_drift(f"upstream lock is invalid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise upstream_mirror_drift(f"upstream lock must be an object: {path}")
    if payload.get("schema_version") != UPSTREAM_LOCK_SCHEMA_VERSION:
        raise upstream_mirror_drift(
            f"unsupported upstream lock schema in {path}: {payload.get('schema_version')!r}",
        )

    upstream = payload.get("upstream")
    if not isinstance(upstream, dict):
        raise upstream_mirror_drift(f"upstream identity is missing from {path}")
    if upstream.get("repository") != UPSTREAM_REPO:
        raise upstream_mirror_drift(
            f"upstream repository does not match {UPSTREAM_REPO}: {path}",
        )
    tag = upstream.get("tag")
    commit = upstream.get("commit")
    if not isinstance(tag, str) or SEMVER_TAG.fullmatch(tag) is None:
        raise upstream_mirror_drift(f"upstream tag is invalid in {path}: {tag!r}")
    if not isinstance(commit, str) or not commit.strip():
        raise upstream_mirror_drift(f"upstream commit is missing from {path}")
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    try:
        plugin_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise upstream_mirror_drift(
            f"local plugin manifest cannot be read: {manifest_path}: {exc}",
        ) from exc
    plugin_version = plugin_manifest.get("version") if isinstance(plugin_manifest, dict) else None
    expected_version = version_from_tag(tag)
    if (
        not isinstance(plugin_version, str)
        or CODEX_ONLY_VERSION_SUFFIX.sub("", plugin_version) != expected_version
    ):
        raise upstream_mirror_drift(
            f"plugin version does not match locked tag {tag}: {plugin_version!r}",
        )

    expected_names = payload.get("published_skills")
    if (
        not isinstance(expected_names, list)
        or not expected_names
        or any(not isinstance(name, str) or not name for name in expected_names)
        or expected_names != sorted(set(expected_names))
    ):
        raise upstream_mirror_drift(f"published skill list is invalid in {path}")
    skills_root = plugin_root / "skills"
    if not skills_root.is_dir():
        raise upstream_mirror_drift(f"packaged skills directory is missing: {skills_root}")
    actual_names = sorted(child.name for child in skills_root.iterdir() if child.is_dir())
    if actual_names != expected_names:
        raise upstream_mirror_drift(
            f"packaged skill set differs from {path}: expected {expected_names}, found {actual_names}",
        )

    expected_digest = payload.get("skill_tree_sha256")
    if not isinstance(expected_digest, str) or re.fullmatch(r"[0-9a-f]{64}", expected_digest) is None:
        raise upstream_mirror_drift(f"skill tree digest is invalid in {path}")
    actual_digest = skill_tree_sha256(skills_root)
    if actual_digest != expected_digest:
        raise upstream_mirror_drift(
            f"skill tree content differs from {path}: expected {expected_digest}, found {actual_digest}",
        )
    return payload


def validate_skill_tree_matches_source(
    source_root: Path,
    skill_paths: list[str],
    plugin_root: Path,
) -> None:
    for upstream_path, name in zip(skill_paths, flattened_skill_names(skill_paths)):
        source_skill = ensure_inside(
            source_root / upstream_path.removeprefix("./"),
            source_root,
            label=f"upstream skill {name}",
        )
        target_skill = plugin_root / "skills" / name
        source_entries = tree_entries(source_skill)
        target_entries = tree_entries(target_skill)
        if source_entries != target_entries:
            differing = sorted(set(source_entries) ^ set(target_entries))
            if not differing:
                differing = sorted(
                    path
                    for path in source_entries
                    if source_entries[path] != target_entries[path]
                )
            preview = ", ".join(str(path) for path in differing[:5]) or "unknown entry"
            raise SystemExit(f"packaged skill differs from upstream: {name}: {preview}")


def replace_skill_tree(
    source_root: Path,
    skill_paths: list[str],
    plugin_root: Path,
) -> list[str]:
    plugin_root = ensure_inside(plugin_root, repo_root(), label="target plugin root")
    skills_root = plugin_root / "skills"
    ensure_inside(skills_root, plugin_root, label="target skills root")
    names = flattened_skill_names(skill_paths)

    if skills_root.exists():
        shutil.rmtree(skills_root)
    skills_root.mkdir(parents=True)

    for upstream_path, name in zip(skill_paths, names):
        source_skill = ensure_inside(
            source_root / upstream_path.removeprefix("./"),
            source_root,
            label=f"upstream skill {name}",
        )
        if not (source_skill / "SKILL.md").is_file():
            raise SystemExit(f"upstream skill is missing SKILL.md: {source_skill}")
        shutil.copytree(source_skill, skills_root / name, symlinks=True)

    validate_skill_tree_matches_source(source_root, skill_paths, plugin_root)
    return names


def update_plugin_manifest(
    plugin_root: Path,
    version: str,
    *,
    preserve_existing_cachebuster: bool = False,
) -> None:
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    current_version = str(manifest.get("version", ""))
    cachebuster = ""
    if preserve_existing_cachebuster:
        match = re.search(r"\+codex\..*$", current_version)
        if match is not None:
            cachebuster = match.group(0)
    manifest.update(
        {
            "name": TARGET_PLUGIN_NAME,
            "version": CODEX_ONLY_VERSION_SUFFIX.sub("", version) + cachebuster,
            "description": "Local Codex package of Matt Pocock's upstream agent skills.",
            "homepage": "https://github.com/mattpocock/skills",
            "repository": "https://github.com/mattpocock/skills",
            "license": "MIT",
            "keywords": ["skills", "engineering", "productivity", "codex"],
            "skills": "./skills/",
        }
    )
    manifest["author"] = {"name": "Matt Pocock"}
    manifest["interface"] = {
        "displayName": "Matt Pocock Skills",
        "shortDescription": "Use Matt Pocock's agent skills in Codex.",
        "longDescription": (
            "Matt Pocock Skills packages the unchanged upstream mattpocock/skills "
            f"v{version} skill tree and its native Codex metadata."
        ),
        "developerName": "Matt Pocock",
        "category": "Productivity",
        "capabilities": ["skills"],
        "defaultPrompt": ["Help me choose the right Matt Pocock skill."],
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_readme(
    plugin_root: Path,
    tag: str,
    commit: str,
    skill_names: list[str],
) -> None:
    skills = "\n".join(f"- `{name}`" for name in sorted(skill_names))
    text = f"""# Matt Pocock Skills

Skill-only local Codex package of Matt Pocock's published skills.

Upstream: https://github.com/mattpocock/skills

Packaged from: `{tag}` (`{commit}`)

## Skills

{skills}

## Upstream Authority

Every directory under `skills/` is copied unchanged from the paths published in
the selected upstream `.claude-plugin/plugin.json`. This includes upstream's
native `agents/openai.yaml` Codex metadata and its dual-harness SKILL.md
frontmatter. The local updater does not generate Codex metadata, rewrite skill
invocations, omit published skills, or patch upstream behavior.

The local-only surfaces are the `.codex-plugin` wrapper, Watcher attribution
metadata, the updater-owned upstream content lock, version/distribution identity, this
README, and the scoped `AGENTS.md`. Never edit `skills/` or manually rebaseline
the lock; validation fails on drift before an upstream update can replace it.

## Updating From Upstream

From the `oh-my-harness` repository root, run:

```bash
python3 scripts/bootstrap_tooling_env.py
"${{OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}}/venv/bin/python" scripts/update_mattpocock_skills.py
```

The updater selects an upstream release, copies its published skills unchanged,
regenerates local wrapper metadata, regenerates the distribution identity, and validates the
upstream-native Codex invocation contract.

This plugin is the source of truth for these third-party skills in this Codex
setup. Do not maintain separate copies under `$CODEX_HOME/skills`.
"""
    (plugin_root / "README.md").write_text(text, encoding="utf-8")


def skill_watcher_aliases(skill_name: str) -> list[dict[str, str]]:
    aliases = [
        {
            "value": f"{TARGET_PLUGIN_NAME}:{skill_name}",
            "kind": "skill_name",
            "match": "phrase",
        }
    ]
    if skill_name != "teach":
        aliases.append({"value": skill_name, "kind": "slug", "match": "token"})
    for value, kind, match in SKILL_WATCHER_ALIASES.get(skill_name, []):
        aliases.append({"value": value, "kind": kind, "match": match})
    return aliases


def load_yaml_object(path: Path, *, label: str) -> dict[str, object]:
    yaml = _require_yaml()
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SystemExit(f"invalid {label}: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} must be a YAML object: {path}")
    return payload


def frontmatter_mapping(text: str, *, label: str) -> dict[str, object]:
    yaml = _require_yaml()
    if not text.startswith("---"):
        raise SystemExit(f"SKILL.md must start with YAML frontmatter: {label}")
    match = re.match(r"^---\r?\n(?P<frontmatter>.*?)\r?\n---(?:\r?\n|$)", text, re.DOTALL)
    if match is None:
        raise SystemExit(f"invalid YAML frontmatter boundaries: {label}")
    try:
        payload = yaml.safe_load(match.group("frontmatter"))
    except yaml.YAMLError as exc:
        raise SystemExit(f"invalid YAML frontmatter in {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"YAML frontmatter must be an object: {label}")
    return payload


def frontmatter_disables_model_invocation(
    frontmatter: dict[str, object],
    *,
    label: str,
) -> bool:
    values = [
        frontmatter[key]
        for key in ("disable-model-invocation", "disable_model_invocation")
        if key in frontmatter
    ]
    if not values:
        return False
    if len(values) > 1 and values[0] != values[1]:
        raise SystemExit(f"conflicting model-invocation flags in {label}")
    value = values[0]
    if not isinstance(value, bool):
        raise SystemExit(f"model-invocation flag must be a boolean in {label}")
    return value


def skill_is_explicit_only(skill_dir: Path) -> bool:
    payload = load_yaml_object(
        skill_dir / "agents" / "openai.yaml",
        label="upstream Codex agent manifest",
    )
    policy = payload.get("policy")
    if policy is None:
        return False
    if not isinstance(policy, dict):
        raise SystemExit(f"Codex policy must be an object: {skill_dir}")
    allow_implicit = policy.get("allow_implicit_invocation")
    if allow_implicit is None:
        return False
    if not isinstance(allow_implicit, bool):
        raise SystemExit(
            "policy.allow_implicit_invocation must be a boolean: "
            f"{skill_dir / 'agents' / 'openai.yaml'}"
        )
    return allow_implicit is False


def validate_native_codex_metadata(plugin_root: Path) -> None:
    skills_root = plugin_root / "skills"
    errors: list[str] = []
    for skill_dir in sorted(path for path in skills_root.iterdir() if path.is_dir()):
        skill_file = skill_dir / "SKILL.md"
        agent_file = skill_dir / "agents" / "openai.yaml"
        if not skill_file.is_file():
            errors.append(f"{skill_dir.name}: missing SKILL.md")
            continue
        if not agent_file.is_file():
            errors.append(f"{skill_dir.name}: missing upstream agents/openai.yaml")
            continue

        try:
            frontmatter = frontmatter_mapping(
                skill_file.read_text(encoding="utf-8"),
                label=str(skill_file),
            )
            payload = load_yaml_object(agent_file, label="upstream Codex agent manifest")
            explicit_in_frontmatter = frontmatter_disables_model_invocation(
                frontmatter,
                label=str(skill_file),
            )
            explicit_in_codex = skill_is_explicit_only(skill_dir)
        except (OSError, SystemExit) as exc:
            errors.append(f"{skill_dir.name}: {exc}")
            continue

        if frontmatter.get("name") != skill_dir.name:
            errors.append(
                f"{skill_dir.name}: frontmatter name is {frontmatter.get('name')!r}"
            )
        description = frontmatter.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(f"{skill_dir.name}: frontmatter description must be non-empty")

        interface = payload.get("interface")
        if not isinstance(interface, dict):
            errors.append(f"{skill_dir.name}: Codex interface must be an object")
        else:
            display_name = interface.get("display_name")
            short_description = interface.get("short_description")
            if not isinstance(display_name, str) or not display_name.strip():
                errors.append(f"{skill_dir.name}: Codex display_name must be non-empty")
            if not isinstance(short_description, str) or not short_description.strip():
                errors.append(f"{skill_dir.name}: Codex short_description must be non-empty")

        if explicit_in_frontmatter != explicit_in_codex:
            errors.append(
                f"{skill_dir.name}: Claude and Codex invocation policies disagree"
            )

    if errors:
        raise SystemExit(
            "upstream native Codex metadata validation failed:\n- "
            + "\n- ".join(errors)
        )


def write_skill_watcher_metadata(plugin_root: Path, skill_names: list[str]) -> None:
    skills: dict[str, dict[str, object]] = {}
    packaged = set(skill_names)
    for name in sorted(skill_names):
        full_name = f"{TARGET_PLUGIN_NAME}:{name}"
        supporting = [
            f"{TARGET_PLUGIN_NAME}:{supporting_name}"
            for supporting_name in SKILL_WATCHER_SUPPORTING.get(name, [])
            if supporting_name in packaged
        ]
        skills[full_name] = {
            "role": SKILL_WATCHER_ROLES.get(name, "specialized"),
            "logical_group": (
                "explicit-workflows"
                if skill_is_explicit_only(plugin_root / "skills" / name)
                else "implicit-primitives"
            ),
            "aliases": skill_watcher_aliases(name),
            "supporting_skills": supporting,
        }
    legacy_names = {
        old: new
        for old, new in SKILL_WATCHER_LEGACY_NAMES.items()
        if new.split(":", 1)[-1] in packaged
    }
    path = plugin_root / ".codex-plugin" / "skill-watcher.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "skills": skills,
                "legacy_names": legacy_names,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def copy_license(source_root: Path, plugin_root: Path) -> None:
    source = source_root / "LICENSE"
    if not source.is_file():
        raise SystemExit(f"upstream license is missing: {source}")
    shutil.copy2(source, plugin_root / "LICENSE")



def validate_plugin_wrapper(plugin_root: Path) -> None:
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid local plugin manifest: {manifest_path}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise SystemExit(f"local plugin manifest must be an object: {manifest_path}")
    expected = {
        "name": TARGET_PLUGIN_NAME,
        "skills": "./skills/",
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise SystemExit(
                f"local plugin manifest field {key!r} must be {value!r}: {manifest_path}"
            )
    version = manifest.get("version")
    if not isinstance(version, str) or not version.strip():
        raise SystemExit(f"local plugin manifest version is missing: {manifest_path}")
    interface = manifest.get("interface")
    if not isinstance(interface, dict):
        raise SystemExit(f"local plugin manifest interface is missing: {manifest_path}")


def git_diff_check(plugin_root: Path) -> None:
    run(
        ["git", "diff", "--check", "--", str(plugin_root.relative_to(repo_root()))],
        cwd=repo_root(),
    )


def validate_package(plugin_root: Path, *, run_git_diff_check: bool = True) -> None:
    validate_plugin_wrapper(plugin_root)
    validate_upstream_lock(plugin_root)
    validate_native_codex_metadata(plugin_root)
    if run_git_diff_check:
        git_diff_check(plugin_root)


def transactional_plugin_paths(plugin_root: Path) -> tuple[Path, Path]:
    token = uuid.uuid4().hex
    parent = plugin_root.parent
    staging_root = parent / f".{plugin_root.name}.staging-{token}"
    backup_root = parent / f".{plugin_root.name}.backup-{token}"
    ensure_inside(staging_root, parent, label="staging plugin root")
    ensure_inside(backup_root, parent, label="backup plugin root")
    return staging_root, backup_root


def sync_from_source(
    source_root: Path,
    *,
    tag: str,
    commit: str,
    update_identity: bool,
    run_validation: bool,
) -> list[str]:
    plugin_root = ensure_inside(
        target_plugin_root(),
        repo_root(),
        label="target plugin root",
    )
    if not plugin_root.is_dir():
        raise SystemExit(f"target plugin root is missing: {plugin_root}")

    validate_upstream_lock(plugin_root)
    validate_upstream_release(source_root, tag)
    skill_paths = load_upstream_skill_paths(source_root)
    staging_root, backup_root = transactional_plugin_paths(plugin_root)
    swapped = False

    try:
        shutil.copytree(plugin_root, staging_root, symlinks=True)
        skill_names = replace_skill_tree(source_root, skill_paths, staging_root)
        copy_license(source_root, staging_root)
        update_plugin_manifest(
            staging_root,
            version_from_tag(tag),
            preserve_existing_cachebuster=True,
        )
        write_readme(staging_root, tag, commit, skill_names)
        validate_native_codex_metadata(staging_root)
        write_skill_watcher_metadata(staging_root, skill_names)
        write_upstream_lock(
            staging_root,
            tag=tag,
            commit=commit,
            skill_names=skill_names,
        )
        validate_upstream_lock(staging_root)
        if run_validation:
            validate_package(staging_root, run_git_diff_check=False)

        plugin_root.rename(backup_root)
        staging_root.rename(plugin_root)
        swapped = True
        if run_validation:
            git_diff_check(plugin_root)
        if update_identity:
            update_repository_identity(repo_root())
    except BaseException:
        if swapped and plugin_root.exists():
            shutil.rmtree(plugin_root)
        if backup_root.exists():
            if plugin_root.exists():
                shutil.rmtree(plugin_root)
            backup_root.rename(plugin_root)
        if staging_root.exists():
            shutil.rmtree(staging_root)
        raise
    else:
        shutil.rmtree(backup_root)

    return skill_names


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh plugins/mattpocock-skills from mattpocock/skills."
    )
    parser.add_argument(
        "--tag",
        default="latest",
        help="Upstream tag to install, or `latest` for the newest vX.Y.Z tag.",
    )
    parser.add_argument(
        "--source-dir",
        help="Use an existing upstream checkout instead of cloning.",
    )
    parser.add_argument(
        "--sources-dir",
        default=str(default_sources_dir()),
        help="Directory used for fresh clones.",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help=(
            "Skip local wrapper and git-diff validation; upstream byte parity and native "
            "Codex metadata invariants still run."
        ),
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the currently packaged plugin without fetching or changing files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.validate_only:
        if args.source_dir or args.tag != "latest":
            raise SystemExit(
                "--validate-only cannot be combined with --source-dir, --tag, or --no-cachebuster"
            )
        validate_package(target_plugin_root())
        require_repository_identity(repo_root())
        print(f"validated {TARGET_PLUGIN_NAME}")
        return

    tag = latest_semver_tag() if args.tag == "latest" else args.tag
    source_root = (
        Path(args.source_dir).resolve()
        if args.source_dir
        else clone_upstream(tag, Path(args.sources_dir))
    )
    commit = upstream_commit(source_root)
    skills = sync_from_source(
        source_root,
        tag=tag,
        commit=commit,
        update_identity=True,
        run_validation=not args.skip_validation,
    )
    print(f"updated {TARGET_PLUGIN_NAME} from {tag} ({commit})")
    print("skills: " + ", ".join(sorted(skills)))


if __name__ == "__main__":
    main()

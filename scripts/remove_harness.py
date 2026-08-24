#!/usr/bin/env python3
"""Remove only resources proven to belong to one oh-my-harness distribution."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from harness_registry import (
    REGISTRY_FILE,
    HarnessRegistryError,
    load_harness_registry,
    resolve_harness_plan,
)
from manager_paths import manager_home, venv_path, venv_python
from repo_skill_catalog import load_repo_skill_catalog
from sync_agents_skills import remove_all_managed_entries
from sync_codex_agents import is_managed as is_managed_agent_support
from sync_harness_instructions import remove_instruction_sync
from refresh_harness import (
    build_env,
    cached_plugin_names,
    configured_marketplace,
    configured_plugin_names,
    default_plugin_names,
    git_remote_source,
    load_install_manifest,
    remove_cached_plugin_dir,
    remove_marketplace_source,
    require_codex_plugin_commands,
    resolve_codex_executable,
    run,
    same_marketplace_source,
    same_path,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _confirm(prompt: str) -> bool:
    try:
        answer = input(f"{prompt} [y/N] ")
    except (EOFError, OSError):
        return False
    return answer.strip() in {"y", "Y", "yes", "YES", "Yes"}


def _remove_codex_agent_support(codex_home: Path, *, dry_run: bool) -> None:
    root = codex_home / "agents"
    if not root.is_dir():
        return
    managed = [
        path
        for path in sorted(root.iterdir(), key=lambda item: item.name)
        if path.is_file() and not path.is_symlink() and is_managed_agent_support(path)
    ]
    for path in managed:
        print(f"{'would remove' if dry_run else 'remove'} managed agent support: {path}")
        if not dry_run:
            path.unlink()


def _remove_watcher_hooks(
    tooling_python: Path,
    *,
    codex_home: Path,
    dry_run: bool,
) -> None:
    hooks = codex_home / "hooks.json"
    if not hooks.exists():
        return
    watcher = REPO_ROOT / "plugins" / "watcher" / "scripts" / "watcher"
    if not tooling_python.is_file():
        raise SystemExit(f"tooling Python does not exist: {tooling_python}")
    if not watcher.is_file():
        raise SystemExit(f"Watcher CLI does not exist: {watcher}")
    command = [
        str(tooling_python),
        str(watcher),
        "skill",
        "uninstall-hook",
        "--target",
        str(hooks),
    ]
    command.append("--dry-run" if dry_run else "--apply")
    run(command, env=os.environ.copy(), dry_run=False)


def _validate_owned_marketplace(codex_home: Path, marketplace_name: str) -> None:
    config = configured_marketplace(codex_home, marketplace_name)
    if config is None:
        return
    source_type = config.get("source_type")
    source = config.get("source")
    if source_type == "local" and source:
        if not same_path(source, REPO_ROOT):
            raise SystemExit(
                "refusing to remove Codex marketplace whose local source is not the "
                f"canonical checkout: {source}"
            )
        return
    if source_type == "git" and source:
        canonical = git_remote_source(REPO_ROOT)
        if canonical is None or not same_marketplace_source(source, canonical):
            raise SystemExit(
                "refusing to remove Codex marketplace whose Git source is not the "
                f"canonical checkout remote: {source}"
            )
        return
    raise SystemExit(
        f"refusing to remove Codex marketplace with unsupported source binding: {marketplace_name}"
    )


def _remove_codex(
    plan,
    *,
    home: Path,
    codex_path: str | None,
    tooling_python: Path,
    dry_run: bool,
) -> None:
    if plan.marketplace_path is None or plan.install_manifest_path is None:
        raise SystemExit("codex harness did not resolve marketplace metadata")
    manifest = load_install_manifest(plan.install_manifest_path)
    marketplace_name = manifest["marketplace"]
    desired_names = set(
        default_plugin_names(
            "install",
            marketplace_name=marketplace_name,
            manifest_file=plan.install_manifest_path,
            marketplace_file=plan.marketplace_path,
        )
    )
    configured = configured_plugin_names(plan.root, marketplace_name)
    cached = cached_plugin_names(plan.root, marketplace_name)
    unknown = sorted((configured | cached) - desired_names)
    if unknown:
        raise SystemExit(
            "refusing Codex removal because the oh-my-harness marketplace contains "
            "unclassified plugin state: " + ", ".join(unknown)
        )
    _validate_owned_marketplace(plan.root, marketplace_name)

    codex = resolve_codex_executable(codex_path, codex_home=plan.root)
    env = build_env(
        codex_home=plan.root,
        tooling_python=tooling_python,
        manager_home=home,
    )
    require_codex_plugin_commands(
        codex,
        env=env,
        require_marketplace=bool(configured_marketplace(plan.root, marketplace_name)),
        require_add=False,
        require_list=False,
        require_remove=bool(configured),
    )

    print(f"Codex removal plan for marketplace `{marketplace_name}`:")
    for name in sorted(configured | cached):
        locations = []
        if name in configured:
            locations.append("config")
        if name in cached:
            locations.append("cache")
        print(f"- {name} ({'+'.join(locations)})")
    if configured_marketplace(plan.root, marketplace_name):
        print(f"- marketplace source {marketplace_name}")

    for name in sorted(configured):
        run(
            [codex, "plugin", "remove", f"{name}@{marketplace_name}"],
            env=env,
            dry_run=dry_run,
        )
    for name in sorted(cached):
        remove_cached_plugin_dir(
            codex_home=plan.root,
            marketplace_name=marketplace_name,
            plugin_name=name,
            dry_run=dry_run,
        )
    if configured_marketplace(plan.root, marketplace_name):
        remove_marketplace_source(
            codex,
            codex_home=plan.root,
            marketplace_name=marketplace_name,
            env=env,
            dry_run=dry_run,
        )
    _remove_codex_agent_support(plan.root, dry_run=dry_run)
    _remove_watcher_hooks(tooling_python, codex_home=plan.root, dry_run=dry_run)


def remove_harness(
    harness: str,
    *,
    registry_path: Path,
    home: Path,
    codex_home: Path | None,
    codex_path: str | None,
    tooling_python: Path,
    dry_run: bool,
    assume_yes: bool,
) -> None:
    environment = dict(os.environ)
    if codex_home is not None:
        environment["CODEX_HOME"] = str(codex_home)
    try:
        registry = load_harness_registry(registry_path, repo_root=REPO_ROOT)
        plan = resolve_harness_plan(
            registry,
            harness,
            repo_root=REPO_ROOT,
            environ=environment,
        )
    except HarnessRegistryError as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Remove oh-my-harness distribution from {plan.harness.display_name}:")
    if plan.skills_root is not None:
        print(f"- managed skill projections under {plan.skills_root}")
    print(f"- managed instructions at {plan.instructions_target}")
    if plan.harness_id == "codex":
        print("- managed Codex marketplace/plugins, Watcher hooks, and agent support")

    if not dry_run and not assume_yes and not _confirm(f"Remove {plan.harness_id} distribution"):
        raise SystemExit(f"{plan.harness_id} removal was not confirmed")

    if plan.harness_id == "codex":
        _remove_codex(
            plan,
            home=home,
            codex_path=codex_path,
            tooling_python=tooling_python,
            dry_run=dry_run,
        )
    else:
        catalog = load_repo_skill_catalog()
        if plan.skills_root is None:
            raise SystemExit(f"harness {plan.harness_id} has no skill projection root")
        remove_all_managed_entries(
            catalog,
            target_root=plan.skills_root,
            dry_run=dry_run,
        )

    remove_instruction_sync(plan, dry_run=dry_run)

    if dry_run:
        print(f"dry-run only; {plan.harness_id} distribution was not removed")
    else:
        print(f"removed oh-my-harness distribution from {plan.harness_id}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", required=True)
    parser.add_argument("--registry", default=str(REGISTRY_FILE))
    parser.add_argument("--home")
    parser.add_argument("--codex-home")
    parser.add_argument("--codex")
    parser.add_argument("--python")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args(argv)

    home = manager_home(args.home).resolve(strict=False)
    tooling_python = (
        Path(args.python).expanduser()
        if args.python
        else venv_python(venv_path(home))
    )
    remove_harness(
        args.harness,
        registry_path=Path(args.registry).expanduser(),
        home=home,
        codex_home=Path(args.codex_home).expanduser() if args.codex_home else None,
        codex_path=args.codex,
        tooling_python=tooling_python,
        dry_run=args.dry_run,
        assume_yes=args.yes,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

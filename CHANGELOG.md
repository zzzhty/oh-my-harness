# Changelog

## Unreleased

- Keep public status, version, check, and doctor read-only and usable while a mutation lock is held; report degraded runtime failures without implicit repair.
- Preserve pure JSON stdout for status/version and move command/bootstrap diagnostics to stderr.
- Avoid creating or modifying manager locks during install, refresh, and remove dry-run previews.
- Cover installed launchers with isolated-home regression tests for JSON, broken runtimes, concurrent locks, and no-write previews.

## 1.0.0 — 2026-08-24

First formal release of `oh-my-harness`.

- Establish one registry-selected distribution across Codex, ZCode, Claude Code, Copilot CLI, Gemini CLI, and OpenCode.
- Provide the manager-owned `~/.oh-my-harness` installation, upgrade, recovery, launcher, and tooling-runtime contracts.
- Package the Watcher, Workflow, and unchanged Matt Pocock skill mirror through the local Codex marketplace.
- Harden interrupted-install recovery against linked manager roots, dirty or remote-drifted checkouts, and revision changes during refresh.
- Introduce content-derived plugin generations and a release-level distribution identity so equal versions cannot silently represent different plugin content.
- Make `omh` the post-bootstrap lifecycle manager with `install`, `refresh`, explicit `refresh --repair`, `remove`, and transactional `update`.
- Add rolling manager/desired/per-harness receipts, a cross-process mutation lock, update journaling and recovery, and manager repair/uninstall flows.
- Move public launchers to a manager-home bootstrap shim so tooling repair and exact checkout reconstruction remain available outside the managed repository.

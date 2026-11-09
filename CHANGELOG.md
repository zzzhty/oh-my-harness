# Changelog

## Unreleased

- Rework the status surface (ADR 0034): without `--skills-root`, `omh status` lists every installed target (home `targets.json` index plus default-root probing, receipts verified live as installed/foreign/other-home/missing), prints a human-readable summary by default and machine JSON with `--json`, and exits 0 only when all targets are clean. Text output is UTF-8 on every platform (Windows pipes previously encoded it in the ANSI codepage). Fixed the CLI program name in help output.
- Add the POSIX `omh` launcher shim (ADR 0033): `install`/`update` write a managed marker-carrying pointer script into `~/.local/bin` (absolute `--bin-dir` override), recording the installing checkout and interpreter. Static pointer only — no state, self-update or manager; unowned `omh` files fail closed with `HARNESS_CONFLICT`, `uninstall` removes an owned shim. Windows keeps the full `python -B -m omh` command.
- Restore global-instructions distribution through the standalone distributor (ADR 0032): `agents/global-instructions.md` is projected as `AGENTS.md` (codex) or `CLAUDE.md` (claude-code) beside the skills root, as an owned managed file with drift detection, journal rollback and uninstall cleanup. Unowned or user-modified instruction files and shadowing `AGENTS.override.md` fail closed with `HARNESS_CONFLICT`; older receipts gain the file on the next update. Historical basis: the v1.0.0 `0b5f4dd` machinery, byte-identical in the internal fork.
- The OMH standalone distributor (`python -m omh`) is the sole distribution channel (ADR 0031).
- CI validates the standalone path end to end through `scripts/check_standalone_distribution.py`.
- Retire the `.omh` archive/lock release path: a release is a tagged source checkout installed from a verified source tree. Published historical archives remain immutable.
- Update README, root authority map, glossary, Codex support notes and plugin READMEs to the single-distributor boundary.

## 1.2.0

- Publish versioned OMH content under a shared export/import contract.
- Retire the Python installer and automatic skill-watcher collector/hooks.
- Preserve 30 skills, four independent maintenance workflows, catalog-only runtime access, and ADR 0027 historical evidence semantics.
- Separate content declarations, immutable locks and installation receipts; imported content does not enable hooks.

## Unreleased

- Prioritize declared, authorized SOP recovery before stopping on recoverable validation failures; keep explicit stops and report-only boundaries, and clarify that failed Goal gates pause dependent steps while authorized current-milestone repairs continue.
- Add an Oh My Pi agent distribution (`oh-my-pi`, input alias `omp`) projecting skills and a managed `AGENTS.md` into the native `~/.omp/agent` directory, sharing `PI_CODING_AGENT_DIR` with `pi-agent` under the existing shared-resource rule.
- Add an explicit OpenClaw skills-only distribution using the existing owned directory projection lifecycle, with state, profile and home overrides and isolated-home regression coverage.
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

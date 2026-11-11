# Changelog

## Unreleased

- Give every standalone validation failure a specific error code instead of the runtime default: `OMH_CONTENT_INVALID` (malformed manifest, composition, packages, skills, or a manifest without `runtimeGroups` — previously `OMH_INVALID` via `KeyError`), `OMH_FILE_INVALID` (unusable or oversized owned files and transaction caps), `OMH_RECEIPT_INVALID` (receipt or recovery-journal validation), `OMH_PATH_INVALID` (path shape and manager/target separation), `OMH_STATE_CHANGED` (target changed between planning and writing) and `OMH_ENVIRONMENT_INVALID` (stream reconfiguration failures, previously `OMH_INVALID`). The documented `HARNESS_*` codes are unchanged; README now lists the full code table.
- Rework the CLI grammar into subcommands (ADR 0035): each command owns its flags (`omh <command> --help` lists exactly what it takes), `--source`/`--home` parse before or after the command, and flag combinations that never applied to a command (`--operation` on `status`, `--offline` on `plan`) are usage errors with exit 2 instead of being silently ignored.
- Make every command readable by default with `--json` for the machine form (ADR 0035): `plan`, `prepare`, `install`, `update`, `uninstall` and `recover` print a one-line human summary; their `--json` shapes are unchanged.
- Note the installed harnesses on stderr when a target command defaults to codex, the home indexes other harnesses, and no codex receipt exists; suppressed under `--json`.
- Report runtime errors as JSON on **stderr** (exit 1) instead of stdout, keeping stdout a parseable result stream for pipes and scripts; usage errors stay argparse text on stderr with exit 2. stdout and stderr are both reconfigured to UTF-8.
- Rework the human `omh status` layout: per-target marks `✓` clean, `!` drift or foreign/missing receipts, `✗` recovery pending with the `omh recover` command to run; healthy targets collapse to one `clean` line instead of repeating "recovery not required", and truncated drift lists point at `omh status --json`.
- Print TTY-gated runtime preparation progress (`[1/2] preparing runtime 'workflow' ...`) to stderr during `prepare`/`install`/`update`.
- Document the whole `omh` CLI surface in `--help`: user-facing description, a per-command list and exit-code semantics; every flag now states its default, absolute-path requirement and which command it applies to.
- Make the README quick start copy-runnable (`cd` into the checkout, real `python3`), document `plan --operation` and `--source`, add concrete `recover` guidance, state the `~/.local/bin` `PATH` prerequisite and multi-target shim removal, list `~/.grok` among probed status roots, and replace the nonexistent `HARNESS_RUNTIME_PROVIDER_REQUIRED` reference with the codes actually reported. Rename the leftover planning section so the file has one `Unreleased` heading.
- Add the `grok` target (Grok Build): skills project into `~/.grok/skills`, global instructions project as `~/.grok/AGENTS.md`, and sibling rule files Grok also scans (`Claude.md`, `AGENT.md`) fail closed as shadows. Status probing covers `~/.grok`.
- Quote the POSIX `omh` shim with `shlex.quote`, so a checkout path that contains quotes, `$()`, or non-ASCII characters is passed to Python literally.
- Create standard-library runtime groups with `venv --without-pip`. Groups with a hashed lock still install with pip. A failed runtime process keeps the stderr and stdout tails instead of discarding them.
- Include runtime group id and `pyvenv.cfg` version in `omh status --json`, matching the human summary (ADR 0034).
- Hold a non-blocking home lock around `targets.json` and `runtime-state.json` updates. The per-target lock stays fail-closed and does not wait.
- Bind installed helpers through one `OMH_SHARED_SCRIPTS` assignment that points at `.omh-support/<package>`.
- Reject goal-sequence links that resolve outside the sequence directory, and report documentation links that resolve outside the repository.
- Rework the status surface (ADR 0034): without `--skills-root`, `omh status` lists every installed target (home `targets.json` index plus default-root probing, receipts verified live as installed/foreign/other-home/missing), prints a human-readable summary by default and machine JSON with `--json`, and exits 0 only when all targets are clean. Text output is UTF-8 on every platform (Windows pipes previously encoded it in the ANSI codepage). Fixed the CLI program name in help output.
- Add the POSIX `omh` launcher shim (ADR 0033): `install`/`update` write a managed marker-carrying pointer script into `~/.local/bin` (absolute `--bin-dir` override), recording the installing checkout and interpreter. Static pointer only — no state, self-update or manager; unowned `omh` files fail closed with `HARNESS_CONFLICT`, `uninstall` removes an owned shim. Windows keeps the full `python -B -m omh` command.
- Restore global-instructions distribution through the standalone distributor (ADR 0032): `agents/global-instructions.md` is projected as `AGENTS.md` (codex) or `CLAUDE.md` (claude-code) beside the skills root, as an owned managed file with drift detection, journal rollback and uninstall cleanup. Unowned or user-modified instruction files and shadowing `AGENTS.override.md` fail closed with `HARNESS_CONFLICT`; older receipts gain the file on the next update. Historical basis: the v1.0.0 `0b5f4dd` machinery.
- The OMH standalone distributor (`python -m omh`) is the sole distribution channel (ADR 0031).
- CI validates the standalone path end to end through `scripts/check_standalone_distribution.py`.
- Retire the `.omh` archive/lock release path: a release is a tagged source checkout installed from a verified source tree. Published historical archives remain immutable.
- Update README, root authority map, glossary, Codex support notes and plugin READMEs to the single-distributor boundary.

## 1.2.0

> **Retracted release.** ADR 0029 records that this 1.2.0 tag, release, and assets were deleted. The bullets below are unchanged historical wording, not a current distribution channel.

- Publish versioned OMH content under a shared export/import contract.
- Retire the Python installer and automatic skill-watcher collector/hooks.
- Preserve 30 skills, four independent maintenance workflows, catalog-only runtime access, and ADR 0027 historical evidence semantics.
- Separate content declarations, immutable locks and installation receipts; imported content does not enable hooks.

## Historical planning notes (pre-rebuild)

> **Not current work.** These notes are leftover planning, kept verbatim. Oh My Pi and OpenClaw are not standalone harness targets. Current distribution is `python -m omh` for `codex` and `claude-code` (ADR 0031).

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

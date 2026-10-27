---
status: accepted
---

# Publish OMH content through ATM

OMH owns versioned skills, script resources, compositions and content releases.
ATM owns installation, target paths, receipts, isolated runtimes and recovery.
The user authorized this transition and retirement of skill-watcher collection.
Do not maintain a second Python installer or require an active `.oh-my-harness`
manager alongside ATM. An OMH-branded installer is deferred; if needed it must
call the same Rust distribution service.

## Contracts and migration inventory

| Surface | Classification and transition |
| --- | --- |
| `content-manifest.json` | New version-1 cross-repository contract: content IDs, internal resources, compositions and runtime requirements only. ATM export creates a separate immutable version lock; neither is an installed receipt. |
| `.agents/harnesses/`, Python lifecycle scripts, `install.sh` / `install.ps1` | Public installation entry points explicitly retired. Their write policy, ownership and recovery are implemented and tested in ATM Rust. Remove current entry points and implementation-specific tests; keep historical ADRs and documented recovery evidence. Existing installations require explicit ATM adoption; no automatic upgrade script is substituted. |
| `plugins/watcher` | Public package transition to `plugins/maintenance` for the four independent callable skills and `runtimes/watcher` for historical reports/audits. This adopts ATM's already shipped split and catalog-only runtime. No collector, automatic hook entry or hook binding remains. |
| `watcher:*`, historical aliases, JSONL/report state, catalog schema 1 | Persisted evidence: preserve names/readers and raw data. Import the report interpretation in ADR 0027 without reintroducing its retired collector. Text mentions, asserted selections, dependencies and execution remain distinct. |
| Native marketplace `oh-my-harness` | Distribution coordinate transitions to the already shipped ATM coordinate `atm-harness`; it does not rename OMH content authorship. ATM adoption removes only proven predecessor ownership. No dual owner or automatic takeover. |
| Plugin byte identities | Keep `sha256-canonical-plugin-tree-v1`; regenerate once after final source edits and owning tests. Existing old version locks/caches remain recovery material. |
| Source instructions, local skill attribution and read-only contracts | Preserve invocation and authorization semantics. `AGENTS.md` routes to content authority; global policy stays in `agents/global-instructions.md`. |
| Historical ADRs, dev evidence and old lifecycle docs | Keep records; mark superseded operational entry points without rewriting their historical instructions as current guidance. |

`atm harness export` is the sole archive writer; `atm harness fetch/import` is the
sole acquisition/validation implementation. The versioned `.omh` archive contains
an allowlisted, bounded payload. It excludes repository installation code and
target policies; remote data cannot specify host paths or execute post-install
scripts. CI pins the ATM Rust revision, runs export, imports into an isolated
cache and tests the resulting distribution. Portable ATM builds may retain this
inactive offline payload beside their binaries without vendoring this repository.

The default composition retains all 30 skills as complete native plugins.
Maintenance skills remain explicit callable workflows; report/audit helpers are
optional Python runtimes. ATM prepares selected groups in its own final-path venvs
using explicit interpreters, never project `.venv` or global Python. Importing or
preparing a runtime cannot enable hooks. The retired collector is unavailable.

The content baseline comes from ATM's shipped maintenance/runtime split plus
OMH e0ce46d's later historical-report semantics. Preserve upstream notices and
attribution, and carry the existing ATM MIT license for transferred code/content.

## Verification and rollback

Keep catalog, plugin validation/identity, workflow/invocation, snapshot-only runtime,
privacy/redaction, report deduplication and historical evidence tests. Collector
normalization/lifecycle tests retire with the collector; historical fixture tests
retain ADR 0027 evidence and outcome guarantees. Old Python installer tests map to
ATM's `distribution_source`, `distribution_adapters`, `distribution_legacy`,
`distribution_service`, `distribution_runtime`, `distribution_hooks`, transaction
recovery and CLI/package tests; these gates remain native on Linux/macOS/Windows.

The content CI retains Python 3.11/3.12 across all three platforms and validates the
actual Rust-exported/imported payload. Rollback means explicitly selecting a prior
locked release through ATM, with its retained receipt/cache and backups. It does
not mean restarting the retired Python owner or enabling hooks. Native client
loading/execution must be reported separately from filesystem and helper checks.

# Distinguish VS Code from Copilot CLI

Status: Accepted
Date: 2026-10-08

## Context and identity inventory

Users who work in VS Code should not have to select a CLI distribution name.
Client identity is not the same as the physical directory for one resource.

- `vscode` is a new public, persisted canonical harness ID, displayed as
  `VS Code (GitHub Copilot)`; it is not an alias of `copilot`.
- `copilot`, its `copilot-cli` alias, existing receipts and legacy migration
  remain unchanged. Historical ADRs retain their original meanings.
- Registry root, skills, and instructions fields retain their existing schema.
  No new resource ledger, refcount state, or schema version is necessary.
- Runtime plans, CLI choices, desired state, receipts, help and lifecycle
  operations consume the registry identity as before.

## Decision

Both clients use `~/.copilot/skills` by default. The installed global
`~/.copilot/copilot-instructions.md` file is for Copilot Agent Host, not a claim
that every VS Code local-agent mode loads it. Local-agent user instructions
remain VS Code profile configuration. Document that qualification beside the
VS Code target. `COPILOT_HOME` continues to override Copilot CLI only; no
unverified VS Code environment-variable contract is introduced.

Sharing is determined per resolved skill root and instruction target, not by
client name or whole-root equality. The removal helper itself consults the
installed desired set and validated receipts. It rejects relevant recorded/current projection-root drift and missing overlapping
consumer receipts before deleting resources. Unrelated consumers do not require
refresh merely to remove another client. Legacy Codex receipts did not honor
`--codex-home`, so their root field is not used as a drift gate; existing Codex
source/ownership validation remains binding. It retains
shared resources, validates the existing changed/unmanaged ownership checks even
when retaining them, and cleans resources when the last consumer is removed.
Receipts are evidence checked against current plans, never trusted deletion paths.
Path comparisons normalize parent aliases and platform case without resolving an
instruction symlink to its source. Existing root safety checks still apply.

The manager removes consumers sequentially, so normal bulk removal and uninstall
naturally clean up on the last consumer. A dry-run-only preview of previously
selected consumers yields the same last-consumer cleanup plan without state
writes. The helper rejects that preview input during actual deletion.

A managed downgrade to a revision lacking `vscode` must fail before switching;
`copilot` is not an equivalent replacement. The existing cross-version identity
resolver enforces this. Remove VS Code explicitly before such a downgrade.

## Future resources

MCP is out of scope. VS Code and Copilot CLI have distinct user configuration
locations, and VS Code profiles matter. Future MCP support must introduce
client-specific resolution rather than reuse `.copilot` as an all-settings root.
Resource sharing must remain explicit and independent of canonical client identity.

## Validation

Tests cover independent identity and override behavior, shared/last-consumer
removal in both orders, root drift, partial resource sharing, path normalization,
legacy alias receipts, missing receipts, changed instructions and unmanaged skills,
dry-run simulation, and unsupported downgrade targets. Existing lifecycle tests
continue to cover state mutation, bulk selection and manager uninstall.

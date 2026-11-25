# Architecture decision index

Start with [README](../../README.md) for behavior and [CONTEXT](../../CONTEXT.md)
for terminology. The numbered ADRs preserve decisions and rationale at the time
they were written; they are not all prerequisites for maintenance.

## Current entry points

| If you need to change or understand… | Start here | Decision rationale, when relevant |
| --- | --- | --- |
| Harness selection, skill or global instruction projection, and drift/conflicts | [Standalone installation](../../README.md#standalone-installation) | [0031](0031-sole-standalone-distribution.md) for the Python projection owner; [0032](0032-standalone-instruction-projection.md) for owned global instructions |
| Launcher, status, and CLI command boundaries | [Standalone installation](../../README.md#standalone-installation) | [0033](0033-standalone-launcher-shim.md), [0034](0034-status-surface-and-target-index.md), [0035](0035-standalone-cli-grammar-and-readable-output.md) |
| Release verification, upgrade, or rollback | [Versions and validation](../../README.md#versions-and-validation), which links the current release and its rollback instructions | [0036](0036-bootstrap-installer-script.md) for managed bootstrap; [0037](0037-venv-seeding-strategy.md) for Python seeding |
| Runtime bindings, target ownership and interrupted writes | [Python helpers](../../README.md#python-helpers), [Standalone installation](../../README.md#standalone-installation) and [owner handoff](../../README.md#migrating-a-previously-managed-installation) | [0030 runtime protocol](0030-independent-distribution-and-shared-runtime.md#runtime-protocol-1) and [transaction rationale](0030-independent-distribution-and-shared-runtime.md#persistent-execution-and-transactions) |
| Content identities and the locally maintained Matt selection | [Versions and validation](../../README.md#versions-and-validation) and [Matt skill guidance](../../plugins/mattpocock-skills/AGENTS.md) | [0009](0009-use-content-derived-plugin-distribution-identities.md) for canonical package hashing; [0012](0012-maintain-a-local-mattpocock-selection.md) for selection ownership |
| Long-running work and native Goal | [long-running-task](../../plugins/workflow/skills/long-running-task/SKILL.md) | [0038](0038-use-native-goals-for-long-running-tasks.md) |

The [Rust manager design](../design/rust-omh-manager.md) is a proposal record,
not an accepted ADR or the operating guide. See the [1.5.0 release record](../releases/1.5.0.md#what-changed)
for its initial source release. The manager delegates projection; it is not the retired export/import core.

## Trace the installation decisions

- Registry-selected distribution and historical Codex marketplace identities:
  [0007](0007-use-one-registry-selected-harness-distribution.md) and
  [0004](0004-accept-native-codex-skill-invocation-identities.md). Neither is the
  current install route.
- Historical archive and lock path: [0028](0028-versioned-content-publishing.md)
  and [0029](0029-pure-hub-with-skill-owned-helpers.md). The published artifacts
  remain historical evidence; use a verified source tag for current installs.
- [0030](0030-independent-distribution-and-shared-runtime.md) recorded dual
  distribution. [0031](0031-sole-standalone-distribution.md) superseded that
  choice without replacing the runtime protocol, receipts, lock or journal.
  [0032](0032-standalone-instruction-projection.md) superseded the skills-only
  portion of 0031, not its projection ownership.
- For why rollback is bounded to owned files and protects edits, start at
  [0030's transaction rationale](0030-independent-distribution-and-shared-runtime.md#persistent-execution-and-transactions).
  For the historical owner cutover, see [its compatibility and rollback notes](0030-independent-distribution-and-shared-runtime.md#identifier-inventory-compatibility-and-rollback)
  and [0031's handover notes](0031-sole-standalone-distribution.md#handover-for-previously-managed-homes).
  To roll back a supported release, use that release's instructions, not commands
  captured in the ADR history.

Other numbered records remain in place and may contain both live and historical
decisions. Omission from this index is not a retirement decision.

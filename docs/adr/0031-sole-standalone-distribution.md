---
status: accepted
---

# Sole standalone distribution

> The skills-only projection boundary is narrowed by [ADR 0032](0032-standalone-instruction-projection.md):
> the standalone distributor also projects the harness global-instructions file.
> Everything else in this decision remains in force.

The previous skills-distribution core, harness CLI verbs, desktop commands and
panels, and the content lock and payload generation are gone. Skills distribution by a GUI
application was the wrong shape; a plain CLI is the right one.

## Decision

OMH's standalone distributor (`python -m omh`, ADR 0030) is the sole
distribution channel. There is no second distributor to keep compatible, and no
Rust export/import core to pin. This concludes the dual-distributor model in
ADR 0030; its runtime protocol, shared owner lock, receipts and journal
contracts remain in force unchanged.

- Content validation belongs to this repository's CI.
  The cross-repository exporter build is replaced by a standalone end-to-end
  check: isolated home, `plan`/`install`/`status`, installed helper execution
  through `.omh-runtime` launchers, idempotent `update`, `uninstall`.
- The `.omh` archive and `omh.lock.json` production path is retired; a
  release is a tagged source checkout,
  and installation always starts from a verified source tree through the
  standalone CLI. Published historical archives remain immutable evidence.
  `scripts/check_standalone_distribution.py` owns the integration check.

## Preserved identities

- The Codex marketplace coordinate is `oh-my-harness`
  (`.agents/plugins/marketplace.json`, `install-manifest.json`). The
  standalone CLI refuses to take over a configured native installation
  without explicit handoff.
- Historical ADRs, release records, the compatibility audit and old CHANGELOG
  entries keep their original wording.

## Handover for previously managed homes

A previously managed home is migrated by owner handoff, not takeover:
uninstall with the previous owner, complete its recovery, verify the target is clean
(no owner receipt, no lingering native plugin configuration), then install with
`python -m omh`. The standalone planner's `HARNESS_OWNER_CONFLICT` protection
is the guardrail for skipped steps.

## Consequences

- README, root authority map, glossary and the Codex support notes describe a
  single distributor; plugin READMEs no longer route release distribution
  through the previous owner.
- No functionality is removed from the standalone CLI, the runtime provider or
  the skills. Packaged-content edits regenerate plugin generations once under
  the existing `sha256-canonical-plugin-tree-v1` authority.
- If a second distributor is ever wanted again, it is a new ADR, not a
  restoration of a previous integration.

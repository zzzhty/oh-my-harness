---
status: accepted
---

# Standalone global-instructions projection

The standalone distributor is the sole distribution channel (ADR 0031).
The harness global-instructions file is part of what a complete
OMH installation means again: it is projected by `python -m omh` itself.

This narrows the skills-only boundary of ADR 0030/0031. It does not change the
runtime protocol, owner lock, receipts or journals, and it does not restore the
retired lifecycle manager, the multi-harness registry, or the
`codex-agent-support` extras projection.

## Historical basis

The last public implementation is `0b5f4dd` (v1.0.0 baseline;
`sync_harness_instructions.py`, registry `instructions` entries, lifecycle
integration and two test modules). The restoration uses the 0b5f4dd semantics
as the reference, re-expressed through the standalone model.

## Decision

- `agents/global-instructions.md` is the single instruction source. `install`
  and `update` project it to the harness-native filename beside the skills
  root: `AGENTS.md` for `codex`, `CLAUDE.md` for `claude-code`.
- The projected file is an ordinary owned managed file in the target receipt:
  it gains drift detection, journal rollback, recovery and uninstall cleanup
  through the existing model, with no parallel ownership mechanism.
- Confirmation semantics are fail-closed instead of interactive: an unowned
  existing instructions file, or a user-modified owned one, fails with
  `HARNESS_CONFLICT` until the user resolves it explicitly. Shadowing files
  (`AGENTS.override.md` for codex) fail the same way at plan time.
- Older receipts without the instructions file are updated in place; the file
  is added on the next `update` and removed by `uninstall`.
- Skills remain self-contained: no skill may assume the presence of global
  instructions or any other installed guidance. The operating-principles
  support note stays uninstalled (it is repository documentation; see
  `docs/codex-agent-support.md`).

Adding another harness target means adding its native filename and shadow list
to the distributor's inline map, with target-resolution tests; it does not
revive a registry.

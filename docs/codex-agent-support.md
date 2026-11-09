# Codex Agent Support

OMH owns the source content for Codex support. The OMH standalone distributor is the sole distribution channel: it installs skills, resources and the harness global-instructions file (`AGENTS.md`, projected from `agents/global-instructions.md` by ADR 0032); it does not install this support file. `agents/global-instructions.md` is the separate harness-global source; root `AGENTS.md` remains repository-local.

## Managed Source And Historical Target

```text
source: agents/operating-principles.md
historical target: $CODEX_HOME/agents/operating-principles.md
```

The repository source is authoritative. An installed target is a historical artifact of the retired projection flow; do not hand-edit or overwrite it, and let its owner's handoff remove it. Do not use retired OMH synchronization scripts.

OMH standalone installs skills, their resources and the projected global instructions; it does not install this support file. A standalone skill must not assume either is present. See [README](../README.md#standalone-installation) and [ADR 0032](adr/0032-standalone-instruction-projection.md) for distribution and runtime ownership. Native client discovery and invocation require separate validation from filesystem projection.

## Current Policy

Custom-agent presets are not installed by this support-file path. The `workflow` plugin's `$orchestrate-subagents` skill uses unique `task_name` assignments whose prompts declare read-only permission or an exact disjoint write scope. Its invocation and delegation authority remain separate.

## Future Custom Agents

The [follow-up plan](todo/subagent-orchestration-follow-up.md) owns the evidence and design requirements for any future custom-agent presets.

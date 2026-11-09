# Codex Agent Support

OMH owns the source content for Codex support; owns its registry-selected projection and installed receipts. `agents/global-instructions.md` is the separate harness-global source; root `AGENTS.md` remains repository-local.

## Managed Source And Target

```text
source: agents/operating-principles.md
target: $CODEX_HOME/agents/operating-principles.md
```

When selects this support file, it projects the source to the target so installed global instructions can refer to it. Edit the repository source, then use the previous owner's explicit plan/apply workflow for an authorized refresh. Inspect the owner's plan and receipt, preserve unrelated files and user changes, and validate the selected projection through that owner. Do not hand-edit managed targets or use retired OMH synchronization scripts.

OMH standalone installs skills and their resources; it does not install global instructions or this support file. A standalone skill must not assume either is present. See [README](../README.md#standalone-installation) and [ADR 0030](adr/0030-independent-distribution-and-shared-runtime.md) for distribution and runtime ownership. Native client discovery and invocation require separate validation from filesystem projection.

## Current Policy

Custom-agent presets are not installed by this support-file path. The `workflow` plugin's `$orchestrate-subagents` skill uses unique `task_name` assignments whose prompts declare read-only permission or an exact disjoint write scope. Its invocation and delegation authority remain separate.

## Future Custom Agents

The [follow-up plan](todo/subagent-orchestration-follow-up.md) owns the evidence and design requirements for any future custom-agent presets.

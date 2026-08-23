# Codex Agent Support

This document explains how `oh-my-harness` manages Codex agent support files.

The repository currently keeps only one managed support file under `agents/`.
That file is copied into `$CODEX_HOME/agents/` so global instructions can refer
to it from any Codex session.

## Managed Source

```text
agents/operating-principles.md
```

## Managed Target

```text
$CODEX_HOME/agents/operating-principles.md
```

Use `scripts/sync_codex_agents.py` to copy repo-managed support files from
`agents/` into the target. The script currently syncs only the managed support
file listed above. Do not hand-edit managed target files; edit the source file
here and sync again.

## Current Policy

The sync script ignores local `agents/*.toml` custom-agent presets today. The
`workflow` plugin's `$orchestrate-subagents` skill uses built-in Codex roles
with task-local assignment labels, so legacy local presets are neither synced
nor installed by this support-file path.

## Future Custom Agents

Future custom agents may be added under `agents/` only after a separate active
plan defines:

- why built-in roles and assignment labels are insufficient
- the ownership model and parent integration boundary
- fallback behavior when a custom agent is unavailable
- sync validation and rollback rules

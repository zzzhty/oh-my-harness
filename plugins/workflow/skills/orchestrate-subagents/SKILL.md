---
name: orchestrate-subagents
description: Use when the user explicitly asks for `$orchestrate-subagents`, subagents, parallel agents, or multi-agent delegation; tool availability and task parallelism alone are not triggers.
---

# Orchestrate Subagents

Use only when the user explicitly asks for this skill, subagents, parallel agents, or multi-agent delegation. Tool availability and task parallelism alone are not triggers.

## Assignment Contract

Choose the minimum useful set of independent assignments. Each assignment uses a unique `task_name` and a self-contained assignment prompt naming:

- the task, bounded scope, relevant context and evidence;
- expected output and stopping condition;
- explicit read-only permission with a ban on edits and commits, or an exact disjoint write scope with shared and forbidden paths identified.

Use natural prose or a short structure as needed; these facts matter, not a fixed prompt shape. For reproduction commands, name any authorized temporary/build outputs even when source is read-only. Implementation assignments preserve concurrent work and stop before edits outside their owned paths.

## Workflow

1. Freeze the parent outcome, required gates, non-goals, and shared artifacts. Use the applicable row of [task patterns](references/task-patterns.md) to choose useful slices; no fixed number of branches or reviewers is required.
2. The parent integrates the returned evidence. A subagent result is not the integrated result. Wait for the selected results before that integration.

## Completion

Account for every selected assignment. Keep write scopes disjoint.

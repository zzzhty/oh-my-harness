---
name: orchestrate-subagents
description: Use when the user explicitly asks for `$orchestrate-subagents`, subagents, parallel agents, or multi-agent delegation; tool availability and task parallelism alone are not triggers.
---

# Orchestrate Subagents

Use this skill only after the user-requested trigger. Delegation and mutation authority come from the active instruction chain or an approved plan; this skill does not expand them.

## Contract

1. Spawn the minimum useful set only when independent work can proceed in parallel.
2. Keep the parent agent responsible for planning, final decisions, integration, cross-slice validation, and the user-facing conclusion.
3. Give each subagent a unique `task_name` plus one self-contained assignment prompt with one primary verb, one bounded scope, one expected output, explicit permission, and one stop condition.
4. Put permission in the assignment prompt: either a read-only scope or an exact disjoint write scope. Naming an assignment never grants mutation authority.
5. Keep shared files, generated artifacts, conflicts and final integration parent-owned. Continue only non-overlapping parent work while subagents run.
6. Wait for the selected agents. Preserve policy-blocked spawning, timeout, missing tools or required context, unsafe overlap, conflicting, incomplete, or missing-evidence results as `partial` or `blocked`; do not silently replace them with assumptions.
7. Treat subagent output as evidence for parent review, not as the final decision or validation result.

## Assignment Contract

Every spawn uses `task_name` as the stable assignment identifier and passes the rest as the assignment prompt (`message` when that is the tool field). Use lowercase letters, digits, and underscores in `task_name`. The prompt is complete only when it has this shape:

```text
task_name: <task_local_identifier>

Assignment prompt:
Task:
<one primary verb, one bounded scope, one expected output>

Context:
<paths, commands, base/head, constraints, relevant facts, and shared artifacts>

Permission:
<read-only scope, or exact disjoint paths the assignment may write; name shared or forbidden paths>

Expected output:
- status: done, partial, or blocked
- findings or implementation summary
- paths inspected or changed
- commands run and results
- evidence for each claim
- blockers and unknowns
- stop-condition outcome

Stop condition:
<exact completion signal or boundary that ends the assignment>

Boundaries:
- Stay inside the declared permission.
- Preserve concurrent and parent-owned work.
- Surface missing tools, evidence, conflicts, and incomplete coverage directly.
```

For an implementation assignment, list every owned path and keep shared files, generated artifacts, integration, and cross-slice validation parent-owned.

## Branch Routing

Select exactly one primary reference before drafting assignments. Choose the branch whose procedure owns the frozen parent task's dominant outcome:

- review a PR, branch, diff, or planned merge: `references/pr-branch-review.md`;
- diagnose a failing command, test, CI run, report, log, or reproducible symptom: `references/debugging-triage.md`;
- plan a feature, migration, refactor, or architecture change before implementation: `references/implementation-planning.md`;
- implement independently writable slices in parallel: `references/parallel-implementation.md`;
- inspect API, schema, serialization, migration, fixture, client, or wire compatibility: `references/api-schema-inspection.md`;
- audit documentation, runbooks, skills, plans, scripts, entry points, or terminology for alignment: `references/documentation-alignment.md`.

Read the primary reference first. Read at most one secondary reference only when the task contains two genuinely independent assignment families: each has a distinct outcome, a non-overlapping scope, and its own stop condition, and each needs a different branch procedure. Supporting concerns inside one assignment family stay with the primary branch. Read at most two branch references in total.

## Workflow

1. Freeze the parent task, success criteria, non-goals, shared artifacts, and parent-owned integration.
2. Select exactly one primary reference from the dominant outcome and read it before drafting assignments.
3. Add one secondary reference only when the frozen task meets the two-independent-family criterion; otherwise keep the primary reference alone.
4. Choose the minimum useful assignments, instantiate the inline Assignment Contract, and spawn with unique `task_name` values and non-overlapping assignment-prompt permissions.
5. Wait for selected results and record each assignment's status, evidence, blockers, unknowns, and stop-condition outcome.
6. Consolidate findings into decisions, risks, validation gaps, conflicts, residual unknowns, and the next parent-owned action.

## Completion

Report `task_name` values and statuses, paths inspected or changed, commands and results, evidence-backed findings, blockers, unknowns, partial coverage, and parent validation. For implementation, also report behavior impact, rollback, and residual risk.

Completion requires that every selected assignment is accounted for, exactly one primary reference was used, any secondary reference is justified by two independent assignment families, write scopes remained disjoint, failures stayed visible, and the parent independently reviewed and integrated the result.

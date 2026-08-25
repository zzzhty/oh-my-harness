---
name: long-running-goal
description: Create, upgrade, execute, resume, evolve, or close a continuation-ready staged goal or strict serial Long-Running Goal Sequence only when the user explicitly requests that lifecycle action or confirms conversion; task size or duration alone is not a trigger.
---

# Long Running Goal

## Trigger And Ready Contract

Use this skill only when the user explicitly requests a long-running goal by name, explicitly requests one of its lifecycle actions, or confirms a proposed conversion into one. A large, long, staged, recurring, multi-milestone, or continuation-sensitive task is not itself a trigger. Use system planning for ordinary complex work; you may suggest `long-running-goal` as an option, then wait for the user's confirmation before creating or converting its contract.

A `Ready` goal records current truth, ordered work, the next milestone, gates, validation and checkpoint evidence, frozen local and external authority, runtime hard stops, close handling, and a reusable continuation prompt. Keep the goal `Draft` while required design, approval, permission, input, or placeholder work remains unresolved.

Use `templates/long_running_goal_template.md` for one goal and `templates/long_running_goal_sequence_template.md` for a strict sequence unless the repository has a stronger local convention. Prefer the user-specified path, then an existing active goal/TODO directory or index, and use `docs/todo/<goal_slug>_long_running_goal_plan.md` only as a fallback. Do not create a parallel planning tree or append `/todo` to a directory that already serves as the goal directory. Templates and readiness checkers own field shape and structural completeness.

Before goal creation or conversion, or before first implementation when the goal lacks a completed marker, apply `components/planning-preflight.md`. Its timeboxed execution-time assessment must report a rough remaining elapsed-time range or a bounded critical-path breakdown, and its explicit task-temporary-cache housekeeping choice is required even when the user skips `grill-with-docs`.

Explicit goal creation may produce a complete `Draft` or `Ready` contract. Keep unresolved design, approval, permission, input, and housekeeping choices visible in a `Draft`; validate that lifecycle with `check_goal_ready.py --allow-draft`. Never invent or infer a missing decision merely to satisfy a checker, and never treat generic no-cleanup or non-destructive language as the user's explicit housekeeping choice.

## Request Supersession

Re-read the newest request before goal work.

- An explicit pause, stop, redirect, or change-scope request overrides every continue case, including same-goal status, evidence, clarification, or progress.
- Continue the active goal for execution, resume, advancement, close, or same-goal status, evidence, clarification, or progress.
- Pause it for unrelated planning, explanation, alignment, skill editing, review-only analysis, Git maintenance, or another bounded task.
- When the request changes the plan, update the goal and current indexes only unless execution is also requested.
- When scope is ambiguous, inspect or answer the bounded request before resuming stale milestone work.

For a paused goal, answer the bounded request without running milestone commands, editing goal evidence, or updating native goal-tool status.

## Branch Routing

Read every reference whose condition matches:

- create or upgrade a goal, or define a Loop-shaped harness: `references/create-and-loop.md`;
- create, authorize, promote, resume, or close `Sequence Child Goals` as a `Long-Running Goal Sequence`: `references/sequence-child-goals.md`;
- perform a production cutover against an authoritative old path: `references/production-cutover.md`;
- execute, resume, continue, advance, evolve, or close a goal: `references/execute-and-close.md`.

Each reference owns its branch detail and completion criterion. The inline `Ready`, supersession, execution-authority, runtime-hard-stop, and goal-tool contracts always apply.

After creating, upgrading, or evolving a goal, update only the current docs that need concise pointers; keep milestone detail in the goal file.

## Execution Authority

Only a `Ready` goal pre-approves its frozen non-destructive local work. A `Draft` goal does not.

Before `Ready`, freeze:

1. allowed local operations needed by the plan;
2. allowed connector, API, issue, PR, CI, automation, hook, messaging, and other external reads or writes;
3. runtime hard stops, rollback, and the explicit task-temporary-cache policy.

Milestone boundaries, reviews, checkpoints, rebuilds, refreshes, dependency restores, code or documentation edits, tests, formatting, link checks, and other planned non-destructive local operations are non-stops. Run them and continue when their gates pass.

Diagnose and fix ordinary failures while the next useful step is clear and in scope. Ask the user only at a runtime hard stop:

- repeated technical impossibility, normally after at least three attempts or three distinct approaches unless the failure is immediately decisive;
- required credentials, files, tools, or source-of-truth inputs are unavailable locally;
- the next step is destructive, irreversible, privacy-sensitive, externally visible, or an unapproved external write;
- evidence contradicts frozen semantics and continuing would change scope or product behavior;
- a required subagent, connector, worktree, or verifier failed and no meaningful in-plan local fallback remains.

Stop only at a runtime hard stop, not at a status checkpoint. Record assumptions, actions, validation, risk, and checkpoint evidence in the goal.

Task temporary cache housekeeping is separate from execution authority. Use only the policy and owner paths recorded by planning preflight; never infer cleanup consent from YOLO scope, a skipped grill, or generic cleanup language.

## Harness Goal Tool Boundary

Use the harness's native goal tools only when the user explicitly asks to create, execute, resume, or close a long-running goal in the active conversation. A planning document alone is not an active harness goal.

Set an active harness goal to the project outcome, set a token budget only when requested, avoid nested active goals, and mark it complete only when no required work remains. Mark it blocked only when the recorded hard-stop threshold is met and no meaningful progress remains.

The goal document, milestone states, validation, commits or equivalent revisions, and final report remain the durable execution authority; native goal status does not replace them.

## Completion

Use the deterministic owners for the affected lifecycle:

```bash
python <skill-folder>/scripts/check_goal_ready.py [--allow-draft] <goal-file>
python <skill-folder>/scripts/check_goal_sequence.py <sequence-file> [--allow-draft]
python <skill-folder>/scripts/check_md_links.py <planning-root>
python <skill-folder>/scripts/check_todo_index.py [--mode active|closed|absent] [--archived-goal <archive-path>] <goal-file> <index-file> [<index-file> ...]
```

Creation or upgrade completes with either a non-executable `Draft` that records known facts and open decisions and passes applicable draft validation, or a `Ready` contract whose planning preflight and every triggered branch criterion pass; current navigation must point to either active contract. Execution advances only after milestone scope, validation, review, rollback, risk, and checkpoint evidence are recorded. Close completes only after all milestones pass, durable current docs are synchronized, the recorded temporary-cache outcome is honored, active navigation is clean, archive or deletion follows local convention, and close evidence is recorded.

Report the goal path, lifecycle state, current or next milestone, triggered branches, authority and hard-stop boundary, evidence and validation, blockers, and residual risk.

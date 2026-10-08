---
name: long-running-goal
description: Create, upgrade, execute, resume, evolve, or close a continuation-ready staged goal or strict serial Long-Running Goal Sequence only when the user explicitly requests that lifecycle action or confirms conversion; task size or duration alone is not a trigger.
---

# Long Running Goal

## Trigger And Ready Contract

Use only for an explicit request naming this skill or one of its lifecycle actions, or a confirmed conversion. Otherwise use system planning; suggesting this skill does not authorize creating its contract.

Only `Ready` pre-approves frozen non-destructive local work; `Draft` does not. Unresolved required design, permissions, input acquisition plans or placeholders keep a goal `Draft`. A fully specified later action may await sourced approval under `components/planning-preflight.md` while earlier authorized milestones proceed. Readiness and action pre-approval do not themselves start execution.

Before creation/conversion, or first implementation without a supported completed marker, apply `components/planning-preflight.md`: required grilling and domain-modeling, sourced decisions, and authorization through Close. Reuse confirmed answers and valid completed preflights; a complete-looking plan cannot skip the workflow. Record completion, reuse or explicit user-skip evidence. `grill-with-docs` remains explicit-only. Estimates are optional; cleanup defaults to `Disabled`, and `Enabled` needs explicit authorization.

## Request Supersession

Read the newest request before goal work. Explicit pause, stop, redirect or scope change overrides every continuation case. Otherwise:

- Continue for execution, resume, advancement, close, or same-goal status, evidence, clarification or progress.
- Pause for unrelated planning, explanation, alignment, skill editing, review-only analysis, Git maintenance or another bounded task.
- A plan-change request updates the goal and current indexes only unless execution is also requested. Resolve ambiguous scope by inspecting or answering the bounded request before resuming stale work.

While paused, answer without milestone commands, goal-evidence edits or native goal-status updates.

## Branch Routing

Read every matching reference, not the whole lifecycle:

- Create/upgrade or define a Loop-shaped harness: `references/create-and-loop.md`.
- Create, authorize, promote, resume or close `Sequence Child Goals`: `references/sequence-child-goals.md` plus the matching lifecycle branch.
- Production cutover against an authoritative old path: `references/production-cutover.md`.
- Execute, resume, continue, advance or evolve: `references/execute-and-close.md`.
- Enter Close: `references/close.md`; do not load it during ordinary execution.

Branches own their detail and completion criteria; inline contracts always apply. After creation, upgrade or evolution, update necessary current-doc pointers and keep milestone detail in the goal file.

## Execution Authority

Before `Ready`, freeze necessary local operations, all external reads/writes (including connectors, APIs, issues, PRs, CI, automation, hooks and messaging), runtime hard stops, rollback and temporary-cache policy. Record approval source, action, target, scope and conditions under the preflight's existing authority owners.

On execution/resume, read those sources and later changes before asking. Still-covered authority survives milestones and context transitions; satisfying an approval condition needs no renewed approval. Ask only for uncovered increments or sourced final-review gates.

Planned non-destructive local operations are non-stops: reviews, checkpoints, rebuilds, refreshes, dependency restores, edits, tests, formatting and link checks. Continue when gates pass. Apply `components/milestone-scope-gate.md` at its defined boundaries; it constrains unplanned expansion, never work frozen by the user, goal, repository, review gate or checkpoint.

After each failure, apply [Failure Recovery](references/execute-and-close.md#failure-recovery) before another attempt: use the evidence to repair the cause or change the strategy within frozen scope and acceptance criteria. When native feedback identifies the first or second Goal failure, make that adjustment immediately; do not spend the remaining native attempts repeating a disproven path. Ordinary test or diagnostic command failures do not establish a native Goal failure count. Ask only at a runtime hard stop:

- The third native Codex Goal failure, when identified by native feedback, or any native hard-stop feedback. Stop active Goal execution even if another useful approach exists; do not initiate a fourth native attempt or recreate the Goal to reset failures.
- Evidence shows no feasible authorized next step, or a required external dependency cannot progress now. Record the blocker and concrete recovery condition; do not wait for an arbitrary number of local failures or loop indefinitely.
- Required credentials, files, tools or source-of-truth inputs cannot be obtained/restored through authorized means and prevent the next required action; local absence alone is a non-stop.
- A destructive, irreversible, privacy-sensitive, externally visible or external-write action needs authorization beyond the frozen contract.
- Evidence contradicts frozen semantics and continuation would change scope or product behavior.
- A required subagent, connector, worktree or verifier failed and no meaningful in-plan local fallback remains.

Authorization problems stop the affected action immediately at any stage; never wait for a failure threshold or route around missing permission. Finish independent authorized work within the current milestone without bypassing gates or advancing past an incomplete milestone. A native hard stop ends active Goal execution; independent work outside that stopped Goal needs its own existing authority. Record failure evidence, strategy changes, recovery conditions, assumptions, validation, risk and checkpoint evidence in the existing goal.

Temporary-cache housekeeping uses only preflight's recorded policy and owner paths. Never infer cleanup consent from YOLO scope, skipped grilling or generic cleanup language.

## Harness Goal Tool Boundary

Use native goal tools only on an explicit active-conversation request to create, execute, resume or close a long-running goal; a planning document alone is not an active native goal. Set the project outcome, add a token budget only if requested, and avoid nested active goals. Complete only when no required work remains; honor native hard stops immediately and use blocked status for actual runtime hard stops, never as a report for every failed command.

The third-failure boundary above is the requested execution constraint. Public documentation has not verified which events the native platform counts or how reset works; this skill and its document validators do not implement platform counting. Use only available native feedback. If the count is unavailable, record it as unknown, improve the next step after every failure, and obey any native stop. Do not infer a count from commands, keep a custom runtime counter, or recreate/replace a Goal to evade a stop or reset its failures. A new user request cannot establish undocumented platform reset semantics.

The goal document, milestone states, validation, commits or equivalent revisions and final report remain the durable authority; native status does not replace them.

## Completion

Use the deterministic owners for the affected lifecycle:

```bash
python <skill-folder>/scripts/check_goal_ready.py [--allow-draft] <goal-file>
python <skill-folder>/scripts/check_goal_sequence.py <sequence-file> [--allow-draft]
python <skill-folder>/scripts/check_md_links.py <planning-root>
python <skill-folder>/scripts/check_todo_index.py [--mode active|closed|absent] [--archived-goal <archive-path>] <goal-file> <index-file> [<index-file> ...]
```

Creation/upgrade follows its Draft/Ready criteria and maintains active navigation. Execution advances only after scope, validation, review, rollback, risk and checkpoint evidence are recorded. Close must satisfy `references/close.md`, including every milestone, docs, temporary-cache disposition, active navigation, archive/delete handling and close evidence.

Report goal path, lifecycle state, current/next milestone, triggered branches, authority and hard-stop boundary, validation evidence, blockers and residual risk.

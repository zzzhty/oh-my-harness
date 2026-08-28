# Long-Running Goal Sequence Template

Copy this template for a strict serial `Long-Running Goal Sequence`. `umbrella` is only an informal alias. Replace every `<...>` placeholder before authorization; never record project progress in this source template.

This two-child shape is the minimum. To add children, add matching rows to both registers, insert one `M<Order> - Child <Child ID>` section per child, renumber Integration Acceptance to `M(n+1)`, and update the milestone table. Do not use this template for parallel or DAG execution.

Overall status: `Draft`

Artifact type: `Long-Running Goal Sequence`

Sequence alias: `umbrella`

Promotion policy: `automatic-after-close`

Goal name: `<Sequence Goal Name>`

Goal owner: `<owner / team / agent>`

Goal path: `<goal-dir>/<sequence_slug>_long_running_goal_sequence.md`

Planning root: `<planning-root>`

Goal directory: `<goal-dir>`

Continuation contract: `<Another agent can re-read this parent, validate both registers, and continue the registered strict-serial state without chat history.>`

Planning preflight marker: `preflight:<sequence_slug>:<yyyymmdd>-<short-id>`

Planning preflight status: `Done`

Preflight source: `grill-with-docs`

Resolved decisions: `<summary or ADR / context paths covering every child boundary and the sequence order>`

Open decisions: `<none or bounded runtime hard stops only>`

Docs written: `<CONTEXT.md / ADR paths / Not applicable with reason>`

## Preflight Time Assessment

Assessment target: `<Ready-to-Closed / current-milestone-to-Closed>`

Assessment mode: `<Rough range / Distribution only>`

Rough elapsed-time estimate: `<low-high with unit / Not quickly estimable>`

Basis or blocker: `<YYYY-MM-DD evidence or blocker, external-wait scope, and serial roll-up assumptions>`

Critical-path time-cost distribution: `<Not required: rough range recorded. / at least two rows shaped: - child or parent driver — Dominant/Material/Minor/Unknown — reason>`

## Task Temporary Cache / Housekeeping

Close housekeeping policy: `<Enabled / Disabled / Not applicable>`

Housekeeping decision source: `<explicit user confirmation with date or turn context>`

Task temporary cache root strategy: `<Enabled/Disabled: resolve the host platform/runtime standard temporary root, allocate a sequence-owned namespace beneath it, and record the exact owner root before first use; Not applicable: no parent task temporary cache root will be created.>`

Recorded task temporary cache roots: `<one fully resolved owner-labeled absolute path entry per parent orchestration/integration root / Resolve and record before first use / None created / Not applicable>`

Housekeeping boundary: `<Enabled uses watcher:housekeeping only for inventoried sequence-owned orchestration/integration disposable candidates; Disabled preserves and reports parent roots; Not applicable creates no parent root; every child records and honors its own policy; durable evidence lives outside the roots.>`

## Template Use

1. Create each child from `long_running_goal_template.md`, complete its own `grill-with-docs` preflight and time assessment, and freeze its scope, owner, compatibility, validation, rollback, permission, release/deploy, privacy, task-temporary-cache housekeeping, and non-goal boundaries.
2. Keep every child overall `Draft` with every atomic row `Not Started / Pending / Pending` until M0 or a predecessor handoff promotes it.
3. Use relative Markdown links. Replace each backticked `Live goal` link example with an actual relative Markdown link when instantiating this template. A Closed row moves its complete atomic child goal from `Live goal` to the `Closeout evidence` archive link; do not replace it with a summary.
4. Run `check_goal_sequence.py --allow-draft` while drafting and without that flag before authorization or execution. Draft mode never relaxes preflight or its time assessment.
5. Create only one active harness system goal for this parent. Never create nested system goals for children.
6. Record a separate parent housekeeping choice only for sequence-owned orchestration/integration caches. Never add housekeeping columns to the child registers or use the parent policy to override a child policy.
7. Apply the timing roll-up in `references/sequence-child-goals.md`; keep the scaffold fields in the parent and linked children, never in either canonical register.

## Child Preflight Register

| Child ID | Marker | Status | Source |
|---|---|---|---|
| `<child-a>` | `preflight:<child-a>:<yyyymmdd>-<short-id>` | `Done` | `grill-with-docs` |
| `<child-b>` | `preflight:<child-b>:<yyyymmdd>-<short-id>` | `Done` | `grill-with-docs` |

Every marker must exactly match the linked child. Missing fields, `:skip:` markers, explicit-skip statuses, and non-`grill-with-docs` sources are forbidden.

## Child Execution Register

| Order | Child ID | Parent milestone | Live goal | Closeout evidence | Depends on | State | Current milestone | Close revision |
|---|---|---|---|---|---|---|---|---|
| 1 | `<child-a>` | `M1` | `[<child-a>](./<child-a>_long_running_goal_plan.md)` | `n/a` | `n/a` | `Draft` | `n/a` | `n/a` |
| 2 | `<child-b>` | `M2` | `[<child-b>](./<child-b>_long_running_goal_plan.md)` | `n/a` | `<child-a>` | `Draft` | `n/a` | `n/a` |

The `Child Execution Register` is the sole current-state authority for child lifecycle and milestone position. Do not add `Current child:`, `Active child:`, or `Current child milestone:` fields elsewhere. Keep transition evidence historical and keep the resume prompt free of copied current child or milestone values.

Allowed `State` values are `Draft`, `Ready`, `In Progress`, and `Closed`. A promoted child records one exact atomic current row such as `M0 Ready`, `M1 In Progress`, or `M1 Blocked`; a Closed child records `Close Done`, `Live goal = n/a`, a relative archived atomic-goal link, and a close revision.

## Baseline And Frozen Boundaries

Current baseline:

1. `<Current code, docs, runtime, and already-delivered capability.>`
2. `<Current compatibility or legacy surface.>`
3. `<Known failure breakpoints and rollback/disable paths.>`

Current sources of truth read:

1. `<Root instructions, README, current indexes, and active planning docs.>`
2. `<Architecture, contract, validation, runtime, release, or permission docs.>`
3. `<Every child goal and relevant prior closeout.>`

Frozen sequence boundaries:

1. `<Child-a scope, owner, compatibility, dependency, permissions, and non-goals.>`
2. `<Child-b scope, owner, compatibility, dependency, permissions, and non-goals.>`
3. Strict child order is fixed by the Execution Register; v1 has no parallel, DAG, per-child authorization, or alternate promotion mode.
4. Parent authorization permits automatic handoff only inside child-frozen boundaries and never expands release, deploy, destructive, privacy-sensitive, external-write, externally visible, or child task-temporary-cache housekeeping permission.
5. Semantic changes to scope, owner, compatibility, dependency order, behavior, or external authorization invalidate affected markers and require `grill-with-docs`; path, command, tool-version, or non-semantic baseline updates only rebaseline evidence.

## Loop Blueprint / Harness

Execution mode: `Loop-shaped execution`

1. Trigger: `<One explicit parent execution authorization, then resume or predecessor Close events.>`
2. Inputs: `<This parent, both registers, linked child goals, source-of-truth docs, validation and checkpoint evidence.>`
3. Triage and orchestration: `<Strict serial selection from the Execution Register; at most one Ready or In Progress child.>`
4. Worktree and isolation: `<Shared-checkout serialization or explicit child-scoped isolation and collision rules.>`
5. Skills and context: `<workflow:long-running-goal, sequence-child-goals.md, child-required skills, runbooks, and specs.>`
6. Connector read/write boundaries: `<Exact child-by-child external read/write permissions; unapproved writes keep the sequence Draft or hard-stop execution.>`
7. Independent verification: `<check_goal_sequence.py plus project-specific tests or reviewer gates.>`
8. Runtime hard stops: `<Only repeated technical impossibility, unavailable facts/credentials, destructive/irreversible/privacy-sensitive/unapproved external action, semantic drift, or required verifier failure with no in-scope next step.>`
9. Durable learning: `<Parent/child evidence, current docs, validation logs, closeouts, and any reusable strategy update.>`

## Pre-Approval / YOLO

1. Pre-approved YOLO local operations: `<Only planned non-destructive local code/docs edits, tests, lint, formatting, rebuilds, refreshes, reinstalls, link checks, plugin/cache refreshes, and project-owned generated-artifact cleanup inside each child boundary; task temporary cache housekeeping remains separately governed.>`
2. Pre-approved external reads/writes: `<Exact union of already-approved child-specific surfaces, or Not applicable; the parent grants no additional permission.>`
3. Runtime hard stops: `<Repeated technical impossibility after local diagnosis, unavailable required facts/credentials, destructive/irreversible/privacy-sensitive/externally visible or unapproved external writes, frozen-semantic conflict, or required verifier failure without an in-plan next step.>`
4. Non-stops: `<M0, child handoff after passed gates, review/checkpoint boundaries, timing rebaseline after a range overrun, evidence recording, rebuild/refresh/reinstall, docs sync, and locally repairable validation failures.>`

## Sequence Execution Contract

1. The parent and every child must retain `Planning preflight status: Done`, exact source `grill-with-docs`, and a marker without `:skip:`. `--allow-draft` relaxes lifecycle only.
2. The Execution Register is the only child current-state source. Closed children form a prefix, at most one child is `Ready` or `In Progress`, and every later child remains `Draft / n/a`.
3. Parent mapping is fixed: Draft child -> `Not Started`; Ready -> `In Progress`; In Progress -> `In Progress`; In Progress with a Blocked atomic milestone -> `Blocked`; Closed -> `Done`.
4. Promotion-drift exception: a parent child stage may be `Blocked` while its child remains `Draft / n/a`, but that exact section must record real section-local runtime hard-stop evidence and no later child may start.
5. In the all-Draft snapshot all parent milestones are Not Started. After every preflight and check passes, set only parent Overall status and M0 to Ready for the one authorization. When M0 starts, set parent Overall status to In Progress and keep it there until Closed; M0 Done promotes the first child, and promoted Ready children map to In Progress parent stages. Each `M<Order>` owns one child. Integration remains Not Started until all children are Closed; Close remains Not Started until integration is Done.
6. After a predecessor Close, verify its archived atomic closeout and revision, parent review/checkpoint and milestone-scope exit gate, next-child preflight/boundaries, handoff inputs, and sequence checker; then promote automatically without another authorization.
7. A child hard stop remains at the owning child. Keep its overall state `In Progress`, mark its atomic current milestone and mapped parent stage `Blocked`, and put `Runtime hard-stop evidence:` in both owning sections with a date, child ID, and breakpoint or attempted diagnostics. Promotion drift additionally names semantic drift/failed handoff and the required re-grill/external decision. Parent-only M0, Integration, or Close evidence uses the same date and diagnostics rule plus the stage owner token `sequence`, `integration`, or `close`. Do not skip or reorder children.
8. Apply `components/checkpoint.md` before every parent milestone or Close becomes Done. Record commands, behavior, docs, rollback, risks, harness evidence, revision, and out-of-scope dirt; after a parent milestone records checkpoint evidence, confirm `components/milestone-scope-gate.md` before marking it Done or promoting the next child.
9. Do not widen gates, hide failure, use fallback or alternate backends, report partial work as success, or convert a permission boundary into a non-stop.
10. Only an explicit `Enabled` policy may invoke `watcher:housekeeping`, and only for inventoried disposable candidates beneath the exact recorded owner root. Do not re-resolve the host temp root at Close or perform unconditional whole-directory deletion. If watcher is unavailable, keep parent Close/overall `In Progress` (`Blocked` only at a runtime hard stop), use no recursive-delete fallback, and change to `Disabled` only through explicit user preflight-policy evolution. Parent and child policies remain independent.
11. Close only after every child is Closed, integration is Done, every parent/child housekeeping disposition is recorded, close evidence passes, current docs are synchronized, and active navigation is clean.

## Transition Evidence

This append-only table records timestamped historical transitions only. Never label a row as the current child or current milestone.

| Timestamp | Child ID | From | To | Predecessor close revision | Handoff gate evidence |
|---|---|---|---|---|---|

Add one row per promoted non-Draft child in child order, use an RFC3339 timestamp, match the predecessor Close revision, and start concrete positive handoff evidence with `Passed:`. Draft children have no transition row in strict v1.

## Milestones

### M0 - Sequence Baseline And First Promotion

Status: `Not Started`

Scope: `<Verify parent/child preflights and boundaries, freeze canonical registers and authorization, then promote child order 1.>`

Review gate:

1. Both registers have matching unique IDs and contiguous order.
2. Parent and every child pass mandatory `Done / grill-with-docs / no-skip` preflight checks.
3. Sequence permissions do not exceed any child boundary, and `check_goal_sequence.py` passes.

Validation evidence: `<commands and actual results>`

Rollback evidence: `<Return first child to Draft only before implementation mutation; otherwise use its frozen rollback contract.>`

Runtime hard-stop evidence: `n/a while this stage is not Blocked`

Checkpoint evidence: `<components/checkpoint.md result, revision, changed files, validation, and excluded dirt>`

### M1 - Child <child-a>

Status: `Not Started`

Scope: `<Execute only the registered live child-a contract through its Close gate.>`

Review gate:

1. Child state, atomic current milestone, and this parent stage remain mapped.
2. Child validation, rollback, review, checkpoint, docs, and Close evidence are complete.
3. Archived atomic closeout, close revision, handoff inputs, and sequence check pass before promotion.

Validation evidence: `<child commands, parent checker, and actual results>`

Rollback evidence: `<Use child-a frozen rollback/disable path without widening scope.>`

Runtime hard-stop evidence: `n/a while this stage is not Blocked`

Checkpoint evidence: `<components/checkpoint.md result, revision, changed files, validation, and excluded dirt>`

### M2 - Child <child-b>

Status: `Not Started`

Scope: `<After automatic promotion, execute only the registered live child-b contract through its Close gate.>`

Review gate:

1. Child-a remains Closed with valid closeout/revision and child-b is the only current child.
2. Child-b validation, rollback, review, checkpoint, docs, and Close evidence are complete.
3. Archived atomic closeout, close revision, integration inputs, and sequence check pass.

Validation evidence: `<child commands, parent checker, and actual results>`

Rollback evidence: `<Use child-b frozen rollback/disable path without widening scope.>`

Runtime hard-stop evidence: `n/a while this stage is not Blocked`

Checkpoint evidence: `<components/checkpoint.md result, revision, changed files, validation, and excluded dirt>`

### M3 - Integration Acceptance

Status: `Not Started`

Scope: `<Validate the composed outcome only after every child is Closed; do not reopen or widen child scope.>`

Review gate:

1. Every child has a valid archived atomic closeout and close revision.
2. Cross-child behavior, compatibility, rollback, docs, and project-specific integration tests pass.
3. The sequence checker passes with Integration Acceptance as the only current parent milestone.

Validation evidence: `<integration commands and actual results>`

Rollback evidence: `<Composed rollback order using only frozen child rollback contracts.>`

Runtime hard-stop evidence: `n/a while this stage is not Blocked`

Checkpoint evidence: `<components/checkpoint.md result, revision, changed files, validation, and excluded dirt>`

## Milestone Status Table

| Milestone | Status | Review | Checkpoint |
|---|---|---|---|
| M0 Sequence Baseline And First Promotion | Not Started | Pending | Pending |
| M1 Child `<child-a>` | Not Started | Pending | Pending |
| M2 Child `<child-b>` | Not Started | Pending | Pending |
| M3 Integration Acceptance | Not Started | Pending | Pending |
| Close | Not Started | Pending | Pending |

## Close Gate

Close remains `Not Started` until M3 is Done. Then set Close and Overall status to `In Progress`, validate, record evidence, and only then set Close to `Done / Passed / Done` and Overall status to `Closed`.

Close requirements:

1. Every child is Closed with a valid archived atomic goal and close revision.
2. M0 through Integration Acceptance are Done/Passed/Done.
3. Final sequence, project-specific, link, and `git diff --check` validations have actual passing results.
4. Current docs, status registers, validation logs, close/archive handling, and active navigation are synchronized.
5. Every non-legacy child has honored its own housekeeping policy, every untouched legacy child has recorded a cleanup-unauthorized no-cleanup disposition, and the parent has handled only its own scope: when no parent root exists, it explicitly records that no task temporary cache roots were created; only for concrete sequence-owned roots does it record exact paths, actions, and removed / preserved / failed / residual sizes, with durable evidence outside those roots.
6. Final rollback, residual risk, harness conclusion, and checkpoint revision are recorded.

Close execution evidence: `<changed artifacts, final behavior, validation commands/results, docs sync, rollback, residual risk, archive outcome, and parent/child task temporary cache dispositions>`

8. Temporary cache / housekeeping evidence:

- Recorded policy: `<Enabled / Disabled / Not applicable>`
- Exact parent roots / Roots outcome: `<repeat each sequence-owned absolute path / None created>`
- Child dispositions: `<each non-legacy child policy or legacy no-cleanup disposition evidence link; never inherit or override it>`
- Action: `<Enabled watcher:housekeeping action / Disabled retained action / no-roots disposition>`
- Removed size: `<concrete parent roots only, for example 0 B>`
- Preserved size: `<concrete parent roots only, for example 0 B>`
- Failed size: `<concrete parent roots only, for example 0 B>`
- Residual size: `<concrete parent roots only, for example 0 B>`

Checkpoint evidence: `<components/checkpoint.md close result, revision, changed files, validation, and excluded dirt>`

## Reusable Resume Prompt

```text placeholder-example
Use workflow:long-running-goal to resume <sequence-goal-path> as a Long-Running Goal Sequence.

Re-read the parent and references/sequence-child-goals.md. Treat Child Execution Register as the sole child current-state authority; do not infer current state from transition history or this prompt. Run check_goal_sequence.py before mutation, follow the registered strict-serial child and parent mapping, promote only after the automatic-after-close handoff gate, keep hard stops at the owning child, preserve every child permission and housekeeping boundary, record checkpoint, transition, and temporary-cache disposition evidence, and close only after all children and integration are complete.
```

## Related Documents

1. `<Current goal/TODO index>`
2. `<Architecture / contract / validation / runtime docs>`
3. `<Child-specific specs, ADRs, and runbooks>`

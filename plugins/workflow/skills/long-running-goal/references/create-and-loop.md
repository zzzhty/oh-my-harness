# Create Or Upgrade And Loop Harness

Use the matching sections after `../SKILL.md` routes a creation, upgrade, or Loop-shaped branch here. The inline `Ready`, pre-approval/YOLO, hard-stop, and goal-tool boundaries remain authoritative.

## Create Or Upgrade

Here, `upgrade` means converting or reshaping an existing TODO, PRD, issue, checklist, or rough plan into a long-running-goal contract. It does not mean ordinary runtime evolution during milestone execution.

1. Read current truth before drafting: root instructions, README/area overviews, active TODO or goal indexes, current guides, status/boundary registers, validation logs, runtime audits, architecture/contract docs, and existing goal/archive docs.
2. Apply `../components/planning-preflight.md` before freezing the goal. Reuse settled decisions and ask only material unresolved questions.
3. Create or reshape the goal file as a continuation contract, preserve useful findings from existing TODOs, and record the planning-preflight marker or skip marker, an optional time estimate, and the task-temporary-cache policy (default `Disabled`).
4. Freeze the contract before implementation:
   - product semantics, owner boundaries, compatibility surface, future/non-goals
   - sequential milestones, usually `M0 Contract Review / Design Freeze`, implementation milestones, docs/release closeout, then `Close`
   - milestone scope, review gate, validation commands, evidence slots, checkpoint expectations
   - execution shape: manual staged execution or Loop-shaped execution
   - pre-approved YOLO local operations, pre-approved external reads/writes, runtime hard stops
   - policy-specific temporary-cache root-or-no-root strategy and `Enabled / Disabled / Not applicable` Close housekeeping policy; `Enabled` records the user's cleanup intent and the `watcher:housekeeping` dependency, not a guarantee that the dependency will still be available at Close
   - Loop harness fields when applicable: trigger, inputs, triage/orchestration, isolation, connector boundaries, independent verifier, durable learning
5. Keep foreseeable approval out of runtime execution. Human approval gates, external-write permission, destructive-action permission, connector permission, permission for planned cleanup, and unresolved design approval must be settled before `Ready`; otherwise keep the goal `Draft`.
6. Add close criteria and a reusable continuation prompt that names the exact goal path and directs the next agent to its frozen authority, required gates, current state, and close handling.

Completion criterion: the goal contains the current baseline, frozen contract, ordered milestones and gates, settled approval boundaries, a task-temporary-cache policy with explicit authorization if `Enabled`, close criteria, reusable prompt, and a completed or explicitly skipped planning-preflight marker; otherwise it remains `Draft`. Legacy goals without the housekeeping section remain compatible but grant no cleanup authorization.

## Loop Blueprint Harness

Do not force automation into small or one-off plans. For manual staged execution, say `Not applicable` with the reason.

When a goal uses recurring triggers, multiple agents, worktrees, connectors, external side effects, or automated triage, make the harness explicit before implementation starts. The plan must answer:

1. Trigger: what starts or resumes the loop.
2. Inputs: which source-of-truth artifacts are read.
3. Triage and orchestration: how findings become scoped tasks and who owns each step.
4. Worktree and isolation: shared checkout, separate worktrees/branches, or serialized edits.
5. Skills and context: mandatory skills, runbooks, docs, specs, or prior decisions.
6. Connector read/write boundaries: readable/mutable systems, pre-approved writes, and writes that keep the goal `Draft` until approved.
7. Independent verification: subagent, script, test, reviewer, or gate that checks producer work without trusting self-evaluation.
8. Runtime hard stops: exact technical breakpoints where execution stops and asks the user.
9. Durable learning: where results are written back, such as a skill, TODO, report, validation log, runbook, automation memory, or current doc.

If the goal claims automation, connector writes, subagent orchestration, worktree parallelism, or any future approval breakpoint but leaves the corresponding harness or pre-approval field unspecified, keep it `Draft`.

Completion criterion: every applicable harness field is explicit, `Not applicable` is reasoned for manual execution, and any unspecified approval-sensitive field keeps the goal `Draft`.

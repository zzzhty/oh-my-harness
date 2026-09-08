# Execute, Checkpoint, Evolve, And Close

Use the matching sections after `../SKILL.md` routes an execute, resume, continue, advance, evolve, or close branch here. The inline supersession, pre-approval/YOLO, runtime-hard-stop, and goal-tool boundaries remain authoritative.

## Execute, Checkpoint, And Evolve

Follow the goal file rather than improvising. After context transition, interruption, or compaction, re-read the newest user request and active goal document before resuming.

Before implementation or resumed work, verify the marker and sourced preflight evidence under `../components/planning-preflight.md`, then run the applicable readiness checker without `--allow-draft`. For Sequence promotion, follow its child-readiness procedure. If evidence is missing, recover it from inspectable sources or complete the affected preflight before implementation. Reuse valid evidence; never manufacture an old interview or approval. Refresh an optional estimate only when changed evidence matters to a decision; missing timing and overruns are not runtime hard stops.

At milestone entry and after context transitions, resolve the action's target, scope and conditions against the recorded authorization sources and the newest request, including withdrawals. Use existing coverage directly; do not ask again because the milestone changed, a checkpoint passed or a condition was satisfied. A tool's access or sandbox permission is not task authorization, and recorded task approval does not override a tool's own execution restrictions.

For an `Enabled` or `Disabled` policy, apply this rule: Before any command may write task-temporary data, resolve the platform/runtime temporary root once, create the recorded goal/sequence-owned child namespace beneath it, replace a deferred roots field with the fully resolved absolute owner path, and bind every task-temporary producer in this goal to that recorded namespace. Reuse the recorded value for the rest of execution and at Close; if no producer ever creates a root, record the runtime outcome `None created` instead. A sequence parent binds only its orchestration/integration producers and never routes child temporary data through the parent root. A `Not applicable` policy creates no root.

At each milestone entry, apply `../components/milestone-scope-gate.md` to derive the current boundary. Reapply it only before material scope or validation expansion and after checkpoint evidence is recorded to confirm the exit condition; do not run it for every ordinary command or edit.

For each milestone:

1. Check any `Deferred approval gates` for this milestone before its work begins. Reconcile the row with sourced actual authorization first; when still covered, record Approved evidence and continue without another question. Otherwise ask only for the reserved final approval or uncovered increment, stop at the gate and record section-local runtime hard-stop evidence. Mark the milestone `In Progress` only after its approval gates pass. Do not remove a user-retained final gate on the strength of generic pre-approval.
2. Apply `../components/milestone-scope-gate.md`, then implement only its recorded scope and necessary consequences.
3. If a gate, validation rule, rollback path, milestone boundary, Loop field, or skill strategy is too weak for observed risk, pause mutation only long enough to update the contract; do not ask for permission unless a runtime hard stop applies.
4. Run the milestone validation commands and complete its review gate.
5. Record scope and necessary-consequence completion, changed files, behavior impact, command results, doc sync, rollback path, and remaining risk.
6. If the milestone exercises a Loop Blueprint, also record trigger/input path, orchestration or worktree isolation evidence, connector read/write evidence, independent verification, YOLO actions, and runtime-hard-stop decisions.
7. Apply `../components/checkpoint.md`.
8. Confirm the milestone-scope exit gate.
9. Mark milestone `Done`, review `Passed`, and checkpoint `Done` only after evidence is recorded.

When both the review gate and milestone-scope exit gate pass, advance to the next milestone and check its approval gates. When a review or scope gate fails, keep fixing and diagnosing in scope while the next useful step is clear; stop only at the runtime-hard-stop boundary.

When execution exposes a weak gate, validation rule, rollback path, milestone boundary, Loop field, or skill strategy, state the gap and evidence, update the active goal within its existing authority, validate the affected contract, and resume the original milestone. Change a reusable skill or template only when source mutation is authorized; otherwise record a bounded improvement suggestion without blocking independent authorized work. If the evolved rule invalidates completed work, reopen affected milestone evidence or mark the gate failed and fix the issue. Do not silently weaken acceptance criteria after implementation, bypass gates with fallback/alternate backends/fake success/hidden partial success/silent degradation, or repackage deprecated surfaces as current semantics unless the goal explicitly requires it and docs are updated.

Use a Git commit as checkpoint evidence only when the project already uses version control and the user or local workflow expects checkpoint commits. Otherwise record an equivalent revision, issue/task history, artifact path, review note, or `Not applicable: no VCS in this workspace`.

Completion criterion: the current milestone has passing scope and review gates plus recorded behavior, docs, rollback, risk, Loop evidence when applicable, validation, review status, and checkpoint evidence before it is marked `Done` or execution advances.

## Current Docs And Close

After creating, upgrading, or evolving a goal, update only the current docs that need concise pointers: active TODO/goal index, development/runtime/status docs, boundary registers, validation logs, or runtime test checklists. Keep detailed milestone plans in the goal file.

When all milestones are done:

1. Apply any deferred approval gate for Close before entering its work. Then mark the Close row `In Progress` and keep the overall goal `In Progress` while preparing close evidence.
2. Fill close execution evidence before removing or archiving the active goal.
3. Sync durable outcomes into current docs, indexes, validation logs, and status/boundary registers.
4. Apply the recorded task-temporary-cache outcome without re-resolving the platform temp root:
   - `None created` or `Not applicable`: record explicitly that no roots were created; do not invoke cleanup or invent size metrics.
   - concrete roots plus `Enabled`: confirm durable evidence is outside the recorded roots, then invoke `watcher:housekeeping` to inventory and clean only confirmed owner-specific disposable candidates. Do not replace it with raw recursive deletion, escalate privileges, cross symlink/junction/reparse-point boundaries, or delete dependencies, runtime state, logs, reports, unknown producers, or locked content. Record the policy, every exact root, the watcher action, and removed, preserved, failed, and residual sizes; safety-preserved residuals do not imply failure unless zero residue was separately confirmed in preflight.
   - concrete roots plus `Disabled`: do not clean; record the policy, every retained exact root, and the retained/preserved action. Size metrics are optional; omit them or record `unknown` with a brief diagnostic when measurement is unavailable. Do not scan retained trees solely to satisfy Close.
   - missing legacy field/section: treat cleanup as unauthorized, preserve any discovered roots, and record the legacy disposition without rerunning the full grill.
   If `watcher:housekeeping` is unavailable for an enabled policy, keep Close and the overall goal `In Progress`, or use `Blocked` only when the normal runtime hard-stop contract is met. Report the missing capability and do not fall back to `rm -rf`, PowerShell recursive deletion, or another raw delete command. Continue as `Disabled` only after the user explicitly evolves the recorded preflight policy.
5. Follow local archive conventions; do not invent dated archive trees or checked-in closed copies just to preserve history.
6. Remove closed goals from active navigation, or archive/delete the goal file according to local convention.
7. Validate index topology with `check_todo_index.py --mode closed --archived-goal <archive-path> <old-active-path> <index>...` after archiving, or `--mode absent <old-active-path> <index>...` after deletion without an archive.
8. Run `git diff --check -- <changed-paths>` and `check_md_links.py` when Markdown links changed.
9. Record close checkpoint evidence. If version control is active and expected, use the local close commit/revision format, such as `<goal_slug> close: <summary>`.
10. Only after every close gate and evidence check passes, set the Close row to `Done/Passed/Done` and the overall goal status to `Closed`.

Completion criterion: every milestone is `Done`, close evidence and validation are recorded, the explicit or legacy task-temporary-cache disposition is recorded, durable current docs are synchronized, active navigation no longer points to closed work, and archive/delete handling follows local convention.

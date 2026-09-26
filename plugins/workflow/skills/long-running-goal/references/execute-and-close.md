# Execute, Checkpoint, And Evolve

Use this reference after `../SKILL.md` routes an execute, resume, continue, advance, or evolve branch here. Load `close.md` only when entering Close. The inline supersession, pre-approval/YOLO, runtime-hard-stop, and goal-tool boundaries remain authoritative.

## Execute, Checkpoint, And Evolve

Follow the goal file rather than improvising. After context transition, interruption, or compaction, re-read the newest user request and active goal document before resuming.

Before implementation or resumed work, verify the marker and sourced preflight evidence under `../components/planning-preflight.md`, then run the applicable readiness checker without `--allow-draft`. For Sequence promotion, follow its child-readiness procedure. If evidence is missing, recover it from inspectable sources or complete the affected preflight before implementation. Reuse valid evidence; never manufacture an old interview or approval. Refresh an optional estimate only when changed evidence matters to a decision; missing timing and overruns are not runtime hard stops.

At milestone entry and after context transitions, resolve the action's target, scope and conditions against the recorded authorization sources and the newest request, including withdrawals. Use existing coverage directly; do not ask again because the milestone changed, a checkpoint passed or a condition was satisfied. A tool's access or sandbox permission is not task authorization, and recorded task approval does not override a tool's own execution restrictions.

For an `Enabled` or `Disabled` policy, apply this rule: Before any command may write task-temporary data, resolve the platform/runtime temporary root once, create the recorded goal/sequence-owned child namespace beneath it, replace a deferred roots field with the fully resolved absolute owner path, and bind every task-temporary producer in this goal to that recorded namespace. Reuse the recorded value for the rest of execution and at Close; if no producer ever creates a root, record the runtime outcome `None created` instead. A sequence parent binds only its orchestration/integration producers and never routes child temporary data through the parent root. A `Not applicable` policy creates no root.

At each milestone entry, apply `../components/milestone-scope-gate.md` to derive the current boundary. Reapply it only before material scope or validation expansion and after checkpoint evidence is recorded to confirm the exit condition; do not run it for every ordinary command or edit.

For each milestone:

1. Check any `Deferred approval gates` for this milestone before its work begins. Reconcile the row with sourced actual authorization first; when still covered, record Approved evidence and continue without another question. Otherwise ask only for the reserved final approval or uncovered increment, stop at the gate and record section-local runtime hard-stop evidence. Mark the milestone `In Progress` only after its approval gates pass. Do not remove a user-retained final gate on the strength of generic pre-approval.
2. Apply `../components/milestone-scope-gate.md`, then implement only its recorded scope and necessary consequences.
3. For an observed weakness in the contract, apply [Contract Evolution](#contract-evolution) before continuing affected mutation.
4. Satisfy the milestone validation commands and complete its review gate. Reuse still-valid passing results under the global verification policy; a checkpoint or skill transition alone does not require rerunning them. Explicit lifecycle fresh-run requirements, including the readiness check above, remain binding.
5. Record scope and necessary-consequence completion, changed files, behavior impact, command results, doc sync, rollback path, and remaining risk.
6. If the milestone exercises a Loop Blueprint, also record trigger/input path, orchestration or worktree isolation evidence, connector read/write evidence, independent verification, YOLO actions, and runtime-hard-stop decisions.
7. Apply `../components/checkpoint.md`.
8. Confirm the milestone-scope exit gate.
9. Mark milestone `Done`, review `Passed`, and checkpoint `Done` only after evidence is recorded.

When both the review gate and milestone-scope exit gate pass, advance to the next milestone and check its approval gates. When a review or scope gate fails, keep fixing and diagnosing in scope while the next useful step is clear; stop only at the runtime-hard-stop boundary.

Completion criterion: the current milestone has passing scope and review gates plus recorded behavior, docs, rollback, risk, Loop evidence when applicable, validation, review status, and checkpoint evidence before it is marked `Done` or execution advances.

## Contract Evolution

When execution exposes a weak gate, validation rule, rollback path, milestone boundary, Loop field, or skill strategy, state the gap and evidence, update the active goal within its existing authority, validate the affected contract, and resume the original milestone. Pause affected mutation for that update; do not ask for permission unless a runtime hard stop applies. Change a reusable skill or template only when source mutation is authorized; otherwise record a bounded improvement suggestion without blocking independent authorized work. If the evolved rule invalidates completed work, reopen affected milestone evidence or mark the gate failed and fix the issue. Do not silently weaken acceptance criteria after implementation, bypass gates with fallback/alternate backends/fake success/hidden partial success/silent degradation, or repackage deprecated surfaces as current semantics unless the goal explicitly requires it and docs are updated.

## Current Docs And Close

Use [close.md](close.md) when entering Close; it owns current-doc synchronization and close completion.

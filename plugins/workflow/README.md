# Workflow

Reusable agent workflow skills maintained from the oh-my-harness repository.

## Skills

- `long-running-goal`: explicitly requested continuation-ready staged goals and strict serial Long-Running Goal Sequences with explicit lifecycle, branch routing, execution authority, runtime hard stops, milestone scope gates, evidence, and close.
- `orchestrate-subagents`: user-requested subagent orchestration using bounded `task_name` assignments, prompt-declared permissions, evidence consolidation, failure handling, and parent-owned integration.
- `prompt-strategy-loop`: evidence-backed prompt and agent-strategy iteration with risk-proportional evaluation and bounded writeback.
- `scope-discipline`: explicit scope-and-evidence discipline that rejects unsupported expansion, keeps necessary consequences, and supplies the shared necessity gate used by long-running-goal milestones.
- `sop`: standard operating procedures for repeatable manual, agent-executed, or automated workflows with explicit trigger, inputs, execution harness, permissions, ordered steps, outputs, validation evidence, allowed/forbidden actions, stop conditions, escalation, failure handling, and durable writeback.
- `summary-in-html`: standalone HTML developer summaries and entry-first source-code walkthroughs for a project, directory, module, feature area, documentation chapter, or user-specified scope, with optional image assets when explicitly requested.

## Shared Vocabulary

- `Continuation contract`: the durable goal file contract that lets the same or another agent continue without chat history.
- `Long-Running Goal Sequence`: the `Sequence Child Goals` branch that gives one parent authorization to a strict serial set of boundary-complete child goals; `umbrella` is only an informal alias.
- `Workflow component`: an internal reusable step used by a skill, such as `long-running-goal` planning preflight or checkpoint evidence, without becoming a standalone user-invoked skill.
- `Necessary consequence`: work not explicitly enumerated but proven by reachable current evidence to be required for the authorized result to remain correct, safe, compliant, or gate-complete.
- `Milestone scope gate`: the `long-running-goal` adapter that applies the shared scope-discipline necessity gate only to material scope or validation expansion, while preserving all work already frozen by the milestone and owner contracts.
- `YOLO non-stops`: planned non-destructive local operations inside a `Ready` long-running goal, such as rebuild, refresh, reinstall, tests, lint, formatting, docs sync, code edits, source skill edits, plugin/cache refresh, and project-owned generated-artifact cleanup. Task temporary cache housekeeping is a separate explicit preflight choice.
- `Task temporary cache root`: a fully resolved goal/sequence-owned namespace created beneath the host platform/runtime-resolved temporary directory, recorded before first use and reused without re-resolution; never the shared system/user temporary root itself. Close cleanup is opt-in and uses bounded housekeeping rather than unconditional whole-directory deletion.
- `Runtime hard stops`: the only post-`Ready` long-running-goal conditions that should pause for the user, such as repeated technical impossibility, missing unavailable credentials or source facts, destructive/irreversible/privacy-sensitive/unapproved external writes, frozen semantic conflict, or required verifier/subagent/connector failure with no in-plan local next step.

# Workflow

Reusable agent workflow skills maintained from the oh-my-harness repository.

## Skills

- `skill-guide`: explicitly choose the smallest useful available skill, or none, after reading that skill's instructions. It does not run the chosen skill. Navigation boundaries adapted from Matt Pocock's `ask-matt` are attributed in [skills/skill-guide/NOTICE.md](skills/skill-guide/NOTICE.md).
- `long-running-task`: explicit long-task workflow with direct execution by default, a brief checkpoint and verification. Native Goal and host-native background are independent opt-ins; subagent orchestration is composed only on request. See [usage and status](skills/long-running-task/SKILL.md).
- `orchestrate-subagents`: user-requested subagent orchestration using bounded `task_name` assignments, stop conditions, and mutually exclusive write scopes. Parallelism alone is not a trigger.
- `prompt-strategy-loop`: evidence-backed prompt and agent-strategy iteration with risk-proportional evaluation and bounded writeback.
- `sop`: standard operating procedures for repeatable manual, agent-executed, or automated workflows with eight core sections: trigger, inputs, execution harness, allowed actions, steps, validation, output contract, and stop conditions. Declared authorized recovery pauses dependent steps until unchanged validation passes; explicit termination, safety and permission stops take priority. Recovery is optional; add further detail only when used.
- `summary-in-html`: standalone HTML developer summaries and entry-first source-code walkthroughs for a project, directory, module, feature area, documentation chapter, or user-specified scope, with optional image assets when explicitly requested.
- `blast-radius`: explicitly find what a change breaks outside the diff, name the one fact its safety depends on, and prove that fact by running code. It is a change-impact procedure, separate from repository-hygiene maintenance.
- `create-verification-skill`: explicitly generate a project-local verification skill in the project's existing skill location, seed a feature map, and prove launch, doctor, drive, evidence, and cleanup once. It asks where to write the skill when the project has no single skill location.

## Long task migration

- Invoke `$long-running-task` to work directly. To use a durable native Goal, explicitly select Goal mode in that same request or use the host’s `/goal` control and tell the skill to use the existing Goal. If the host only allows manual control, invoke it yourself; the skill does not activate `/goal` automatically.
- The old `long-running-goal` skill and its staged templates/checkers are no longer distributed. Existing project plans and native Goal state stay intact. They are not automatically converted or treated as execution authority.
- For an OMH-managed target, preview `omh plan --operation refresh` and then use the normal managed refresh for the selected source. It prunes unchanged OMH-owned legacy files and stops on edited owned files. Manually installed copies and user files outside the receipt are not removed; inspect them separately if the old skill remains visible.
- For rollback, refresh from the previous compatible source through the same owner, after reviewing the plan. Neither refresh nor rollback updates, resumes, or clears a native Goal.

## Helper runtime

`sop` and `summary-in-html` use the `workflow` Python group.
Invoke their helpers through the owner-installed `.omh-runtime/run.sh` (POSIX)
or `run.ps1` (Windows), with the group followed by script path and argv. OMH owns
`scripts/omh_runtime.py` for environment preparation, validation and startup;
the standalone distributor is its only caller and records the target bindings.
Bindings persist across sessions. An explicit absolute `OMH_PYTHON` selects a
validated venv and invalid overrides fail without fallback.

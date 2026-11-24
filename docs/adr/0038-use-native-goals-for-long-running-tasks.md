# ADR 0038: Use native Goals for long-running tasks

Status: Accepted.

## Decision

Maintain one OMH long-task skill, [`long-running-task`](../../plugins/workflow/skills/long-running-task/SKILL.md). It defaults to direct work with a short checkpoint and a verifiable outcome. Use it with the host’s native `/goal` only when the user explicitly selects a Goal. The host owns the Goal lifecycle, state, continuation, budgets and stops; OMH has no separate Goal planner, state machine, retry counter or scheduler. Detached background execution and multi-agent delegation are distinct opt-ins.

A brief or old project plan is evidence, not execution authority. A status-only request reads and reports the identified task or Goal without advancing or mutating it; an already active Goal may continue independently under host policy. Explicit instructions, current permissions and host denials still apply. Leave detailed operating procedures in the skill, not in a second instruction owner.

## Compatibility

This decision replaces the former OMH-managed staged Goal workflow and supersedes ADRs 0013, 0014 and 0019. The retired skill, templates and checkers are no longer distributed. The [managed migration and rollback instructions](../../plugins/workflow/README.md#long-task-migration) distinguish OMH-owned files from manually installed copies. No upgrade automatically converts project documents, modifies native Goal state, or carries over execution authority.

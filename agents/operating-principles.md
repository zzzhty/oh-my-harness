# Agent Operating Principles — Repository Map

This is the repository-managed support note installed at `$CODEX_HOME/agents/operating-principles.md` when selected by the installation owner. `agents/global-instructions.md` owns global authority, safety, failure handling, verification, delegation, and subagent-failure policy. Root `AGENTS.md` owns only `oh-my-harness` repository routing and deltas. This file maps those owners to reusable workflow surfaces; it does not expand their authority.

## Managed Source And Target

```text
source: agents/operating-principles.md
target: $CODEX_HOME/agents/operating-principles.md
```

Edit the repository source, not the installed target. owns its registry-selected instruction/support projection and installed receipts. OMH standalone installs skills and resources, not global instructions or this support note. Use the installation owner's explicit plan/apply workflow; preserve unrelated files and user edits. See `README.md` and `docs/adr/0030-independent-distribution-and-shared-runtime.md` for the current ownership contract.

## Durable Owner Map

| Concern | Repository owner |
| --- | --- |
| Global agent behavior, mutation boundaries, failure handling, test policy, and delegation authority | `agents/global-instructions.md` |
| Repository-local routing and conditional guidance | root `AGENTS.md` |
| Installed Codex support paths and assignment mapping | this file |
| Reusable workflow behavior | `plugins/*/skills/*/SKILL.md` and the skill's direct references |
| Plugin/runtime architecture and commands | the owning plugin `README.md`, scripts, and validators |
| Active multi-turn work | `docs/todo/README.md` and the named active plan or goal |
| Generated reports or automation memory | the owning tool's documented report or memory root |

Choose the narrowest owner that future agents can inspect. Do not duplicate a global rule in a skill or support note merely to make it more visible; point to the owner and state only the local workflow delta.

## Delegation Routing

Keep capability, authority, and workflow invocation separate:

- The harness exposes subagent capability.
- `agents/global-instructions.md` or an active plan authorizes delegation and write scope.
- `$orchestrate-subagents` defines the detailed workflow only after the user explicitly requests that skill, subagents, parallel agents, or multi-agent delegation.
- Broad read-only review authorization comes from `agents/global-instructions.md`; it does not invoke `$orchestrate-subagents` by itself.

For an invoked orchestration workflow, read:

```text
plugins/workflow/skills/orchestrate-subagents/SKILL.md
```

The skill owns branch routing, slicing, assignment contracts, disjoint write ownership, waiting, partial coverage, and consolidation. `agents/global-instructions.md` remains the authority for whether delegation or mutation is allowed and for how failures affect integration.

Assignments inherit the active delegation authority. The invoked orchestration skill owns prompt contents and write isolation; `task_name` is an assignment identifier, not a role or permission.

Custom-agent presets are not installed. Future requirements belong in `docs/todo/subagent-orchestration-follow-up.md` in the source repository.

## Scheduling And Monitoring Boundary

Scheduled or repeated workflows must define the trigger or schedule, exact command or tool, working directory, inputs and output contract, allowed and forbidden actions, report or memory location, validation or freshness checks, and stop condition. For `long-running-goal`, use its narrower runtime hard-stop boundary.

For wall-clock schedules, preserve the user-visible local time unless the user explicitly requests UTC, and verify the written automation state before reporting the schedule.

## Memory Writeback Boundary

Write back only durable, reusable knowledge: user preferences that affect future work, validated commands, recurring failure modes, workflow contracts, open loops or close criteria, and privacy or mutation boundaries. Do not write secrets, full private prompts, full tool responses, unverified assumptions, one-off noise, or implementation details that are cheap to rediscover.

Memory updates must remain reviewable through file paths, diffs, or report artifacts.

## Distribution And Validation

For an previously managed installation, inspect the owner's current plan and receipt before an authorized refresh, then validate the selected support projection through that owner. Do not invoke a retired OMH sync script or overwrite an unmanaged target. `$CODEX_HOME` defaults to `~/.codex` for the target shown above.

Standalone skill execution must remain self-contained: do not make a skill depend on this note being installed. Native Codex discovery and invocation remain separate acceptance checks from filesystem projection.

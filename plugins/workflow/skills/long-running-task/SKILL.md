---
name: long-running-task
description: Run explicitly requested long-running tasks with a brief checkpoint and verifiable outcome. Default to direct execution. Native Goal, detached background execution and multi-agent orchestration are separate opt-ins.
disable-model-invocation: true
---

# Long-Running Task

Use only when the user explicitly requests this workflow. Ordinary complex work uses system planning. Read the newest request before acting; pause, stop, or changed scope overrides an older brief or approval. A status-only request never starts, resumes, or changes work.

## Route The Request

- **Direct (default):** Work in this conversation with the host's normal tools. Use a brief checkpoint; do not create a Goal, detach, or invoke orchestration because of task length, a deadline, or tool availability.
- **Native Goal (explicit):** If the user requests a native Goal or confirms conversion, read and follow `workflow:long-running-goal` for the requested lifecycle action. Its preflight, Draft/Ready distinction, explicit execution and hard stops own this route. Do not treat the task brief as a Ready goal or create a duplicate goal. A native Goal is not a background request.
- **Background (explicit):** If the user asks to continue out of turn, use only an authorized host-native detached task facility. Read [host handoff and status](references/host-handoff.md) before dispatch or status checks. If detached execution is unsupported, say so; don't claim the work will continue, manufacture a substitute, or silently switch modes.
- **Multi-agent (explicit):** When the user also explicitly requests subagents, parallel agents, or multi-agent delegation, compose `workflow:orchestrate-subagents` in the selected route. Read its actual instructions and [host handoff and status](references/host-handoff.md) for worker dispatch and progress. Give read-only workers no write authority; give write workers only exact, disjoint paths within authorized scope. Background or Goal approval does not itself request orchestration. If a requested combination isn't supported, surface the missing capability rather than quietly dropping it or creating competing owners.

## Brief And Checkpoint

Reuse the existing durable task owner when available. For direct or background work needing cross-turn recovery, keep one brief in an authorized task record, not a second plan or a hidden state store. Record only:

- outcome, exact target and scope (including consequential exclusions);
- expected artifact or result and verification;
- current state, checkpoint or host reference, and next step or blocker.

Read [scope and authority](references/scope-authority.md) before a permission-sensitive action, worker handoff, or resuming checkpointed work.

Update on meaningful state changes; preserve already sourced decisions. The brief is evidence, not an authorization surface. Ask only for an unresolved decision that blocks the next affected action. Never grant writes, publication, access changes, or cleanup based on the brief, a tool's presence, or stale consent.

## Close

Verify the requested artifact or outcome and its acceptance checks before calling the task complete. For a host run, also verify the host's terminal outcome or exit status. Report the verified result and anything still unverified; a dispatch receipt, worker summary, or successful process by itself is not completion.

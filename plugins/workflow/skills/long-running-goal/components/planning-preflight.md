# Planning Preflight

Before creating or converting a long-running goal, or first implementing one without a completed marker, verify its scope, owner boundaries, non-goals, compatibility, validation, rollback, milestone order, and action permissions.

## Reuse Decisions First

Read the active request, existing decisions, and source evidence. Reuse answers already settled; ask only material questions whose answers are needed for `Ready`. Run `grilling` / `domain-modeling` when the user requests that interview or unresolved design actually benefits from it. Do not force an interview or new glossary/ADR for a complete plan.

A completed marker prevents repeated preflight. Revalidate only the affected decisions when scope, ownership, product semantics, order, or authorization changes enough to invalidate them. Ordinary path, command, baseline, or estimate updates do not invalidate the marker.

## Record The Result

Record these fields in the goal:

```text
Planning preflight marker: preflight:<goal_slug>:<yyyymmdd>-<short-id>
Planning preflight status: Done
Preflight source: existing decisions / grill-with-docs
Resolved decisions: <concrete summary or source paths>
Open decisions: <none or declared runtime hard stops>
Docs written: <paths when needed / Not applicable>
```

`Done` means the plan's required decisions were verified, not that a particular interview ran. When the user explicitly skips the interview, use a `preflight:<goal_slug>:skip:<yyyymmdd>-<short-id>` marker, status `Skipped by explicit user instruction`, and source `user skip (<date or turn context>)`. Do not infer skip from urgency. Skip never supplies missing authority or turns unresolved required design into `Ready`.

## Optional Time Assessment

Estimate only when useful for a planning or scheduling decision. Use evidence already gathered plus at most one bounded inspection; do not launch builds, benchmarks, installs, CI waits, or external reads solely to estimate time.

A short `Preflight Time Assessment` section may give a rough remaining wall-clock range and its basis, including external waits and serial/parallel assumptions. If unknown, state the concrete reason; no distribution, fixed sentinel, or driver count is required. Estimates do not determine readiness and are not SLAs. Refresh only when the user asks or changed evidence affects a decision; an overrun alone is a non-stop. Sequence estimates must distinguish known child costs from unknown ones rather than imply a complete total.

## Task Temporary Cache / Housekeeping

Default to `Disabled`: retain task-owned temporary roots at Close. Do not ask the user merely to confirm this default. Use `Not applicable` when the plan creates no task temporary cache roots. Use `Enabled` only with explicit user authorization for the recorded cleanup scope; the goal remains `Draft` if its planned cleanup needs missing permission.

An existing `Enabled` contract remains in force; the default cannot silently replace it. A goal without this section grants no cleanup permission.

When recording a policy, include:

```text
Close housekeeping policy: Disabled
Task temporary cache root strategy: <owner-specific platform/runtime-resolved namespace, or no-root strategy>
Recorded task temporary cache roots: <owner-labeled absolute paths / Resolve and record before first use / None created / Not applicable>
Housekeeping boundary: <retention or authorized bounded cleanup and preservation rules>
```

Only `Enabled` additionally requires `Housekeeping decision source` with the user's explicit confirmation and date or turn context.

For `Enabled` or `Disabled`, before a producer writes temporary data, use the host platform or runtime's standard temporary-directory resolver, then allocate an owner-specific goal/sequence namespace beneath the resolved root. Do not prescribe `/tmp`, a fixed Windows path, an environment-variable expression, the shared system/user temporary root itself, a generic `tmp` / `temp` / `cache` root, or another owner's directory. Record each fully resolved absolute owner root with a `goal-owned:` or `sequence-owned:` label and bind subsequent task-temporary writes to that recorded namespace. Reuse the recorded value at Close rather than resolving the platform root again. For `Not applicable`, record directly that no task temporary cache root will be created; do not resolve or allocate one.

`Enabled` authorizes the housekeeping workflow, not unconditional recursive deletion. Inventory first; preserve dependencies, runtime state, logs, reports, durable evidence, unknown producers, locked files, permission boundaries, and symlink/junction/reparse-point escapes. Keep durable Close evidence outside the temporary cache root. If `watcher:housekeeping` is unavailable, do not substitute a raw delete command: keep Close and the overall goal `In Progress`, or mark Close `Blocked` only when the normal runtime hard-stop contract is met. Only a new explicit user decision recorded as a preflight-policy evolution may switch the policy to `Disabled`.

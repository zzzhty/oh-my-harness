## Agent Operating Principles

- Observe before acting; for uncertain, scheduled, recurring, or long-running work, keep durable, inspectable evidence in a named thread, repo file, automation memory, report, TODO, or skill when the state matters beyond the current turn. Do not leave important project state only in chat history.
- Apply Occam's razor: do not add entities without necessity. Prefer fixing the root cause in the owning surface over adding patches, wrappers, shims, fallback paths, alternate backends, compatibility layers, or parallel abstractions that route around the real problem.
- Keep planning schemes separate: use system planning for ordinary complex tasks. Suggest `long-running-goal` only as an option. Create or convert its contract—and run its required planning preflight—only after the user explicitly requests the goal or confirms the conversion; execute it only after an explicit execution request.
- Verification defines done. Use the smallest check that can falsify the changed behavior; do not validate unaffected surfaces or create extra evidence artifacts solely as proof of diligence.
- Automate waiting, checking, summarizing, and reporting; preserve human judgment for mutation, escalation, privacy-sensitive actions, messages to others, source skill mutations, automation changes, and irreversible actions.
- Only a `Ready` `long-running-goal` continuation contract pre-approves planned, non-destructive local work inside its frozen scope as YOLO non-stops; a `Draft` does not. Execute such work without pausing and stop only at a declared runtime hard stop.
- Turn repeated successful workflows into skills, scripts, plugin docs, or checklists so future runs need less re-teaching without hiding review boundaries.
- For global subagent workflow guidance, Codex sessions use the installed note at `$CODEX_HOME/agents/operating-principles.md`; if `$CODEX_HOME` is unset, use `~/.codex/agents/operating-principles.md`. Other harnesses use only their own native support surface.

## Internal identifier evolution

- Use one stable semantic name, not a generation label, only for a current implementation or instruction identifier that is repository-owned, repo-local, non-public, not used outside repository source as an identity in persisted data/state or a persisted contract, and atomically replaceable across all consumers in one change. Replace superseded names across all consumers without compatibility aliases, dual reads/writes, fallbacks, duplicate paths, parallel current entities/authorities, or history-only versioning; keep revision history in Git and applicable checkpoint/validation ledgers.
- Preserve package/release, standard/protocol/API or another external contract, migration/rollout/feature-flag, milestone/phase, user/business, immutable, persisted, archival, and historical identities. Changing a public, persisted, externally consumed, or cross-repository identity requires an inventory of consumers, existing data, and compatibility impact plus explicit scoped migration, validation, and rollback authorization; this policy grants no rename authority.
- Classify each match before scoped edits and validate every affected consumer. Preserve archives and historical evidence; repository-wide regex or bulk renames and silent rebaselines are hard stops. When a canonical algorithm or fingerprint field, payload, or semantic changes, record the replacement, regenerate the expected value from the changed source, and validate the single current value against its oracle.

## Failure-handling policy

- Surface failures directly: report the root cause, failing command/path, and exact breakpoint when known.
- Fix the underlying issue first. Do not mask or route around failures with fallbacks, silent degradation, temporary workarounds, compatibility shims, alternate systems, data paths, implementations, backends, changed assumptions, or fake success states unless explicitly requested.
- If the root cause cannot be fixed yet, stop after collecting minimal useful diagnostics and report the concrete blocker clearly.

## Test coverage policy

- Keep tests focused on behavioral red lines, integration contracts, and regression-prone flows.
- Prefer consolidating narrow single-point assertions into behavior-level tests when setup and failure mode are shared.
- Avoid fragmented tests for trivial helpers unless they protect real compatibility, safety, or failure-handling boundaries.
- Do not add SHA-256/checksum receipts, snapshots/golden files, or duplicate defensive tests as generic completion evidence. Add such mechanisms only when explicitly requested, when they protect an observed failure mode, or when an owning content-identity or integrity contract requires them. This rule is prospective; it does not by itself authorize removing or silently rebaselining any existing hash, checksum, snapshot, golden file, test, or owning contract.
- Preserve explicit coverage for privacy, destructive actions, schema compatibility, cross-platform command generation, and user-visible workflow guarantees.

## Delegation policy

- Use subagents only when the user explicitly asks for subagents or the active environment/plan authorizes them. When a task invokes `$orchestrate-subagents`, use that skill as the detailed workflow instead of duplicating recipes here.
- Broad read-only review requests, such as PR, branch, diff, architecture, skill, prompt, docs, contract, security, or regression review, authorize read-only subagent review. This authorization does not invoke `$orchestrate-subagents` by itself. Spawn only read-only explorer/default reviewers; do not use workers or edit files. Consolidate evidence-backed findings and mark partial coverage or subagent failures explicitly.
- Delegate only bounded tasks with clear inputs, expected outputs, stopping conditions, and read-only scope or disjoint write ownership.
- Do not delegate tiny tasks, tightly coupled sequential debugging, or work where multiple agents may race on the same files.
- Keep the main agent responsible for planning, final decisions, integration, verification, and user-facing conclusions; subagents must report concise findings with relevant paths, commands run, evidence, and unresolved blockers.

## Subagent failure handling

- Treat subagent failures as first-class failures: surface timeouts, missing access/tools, incomplete findings, and blockers explicitly.
- Do not silently replace a failed subagent with assumptions, fabricated findings, or a different implementation path just to continue.
- The main agent may run minimal follow-up diagnostics to confirm the failure or narrow the blocker, but must not hide the original subagent failure.
- If a failed subagent owned required work, stop integration until resolved or explicitly accepted by the user; if optional, continue only after marking coverage as partial and explaining what coverage is missing.

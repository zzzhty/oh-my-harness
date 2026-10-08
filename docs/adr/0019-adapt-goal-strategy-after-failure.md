# ADR 0019: Adapt goal strategy after failure and honor native hard stops

Status: Accepted for implementation on 2026-10-08.

## Evidence and decision

The user requires a hard stop at the third native Codex Goal failure. The prior skill treated technical impossibility as a stop normally after at least three local attempts or approaches, without requiring improvement after each failure. Its atomic template repeated that local threshold, and the Sequence template prohibited every fallback or alternate backend despite the global failure policy allowing equivalent authorized methods.

Remove the local three-attempt expectation. After every failure, record its evidence and repair the cause or change the next step within frozen scope and acceptance criteria. Native feedback identifying the first or second Goal failure requires immediate strategy adjustment. A deterministic failure rules out repeating the unchanged path without new evidence. A repair can legitimately rerun the same required validation; an unchanged retry requires evidence of a transient fault or a changed prerequisite.

A third native failure identified by native feedback, or any native hard-stop feedback, ends active Goal execution even when another useful approach exists. Do not automatically make a fourth native attempt, resume, or recreate/replace a Goal to reset failures. A Sequence has one native parent Goal; child promotion or creation of a child native Goal cannot route around its stop.

This is the requested execution constraint. Public documentation has not verified the native platform's counted events or reset semantics. Ordinary test and diagnostic exits are not native failure events. Use only available native feedback; absent counts remain unknown and still require improvement after every failure. No custom runtime counter, native-event inference, remaining-attempt estimate, or platform reset claim is introduced.

Authorization gaps stop affected actions immediately at any stage. Independent authorized work can continue within the current milestone without bypassing gates; a native hard stop permits only independently authorized work outside the stopped Goal. Equivalent fallback or alternate methods retain existing authorization, specified methods, required gates, privacy/safety, frozen semantics, acceptance criteria and Sequence order. If no feasible authorized path remains or an external dependency must change, record the blocker and concrete recovery condition rather than loop indefinitely.

## Consumer classification

| Surface | Treatment |
| --- | --- |
| Long-running-goal skill and execution reference | Current instruction owners; the inline authority and native boundary apply before the execution reference's recovery protocol and ordinary continuation. |
| Atomic and Sequence templates, Sequence handoff reference, Workflow README | Current producers/consumers; align native stops, per-failure recovery and equivalent-method boundaries. Preserve field names, lifecycle states, registers, invocation and promotion policy. |
| Readiness and Sequence scripts | Existing document validators, not retry engines; preserve their implementation and verify admission of recovery and native-stop evidence. |
| Disclosure and recovery tests | Replace the old local three-attempt assertion and add scoped semantic disclosure guards plus isolated document-validator integration. |
| Existing user goals, prior ADRs and historical results | Preserved; no active goal, installation or historical evidence is rewritten. On authorized execution, current skill authority applies without inventing missing native feedback. |
| Workflow manifest and distribution identity | Existing generated integrity contract; run the repository updater after source edits and owning tests, then validate its one current identity. Other packages retain their content identities. |

## Frozen oracle

- After a deterministic failure, change the supported hypothesis, implementation, inputs or authorized path before another attempt; do not exhaust native opportunities on a disproven route.
- After a repair, the original validation command can run again with the original acceptance criteria. Transient or changed-prerequisite evidence may justify an unchanged retry.
- Identified native failures one and two require immediate adjustment. An identified third failure or any native hard stop ends the active Goal regardless of possible progress.
- Ordinary test or diagnostic failures never establish native counts. Unknown counts remain unknown, while recovery still improves each next step.
- Missing authorization stops the affected action before any retry or alternate route; unrelated authorized work retains its own authority.
- An equivalent authorized method can complete the same required result while preserving specified methods, gates, acceptance and frozen semantics.
- A stopped Sequence cannot promote another child or recreate the native parent. An external wait or infeasible path records recovery conditions.

The no-change baseline violates the first, third and sixth cases. Merely adding a third-failure stop leaves the earlier repetition and blanket fallback prohibition intact. Adding a retry engine or counter would claim unsupported platform semantics and duplicate the native authority.

## Validation limits and recovery

The recovery tests inspect the affected declarations and routing, and invoke the unchanged readiness checker on synthetic goal documents in isolated temporary directories. They guard the declared contract and structural admission; they do not measure live model behavior, observe native failure events, or verify the platform's third-failure counting or reset implementation. No real native Goal or user installation is exercised.

Validate the owning Workflow suite, the full repository/Watcher suites, source plugin schemas, relative links, JSON authorities, diff hygiene and generated distribution identity. Report actual CI outcomes separately. Independent model/counterexample evaluation remains unperformed in this execution environment; static checks cannot establish model adherence.

Git retains the prior source and generated identity. Revert them together if necessary, preserve user evidence, and never recreate a native Goal as a recovery mechanism for its stopped attempts.

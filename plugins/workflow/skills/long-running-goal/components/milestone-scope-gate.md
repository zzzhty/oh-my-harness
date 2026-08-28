# Milestone Scope Gate

Use this component during `long-running-goal` execution to constrain unplanned scope and validation expansion inside one milestone. The generic decision remains owned by `../../scope-discipline/references/necessity-gate.md`; this component maps that decision onto the goal lifecycle.

## Milestone Boundary Inputs

Derive the current boundary from existing goal fields only:

- overall outcome and goal-level non-goals;
- current milestone scope and its explicit "does not do" boundary;
- current review gate and declared validation;
- pre-approved local and external operations;
- later milestones and their ownership;
- runtime hard stops and frozen semantic decisions.

Do not add a scope budget, validation budget, file allowlist, maximum tool count, or duplicate checklist to the goal merely to use this component.

## Entry Gate

At milestone entry, state internally which recorded scope, review gate, validation, and later-stage boundaries are active. Planned work and declared gates are already authorized. This component does not reduce or reopen them.

## Expansion Gate

Before material scope or validation expansion, apply `../../scope-discipline/references/necessity-gate.md` and route the result:

- **Current milestone work**: execute it normally.
- **Necessary consequence**: update the current milestone scope or evidence with the reachable reason, implement only the required expansion, and continue without asking the user unless a runtime hard stop independently applies.
- **Later milestone work**: defer it to the recorded later milestone and do not implement it early.
- **Speculative expansion**: reject it and continue the current milestone.
- **Semantic conflict**: pause mutation, record the contradictory evidence, evolve the goal or reusable strategy, and ask the user only when the existing runtime hard-stop boundary applies.

A scope change is material when it changes an owned subsystem, externally visible behavior, persisted state, compatibility boundary, dependency set, milestone ordering, or declared validation surface. Ordinary caller updates, focused fixes, and commands already implied by the current gate do not require a separate expansion ceremony.

## Validation Gate

Always run validation already declared by the milestone, repository, review gate, or checkpoint contract. Broaden it only when current failures or affected interfaces prove the need.

After the declared validation and review gate pass, stop adding tests, searches, reviews, audits, hashes, snapshots, or reports unless a new oracle or reachable contract requires them.

## Exit Gate

A milestone may advance when:

- its recorded scope and necessary consequences are complete;
- its review gate and required validation pass;
- checkpoint evidence is recorded;
- no unresolved in-scope failure or semantic conflict remains.

The checkpoint component has already recorded its evidence before this gate passes. Once these conditions pass, enter the next milestone automatically without another final scope audit.

Completion criterion: material expansions were routed through the shared necessity gate, later-stage work was not pulled forward, required validation passed, and the milestone exited without unsupported residual work or an extra audit loop.

---
name: scope-discipline
description: Apply a temporary scope-and-evidence boundary only when the user explicitly invokes scope-discipline or explicitly asks to reject overengineering, scope creep, speculative hardening, redundant validation, repeated audits, or unnecessary agent work. Ordinary coding tasks are not a trigger.
---

# Scope Discipline

Deliver the requested result and its necessary consequences. Stop unsupported expansion.

## Trigger And Authority

Use this skill only when the user explicitly invokes `scope-discipline` or explicitly asks to reject overengineering, scope creep, speculative hardening, redundant validation, repeated audits, or unnecessary agent work. Ordinary coding, review, debugging, planning, or long-running work is not itself a trigger.

This callable skill is explicit-only. Another already-invoked workflow may reuse `references/necessity-gate.md` as an internal component; that reuse does not make `scope-discipline` the primary workflow and does not broaden the active task authority.

Apply authority in this order:

1. the newest user request and explicit scope;
2. active repository, `Ready` goal, SOP, release, safety, privacy, compatibility, and compliance contracts;
3. reachable correctness evidence from current code, data, callers, tests, deployment state, or acceptance;
4. the default discipline in this skill.

Never use this skill to weaken an explicit gate, planned validation, required migration, compatibility obligation, security or privacy boundary, or current reachable caller. The target is the smallest correct result, not the fewest files, lines, tests, tools, or elapsed minutes.

Global instructions remain the owner of general mutation, testing, delegation, safety, and failure-handling policy. This skill owns only the temporary scope-and-evidence workflow delta.

## Freeze The Current Boundary

Before applying the discipline, identify from existing authority:

- requested result and task mode;
- authorized write and external-action scope;
- explicit non-goals or later-stage work;
- applicable review gates, validation commands, and completion criteria.

Do not create a new plan, ledger, checklist, or evidence artifact merely to restate that boundary. Use the current request and existing owner contracts.

Read `references/necessity-gate.md` before deciding whether to add material scope or validation.

## Apply Proportionately

Apply the necessity gate only before a material expansion, such as:

- a new abstraction, dependency, compatibility layer, migration, fallback, backend, or generalized framework;
- work assigned to another milestone or explicitly excluded from the current result;
- a new subagent or independent review pass;
- validation broader than the declared or currently evidenced impact;
- another audit, search, test, report, checksum, snapshot, or evidence artifact after the completion evidence is already sufficient.

Do not run the gate for every ordinary command, edit, caller update, focused test, or checkpoint operation already authorized by the active contract.

When reachable evidence proves a necessary consequence, expand only enough to preserve correctness and record the material reason in the existing owner. When work belongs to a later milestone, leave it with that existing owner rather than implementing it early or creating a parallel TODO. When continuing would change frozen semantics, update the owning contract and use its existing hard-stop boundary.

## Verification And Stop Condition

Run validation already required by the user, repository, active workflow, review gate, or affected behavior. Expand validation only when a failure, shared interface, persisted state, cross-platform path, security or privacy boundary, migration, or other reachable evidence proves the broader check is needed.

Stop adding work when all of the following hold:

- the requested result and necessary consequences are complete;
- required validation and review gates pass;
- no new failure or reachable contract requires expansion;
- no unresolved in-scope correctness or semantic conflict remains.

Do not add a final audit loop merely to demonstrate that this skill was used.

## Completion

Report the requested result, material necessary consequences, and the evidence that makes the task complete. Mention a rejected or deferred expansion only when it changes follow-up decisions; keep internal scope policing out of the deliverable otherwise.

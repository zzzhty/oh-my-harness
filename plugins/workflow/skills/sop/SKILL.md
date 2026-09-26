---
name: sop
description: Create, run, or revise a reusable Standard Operating Procedure for a stable workflow with explicit inputs, ordered actions, outputs, validation, and stop or escalation boundaries.
---

# SOP

Use this skill when a repeated workflow is stable enough to execute the same way again.

Route unresolved design or prompt behavior to `prompt-strategy-loop`. When the work may need staged milestones, checkpoint evidence, or close/archive lifecycle, suggest `long-running-goal` and wait for explicit user confirmation before creating or converting its contract.

## Suitability

An SOP is ready to author when its trigger, inputs, permissions, steps, outputs, validation, and stop conditions are known. State the execution mode in a short Execution Harness section. Add orchestration, isolation, connector permissions, independent verification, escalation, and writeback only when the procedure uses them; manual procedures need no `Not applicable` inventory.

## Select The Mode

Resolve the newest request against the existing SOP before taking action:

- **Create / update:** follow Create Or Update; authoring does not execute the procedure.
- **Explain:** read and explain the procedure, including an unfinished `Draft`, and identify gaps without running its steps. `Ready` is not required for explanation.
- **Dry-run:** preview steps and expected outputs using only authorized, non-mutating inspection. Treat commands named `--dry-run` as safe only after inspecting their actual behavior and permissions. Do not perform destructive, publishing, or other real procedure effects; report what remains unverified. A Draft may be previewed but cannot authorize execution.
- **Execute:** follow Execute, including its `Ready` gate. If a mixed request moves from another mode into execution, apply that gate before any procedure action.

## Create Or Update

1. Read the current source of truth: instructions, README, runbook, script, automation state, prior SOP, and relevant failure evidence.
2. Classify the procedure as manual, agent-executed, automated, report-only, validation, maintenance/release, or incident/failure.
3. Update an existing SOP in place, preserving unrelated content. Only for a new SOP, copy `templates/sop_template.md` into the existing owning runbook, operations, workflow, plugin-doc, or SOP directory. Use `docs/sop/<sop-slug>.md` only when no owner already exists.
4. Replace placeholders and keep unverified commands visibly marked as expected. Include the working location with inputs when commands depend on it. A reuse prompt is optional; link to the contract instead of restating it.
5. When behavior changes, update the affected trigger, inputs, steps, validation, failure/stop, and harness fields as one contract. Use evidence-backed review through `prompt-strategy-loop` for prompts, rubrics, permissions, automation triggers, or verification rules.
6. Validate:

```bash
python <skill-folder>/scripts/check_sop_ready.py [--allow-draft] <sop-file>
python <skill-folder>/scripts/check_sop_links.py <sop-root-or-file>
```

## Execute

1. Re-read the SOP, available inputs, and current authorization.
2. Before the first action, run `check_sop_ready.py <sop-file>` without `--allow-draft` and confirm the top-level status is `Ready`. If the SOP is `Draft` or the check fails, do not execute it; stop or route the request to Create Or Update.
3. Follow the declared steps and permissions in order, using only available inputs. Keep report-only procedures non-mutating and treat a missing required input as a stop.
4. Stop at the first declared stop condition or failed required validation. Record the evidence the SOP requires.
5. Report outputs, commands, changed files or artifacts, validation, blockers, and residual risk.

## Completion

A reusable SOP has eight core sections: Trigger, Inputs, Execution Harness, Allowed Actions, Steps, Validation, Output Contract, and Stop Conditions. Each step names its action and expected output; add local failure handling or completion criteria only when the shared stop and validation rules are insufficient. Summary, preconditions, separate working directory, forbidden actions, update rules, and reuse prompt are optional. The checker accepts only `Ready` by default; `--allow-draft` validates a non-executable `Draft`. Passing a check never grants additional action permissions.

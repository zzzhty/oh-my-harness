---
name: sop
description: Create, run, or revise a reusable Standard Operating Procedure for a stable workflow with explicit inputs, ordered actions, outputs, validation, and stop or escalation boundaries.
---

# SOP

Use this skill when a repeated workflow is stable enough to execute the same way again.

Route unresolved design or prompt behavior to `prompt-strategy-loop`. When the work may need staged milestones, checkpoint evidence, or close/archive lifecycle, suggest `long-running-goal` and wait for explicit user confirmation before creating or converting its contract.

## Suitability

An SOP is ready to author when its trigger, inputs, ordered actions, outputs, validation, failure handling, stop conditions, and durable owner can be explicit. For agent-executed or automated procedures, also freeze the execution mode, orchestration, isolation, connector permissions, independent verification, escalation, and writeback. A manual SOP may mark those fields `Not applicable` with a reason.

## Create Or Update

1. Read the current source of truth: instructions, README, runbook, script, automation state, prior SOP, and relevant failure evidence.
2. Classify the procedure as manual, agent-executed, automated, report-only, validation, maintenance/release, or incident/failure.
3. Copy `templates/sop_template.md` into the existing owning runbook, operations, workflow, plugin-doc, or SOP directory. Use `docs/sop/<sop-slug>.md` only when no owner already exists.
4. Replace placeholders, keep unverified commands visibly marked as expected, and include a reuse prompt naming the SOP path, trigger, execution mode, mutation boundary, expected output, and stop conditions.
5. When behavior changes, update the affected trigger, inputs, steps, validation, failure/stop, and harness fields as one contract. Use evidence-backed review through `prompt-strategy-loop` for prompts, rubrics, permissions, automation triggers, or verification rules.
6. Validate:

```bash
python <skill-folder>/scripts/check_sop_ready.py [--allow-draft] <sop-file>
python <skill-folder>/scripts/check_sop_links.py <sop-root-or-file>
```

## Execute

1. Re-read the SOP and newest request; classify the requested mode as execute, update, explain, or dry-run.
2. Before the first action, run `check_sop_ready.py <sop-file>` without `--allow-draft` and confirm the top-level status is `Ready`. If the SOP is `Draft` or the check fails, do not execute it; stop or route the request to Create Or Update.
3. Follow the declared steps and permissions in order, using only available inputs. Keep report-only procedures non-mutating and treat a missing required input as a stop.
4. Stop at the first declared stop condition or failed required validation. Record the evidence the SOP requires.
5. Report outputs, commands, changed files or artifacts, validation, blockers, and residual risk.

## Completion

A reusable SOP identifies its trigger, inputs, working location, execution harness, allowed actions, ordered steps with completion criteria, outputs, validation evidence, stop and escalation boundary, durable writeback, and reuse prompt. The template and readiness checker are authoritative for the field-level contract; the default check authorizes only `Ready`, while `--allow-draft` validates a complete but non-executable `Draft`.

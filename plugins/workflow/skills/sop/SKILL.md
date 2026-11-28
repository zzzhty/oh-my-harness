---
name: sop
description: Create, run, or revise a reusable Standard Operating Procedure for a stable workflow with explicit inputs, ordered actions, outputs, validation, and stop or escalation boundaries.
---

# SOP

Use this skill when a repeated workflow is stable enough to execute the same way again.

Route unresolved design or prompt behavior to `prompt-strategy-loop`. If the work needs a brief checkpoint to continue across turns, suggest `long-running-task` and wait for explicit user confirmation before switching. Direct execution is the default; use the host's native `/goal` only if the user explicitly selects it and the host supports it.

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
5. When behavior changes, update the affected trigger, inputs, steps, validation, failure/stop, and harness fields as one contract. For applicable continuation workflows, state what prior evidence can be reused, what invalidates its coverage, who decides, and where to resume once the required state prerequisites hold. Use evidence-backed review through `prompt-strategy-loop` for prompts, rubrics, permissions, automation triggers, or verification rules.
   - After consulting evidence, keep the conditions and actions the next executor needs to choose inputs, follow steps, reuse evidence, and honor authorization and stops. If an incident exposes a mistake a future agent could repeat, capture a lesson with the trigger, the mistaken assumption, what to do next time, and a link to evidence or an automated check. If an existing SOP or test already teaches that action, reference it instead. For one-run details, link the original evidence: a fixed Git commit and path for committed implementation, and the actual stored readback or receipt for runtime and external facts. A validation record can just index the object checked, result, scope, and evidence link. Use existing repository locations; no new lesson file, validation log, or archive is required.
   - Example: “Round three used the old running image despite the config update; after a restart, round four passed.” SOP: “Before retesting, read the running container's image ID and compare it with the candidate manifest; stop on mismatch.” Lesson, only if needed: when validating a deployed candidate, read identity from the running process; updated config describes intended state, not running state. Keep both runs' outputs in the original validation record and link to them; this is not authorization to restart.
6. Review and prune the candidate before finishing maintenance. Review the whole draft for a new SOP; for an update review the changed and adjacent rules plus affected commands, writeback destinations, and references. Look for stale claims about what is current, next, or already authorized.
   - If authorized and supported, ask one read-only subagent in a fresh context to review the candidate. Provide the maintenance goal, candidate or diff, governing rules and execution entry points, and available validation and archive locations. Do not supply your proposed deletions or conclusions. The reviewer may inspect source, references, and tests, but must not write files or execute the SOP. If delegation or independent context is unavailable, apply the same standard yourself and disclose the actual mode and coverage. This step does not apply to explain, dry-run, or execute.
   - Ask what could go wrong for the next executor if a passage disappeared: wrong trigger, input or artifact, order, authorization, compatibility, evidence reuse or invalidation, validation, recovery, or stop. Keep the minimum rule needed to decide correctly. Dates, old versions, and hashes are not removal criteria; preserve conditions enforced by current code, including exact gates and build identities that distinguish same-version artifacts.
   - Apply the evidence-link rule above to one-run observations. Link existing historical records for completed or superseded plans, stale queues, consumed one-time grants, retired commands, and task-only checkpoints; preserve the grant's original target and scope as history, not live permission. Split mixed passages by sentence. If an active instruction points to a closed destination, retarget new results to the current task's record and keep the old result linked as history. Correcting a destination does not authorize writeback.
   - The reviewer returns actionable findings only: location, proposed disposition, reason, existing destination, and the rule that must remain. Identify missing evidence and retain uncertain material. If there are no findings, say so briefly; do not inventory reviewed paragraphs.
   - The main agent verifies findings and makes authorized edits. Link existing authoritative records instead of copying them. Before moving unique material, check inbound links, anchors, and scripts or tests that read its path, heading, or content. Preserve live entry points and constraints; move unique evidence to its authorized owner before pruning, or leave it in place and report the blocker. Do not add a review section or ledger to business SOPs.
7. Validate the final candidate with the existing readiness and link checks below and the smallest tests that directly depend on changed content. Check that operative rules still suffice, history is traceable, and destinations still serve their intended purpose. Reuse valid review and checks for the same final state. If later edits change rules, record ownership, evidence meaning, or reader dependencies, re-review and revalidate only the affected scope:

```bash
sh "<harness-root>/.omh-runtime/run.sh" workflow "<skill-folder>/scripts/check_sop_ready.py" [--allow-draft] <sop-file>
sh "<harness-root>/.omh-runtime/run.sh" workflow "<skill-folder>/scripts/check_sop_links.py" <sop-root-or-file>
```

## Execute

1. Re-read the SOP, available inputs, and current authorization.
2. Before the first action, run `check_sop_ready.py <sop-file>` without `--allow-draft` and confirm the top-level status is `Ready`. If the SOP is `Draft` or the check fails, do not execute it; stop or route the request to Create Or Update.
3. Follow the declared steps and permissions in order, using only available inputs. Keep report-only procedures non-mutating and treat a missing required input as a stop.
4. Honor user stops, explicit termination, safety, permission boundaries and missing required inputs immediately. For a recoverable validation failure, pause dependent steps and preserve evidence. If authorized diagnosis, repair, or continuation is needed, read [Recovery And Continuation](references/recovery.md) before proceeding. The owning SOP's recovery and retry limits govern; a Draft or report-only SOP gains no mutation authority from this reference. Independent authorized work may continue where dependencies allow.
5. Report outputs, commands, changed files or artifacts, validation, blockers, and residual risk.

## Completion

A reusable SOP has eight core sections: Trigger, Inputs, Execution Harness, Allowed Actions, Steps, Validation, Output Contract, and Stop Conditions. Each step names its action and expected output; add local failure handling or completion criteria only when the shared stop and validation rules are insufficient. Recovery is optional: when used, declare its shared or step-local path, any retry limit and required revalidation; an explicitly terminating procedure may stop directly. Summary, preconditions, separate working directory, forbidden actions, update rules, and reuse prompt are optional. The checker accepts only `Ready` by default; `--allow-draft` validates a non-executable `Draft`. Passing a check never grants additional action permissions.

## Runtime

Invoke Python helpers using the owner-installed `<harness-root>/.omh-runtime/run.sh`
(`sh ...` on POSIX) or `run.ps1` (`& ...` on Windows), then group `workflow`,
script and arguments. Locate `.omh-runtime` beside the skills root or above its
native plugin cache; read its persisted group binding. An absolute `OMH_PYTHON`
overrides it only with a validated venv; an invalid override fails closed.
Unprepared groups require the installation owner to prepare them. Helper
execution never creates a venv or installs dependencies.

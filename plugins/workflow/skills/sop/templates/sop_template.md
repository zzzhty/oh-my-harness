# SOP: <Name>

Status: Draft

## Trigger

<When this stable procedure applies.>

## Inputs

<Required inputs, source of truth, and working location when relevant.>

## Execution Harness

<Manual, agent-executed, or automated. Add only applicable orchestration, isolation, external permissions, independent verification, escalation, and durable writeback details.>

## Allowed Actions

<Read and write scope covered by the current authorization. State any material exclusions here.>

## Steps

### Step 1 - <Name>

Action: <Concrete command or action.>

Expected Output: <Observable result.>

## Validation

<Checks that establish the procedure succeeded. Add step-specific completion criteria only where these checks are insufficient.>

## Output Contract

<Results, evidence, changed paths, and artifact location to report.>

## Stop Conditions

<Define procedure-specific termination, missing-input, safety and permission stops. If recovery is permitted, name its authorized diagnosis, repair, retry limit and revalidation path. Pause dependent steps and preserve failure evidence; keep acceptance criteria and report-only non-mutation intact. Reuse passing evidence only within the owner's accepted bindings; recheck changed or failed coverage and necessary prerequisites before resuming. Specify required fresh/full admission, fixtures/resources, complete transaction/rollback, readback and cleanup where applicable. Never splice old mutable state, reset retry budgets merely by changing sessions, or blindly repeat failures. Stop and report when recovery is prohibited, exhausted, or needs authorization.>

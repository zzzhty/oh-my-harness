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

<Explicit termination, missing-input, safety and permission stops take priority. If this procedure permits recovery, declare shared or step-local diagnosis, repair or bounded retries within scope: pause dependent steps, keep report-only work non-mutating, and repeat unchanged required validation before continuing. Stop and report when recovery is unavailable, exhausted or needs more authorization; a procedure may instead terminate immediately.>

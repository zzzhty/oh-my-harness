# Implementation Planning

Use this branch when the user asks for a plan before implementation and independent inspection can clarify architecture, options, validation, or rollback. Keep implementation out of this branch.

## Candidate Assignments

Choose the minimum set needed to close genuine planning unknowns:

| `task_name` | Assignment prompt focus | Prompt permission |
| --- | --- | --- |
| `architecture_mapper` | Map ownership boundaries, entry points, dependencies, and related tests. | `Permission: read-only` for the named modules and their direct consumers. |
| `option_analyst` | Compare viable implementation options, tradeoffs, risks, and rejected alternatives. | `Permission: read-only` for the evidence required by the decision. |
| `validation_planner` | Identify behavioral gates, existing commands, missing tests, and rollback or containment. | `Permission: read-only` for tests, scripts, and configuration. |

Every prompt names the planning decision it informs. Evidence collection remains part of that single decision, not a second assignment.

## Completion Criterion

The parent receives an evidence-backed architecture map, bounded option decision, or validation plan for every selected assignment, with missing facts and unresolved choices visible before implementation begins.

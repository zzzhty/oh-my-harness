# PR Or Branch Review

Use this branch for a read-only PR, branch, diff, or planned-merge review with a known base/head or exact diff scope. Keep a narrow file review in the parent, and route implementation elsewhere.

## Candidate Assignments

Choose only the assignments that expose materially independent evidence:

| `task_name` | Assignment prompt focus | Prompt permission |
| --- | --- | --- |
| `change_mapper` | Map changed files, affected symbols, call paths, configuration changes, and risky boundaries. | `Permission: read-only` for the exact diff and reachable source. |
| `implementation_reviewer` | Review correctness, security, regression, compatibility, and contract risks. | `Permission: read-only` for the diff, owning instructions, and relevant source. |
| `test_gap_reviewer` | Identify missing behavioral coverage and validation gaps. | `Permission: read-only` for changed behavior, related tests, and test commands. |

Every prompt names the exact base/head or diff, requested review axis, evidence paths, and the point at which the assignment must stop.

## Completion Criterion

Every selected assignment returns paths and command evidence for its claims, unresolved coverage is visible, and no assignment writes repository or external state.

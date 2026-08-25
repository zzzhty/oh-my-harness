# Parallel Implementation

Use this branch only when implementation is authorized, write scopes are exact and disjoint, and shared files plus final integration remain parent-owned. Keep sequential debugging, shared configuration, lockfiles, and generated artifacts out of parallel write ownership.

## Candidate Assignments

Derive task-local names from the owned slice rather than reusing generic identities:

| `task_name` | Assignment prompt focus | Prompt permission |
| --- | --- | --- |
| `<slice>_implementation` | Implement one bounded behavior in one owned module or file group and run focused slice checks. | `Permission: exact disjoint write scope` listing every writable path and every shared or forbidden path. |
| `<other_slice>_implementation` | Implement a second independent behavior with no overlapping files. | `Permission: exact disjoint write scope` listing every writable path and every shared or forbidden path. |
| `integration_risk_review` | Inspect the planned slices for cross-boundary risk while implementation proceeds. | `Permission: read-only` for both slices and their shared contracts. |

Each implementation prompt states that concurrent edits may exist, forbids reverting others' work, and stops before any required edit outside the declared write scope. Slice tests are assignment evidence; final integration and cross-slice validation remain parent work.

## Completion Criterion

Every changed path belongs to exactly one assignment, no shared artifact was edited by a subagent, focused checks and behavior impact are reported, and the parent independently integrates and validates all slices.

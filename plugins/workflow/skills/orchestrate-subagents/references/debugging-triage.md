# Debugging Triage

Use this branch when a failing command, test, CI run, report, log, or reproducible symptom can split into independent reproduction, code-path inspection, and diagnostic planning. Keep sequential interactive debugging in the parent.

## Candidate Assignments

Choose only the assignments supported by available failure evidence:

| `task_name` | Assignment prompt focus | Prompt permission |
| --- | --- | --- |
| `failure_reproducer` | Reproduce or classify the supplied failure and report the exact breakpoint. | `Permission: read-only source`; name any approved temporary or build outputs the reproduction command may create. |
| `code_path_inspector` | Inspect the affected code path, configuration, and relevant recent changes. | `Permission: read-only` for the named path and directly connected source. |
| `diagnostic_planner` | Propose diagnostics or regression tests that distinguish evidence-backed hypotheses. | `Permission: read-only`; no source or test edits. |

Every prompt includes the original command, error or symptom, available environment facts, and a stop when the failure cannot be accessed or the assignment would need mutation.

## Completion Criterion

The reproduction outcome or access blocker is explicit, likely failure boundaries cite exact evidence, and proposed diagnostics distinguish hypotheses without claiming an unobserved cause.

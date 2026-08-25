# Documentation Alignment

Use this branch to audit active documentation, runbooks, skills, plans, scripts, entry points, or terminology against an identified source of truth. Keep narrow wording edits and archive-only historical hits in the parent unless history is explicitly in scope.

## Candidate Assignments

Choose assignments that inspect separate evidence surfaces:

| `task_name` | Assignment prompt focus | Prompt permission |
| --- | --- | --- |
| `documentation_inventory` | Map active docs, indexes, operational entry points, and scoped historical material. | `Permission: read-only` for the named documentation roots and source indexes. |
| `drift_reviewer` | Compare active guidance with owning source and rank semantic drift. | `Permission: read-only` for docs and the exact source-of-truth paths. |
| `link_validator` | Check links, commands, entry-point reachability, and validation coverage. | `Permission: read-only`; allow only named non-mutating validation commands. |

Every prompt distinguishes active guidance from archives and names the source that can prove each claimed mismatch.

## Completion Criterion

The active inventory, source-of-truth comparison, stale terms, broken links, outdated commands, and uncovered areas are reported with exact paths, while archive-only evidence remains classified rather than treated as current guidance.

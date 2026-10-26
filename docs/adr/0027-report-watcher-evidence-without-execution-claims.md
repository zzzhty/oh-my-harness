# Report Watcher evidence without claiming execution

## Context

At baseline `c77cd266a4be4667d61811afe55d606ba420a1a2`, the Codex adapter
selected the first catalog alias match as primary, expanded manifest dependencies
into `effective`, and scanned tool-response text for failure words. Reports called
these summarized-turn references usage and classified frequent references as active.
These signals do not establish execution, execution order, task quality or a
false-positive rate. Earlier reports from other revisions are historical evidence,
not a baseline to apply blindly to current source.

## Decision

Keep the small hook/JSONL/report architecture and existing CLI. Classify observations
by evidence source: text mention, structured/manual selection assertion, declared
dependency, or unclassified historical attribution. Do not infer selection from
text syntax or current logical groups. Current supported hooks provide no verified
skill-load/invocation signal, so execution remains unknown even for an explicit
selection. Do not introduce more elaborate regexes, required announcements,
per-turn manual logging or full conversation collection to fill this gap.

New text matches populate `mentioned` only. Structured `skill_name`/`skill` fields
can populate primary, with `provided` provenance. Later text mentions preserve that
selection instead of replacing it with the first catalog match. Dependency metadata
remains a declaration. All new hook attribution includes `execution_status: unknown`.

Tool outcomes use only supported top-level structured exit/error status fields.
Nested content, ordinary strings and failure keywords cannot establish failure;
unsupported responses remain unknown. Tool failures remain observations, never task
outcomes or skill-quality attribution. Stop still writes `task_outcome: unknown`.
Reports use explicit task-outcome fields only and retain their uncertainty; they
never fall back to a raw event outcome or compute rates without a complete denominator.

Reports count unique summarized session/turn keys, falling back to event ID and then
content hash. The last summary for the same key wins consistently for evidence,
task outcomes and tool counts. Exact duplicate records are counted once per window;
incremental overlap retains its existing content-hash cursor contract. This is not
a global execution counter. Columns/skills/groups can overlap, and missing summaries
or filtered events limit coverage.

## Authority and compatibility

- Canonical skill files remain the callable authority; repository attribution
  overlays own declared aliases/dependencies. Runtime metadata is their cached
  projection. No skill text, invocation contract, permissions or selection set changes.
- Preserve schema 2, `primary`, `supporting`, `effective`, `mentioned`, raw outcomes,
  event identities, stored reports and incremental cursor identities. These persisted
  names are compatibility surfaces, not new execution claims. Evidence/provenance
  additions are optional for old records. No reset or migration is required.
- Interpret historical `prompt_mention` and `assistant_announcement` primaries as
  mentions; provided/manual primaries as selection assertions; missing sources as
  unclassified. The old single `skill_name` shape is readable as unclassified.
- Fold only explicitly declared `legacy_names` in report views/filters. Display raw
  identities and preserve unmapped history; never rewrite JSONL. Current group labels
  are present-day display categories, not historical trigger or invocation policy.
- Rename repository-local report helpers and misleading headings atomically with
  tests. Keep CLI options and output paths. New mention-only records require the
  updated report reader; older readers may omit them.
- Preserve the bounded redacted summaries, hashes and persistence filter. No user
  runtime events, configuration, installations or external downstream copy is needed
  to test this change.

This supersedes the current execution/effective-usage interpretation and discard/reset
permission in [ADR 0001](0001-skill-watcher-breaking-usage-schema.md) for this correction;
that ADR remains historical evidence. It retains the legacy view-mapping boundary in
[ADR 0002](0002-consolidate-watcher-plugins.md).

## Validation and limits

Synthetic isolated tests cover tables, quotations, negation, multi-skill comparison,
structured selection without loading, dependency declarations, tool-text counterexamples,
same-turn and incremental deduplication, explicit alias folding without log mutation,
unmapped identities, unknown task outcomes, no rate, and bounded redaction/persistence.
Run the Watcher test suite (including `test_skill_watcher.py`,
`test_report_incremental.py`, and `test_skill_evidence.py`), owning catalog/package tests
and plugin validation. Regenerate content-derived plugin identity once after source
and test completion, then validate the generated identity.

Live native loading/invocation coverage is intentionally unverified and unavailable.
Historical tool failures and task-outcome assertions cannot be independently verified
from redacted records. Tests do not recount the user's historical logs or install hooks.

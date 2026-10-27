# ADR 0029: Pure Hub with skill-owned helpers

Status: accepted for the 1.1.0 preparation; publication is a separate approval.

## Decision

OMH supplies versioned content and contracts. ATM's existing Rust CLI performs
official distribution without requiring the desktop application. OMH supplies
no installation CLI, Python installable package, second engine, or maintained
hook content. Users distributing through other shell tools own those tools.

The historical 1.0.0 baseline is `e0ce46da5e1cbca5313a6db14401cdfa07b4d5a7`,
the last pre-Hub architecture with the old distribution mechanism and Watcher
collection hooks, including the evidence-reporting fix. The pure Hub is 1.1.0;
ATM remains application version 0.2.0 and binds exact content revision/digests.
Neither planned release is implied to exist by changing the source version.
The withdrawn 1.2.0 draft, its tag and assets are retained unchanged for recovery.

OMH 1.1.0 removes historical Watcher report reading, attribution compatibility,
state migration, collection and the skill-maintainer evidence/proposal pipeline.
The existing `mattpocock-skills:writing-for-agents` covers agent-guidance authoring;
it receives no new functionality or permission from this change.

The 29-skill composition retains doc-alignment, housekeeping and skill-compressor
as distinct maintenance workflows. Doc-alignment owns its audit scripts, profile
config, new report generation and commit/finding checkpoints. These are skill
resources, not a separate Watcher product. Its caller selects an explicit state
directory; no old state is discovered or migrated. Target repositories remain
read-only in audit mode, and repository owner commands require the existing trust
decision. Only the consumed standard-library `maintenance` and `workflow` Python
groups remain. Static installation needs no Python.

## Identifier and consumer migration

The explicit migration covers current maintenance catalog IDs, runtime bindings,
workflow references/checkers/templates, plugin attribution overlays, helper paths,
tests and current documentation. Maintenance IDs now derive directly from the
`maintenance` package. Current callers use `maintenance:housekeeping` and
`maintenance:doc-alignment`; the new bundle carries no historical aliases.

Doc helpers move from `runtimes/watcher/scripts/watcher_runtime/doc` to
`plugins/maintenance/skills/doc-alignment/scripts/doc_alignment`. Its dispatcher,
config and references move with the implementation. There is one current path;
no wrapper at the historical location forwards into the new skill.

Historical ADRs, source commits, real Home reports/logs and installed receipts
retain their identities. ATM's generic schemas, legacy import/ownership logic
and receipt-based retired-hook removal are not removed. Upgrading a Home is a
separate explicit import, source selection, plan and apply operation. An old
cache is never relabeled 1.1.0; rollback uses the preserved old source/receipts.

## Validation

Audit profile, new report/delta and read-only behavior tests move into maintenance
with their consumer. Old collector, historical attribution/report-reader and
state-migrator tests leave with the retired product capabilities. Tests preserve
the other skills' invocation and permission boundaries and verify that every
remaining runtime group has a current script consumer.

The shared pinned Rust exporter validates new package identities and exports an
exact revision. Isolated import checks 29 canonical skills, absent legacy runtime
and overlays, static CLI lifecycle without Python, and explicit optional venv
preparation. ATM package tests continue user-file, ownership, native projection
and offline-cache protection. Published-asset download and clean-fetch CI remain
gates after publication; no consumer lock to an unpublished asset may merge.

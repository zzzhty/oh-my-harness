# Maintenance skills

This plugin preserves three distinct interactive workflows:

- `doc-alignment`: audit and align current documentation and operational guidance.
- `housekeeping`: remove inventoried disposable artifacts while protecting user work.
- `skill-compressor`: reduce instruction size while preserving required behavior.

The audit and validation helpers belong to their consuming skills. Static skill
installation needs no Python, and preparing a payload runtime never enables hooks.

`doc-alignment` owns `skills/doc-alignment/scripts/audit_docs.py`, its sibling
`doc_alignment/` modules and `config/repos.example.json`. Resolve that skill's
directory before running `"$atm_tooling_python" -B scripts/audit_docs.py`, with
`atm_tooling_python="$ATM_PAYLOAD_PYTHON"` set to the exact prepared `maintenance`
interpreter. Set an explicit `--state-dir` or `DOC_ALIGNMENT_STATE_DIR` outside the
audited repository; there is no automatic discovery or migration of Watcher state.
The helper retains fresh audit/report generation, configured profiles and commit
thresholds while target repositories stay read-only. See its `references/doc-audit.md`.

OMH 1.1.0 removes `skill-maintainer` and its exclusive historical evidence and
proposal pipeline. Use the existing `mattpocock-skills:writing-for-agents` skill
for authoring or revising agent guidance. Its behavior and invocation policy are
unchanged. The three maintenance skills retain their separate permission boundaries.

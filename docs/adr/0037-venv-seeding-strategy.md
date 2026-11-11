---
status: accepted
---

# Venv seeding strategy

Hosts increasingly default to uv-managed CPython — a relocated build whose
baked-in compile prefix does not exist locally. Such interpreters locate the
standard library through their real location, so a `venv --copies` seeding
(which OMH prefers: the runtime keeps working after the base interpreter is
removed) produces copied executables that die with "Failed to import
encodings". Refusing those interpreters would force every uv host off the
default experience, so they become first-class instead.

**Decision: verification-gated strategy selection at creation time.**
`prepare` seeds with `--copies` and probes the result in place; if the probe
fails, the venv's `python*` executables are removed and a `--symlinks`
seeding is created and probed the same way. Either strategy passing
verification is accepted — the winning strategy is recorded as `seed` in the
`.omh-runtime.json` marker — and only failure of both is a hard failure with
the process tail. Nothing falls back silently: verification gates both
strategies. `install.sh` mirrors the same two-strategy probe for the
bootstrap interpreter.

**Trade-off, accepted and visible.** A symlinked runtime depends on the base
interpreter's continued existence; uv may prune its interpreter directories on
upgrade. That breakage is detected by the next `verify`/`prepare`, which
refuses with the standard diagnosis and asks for a new bootstrap interpreter —
an explicit, actionable failure, not silent decay. Standard (non-relocated)
interpreters keep the private-copies behavior unchanged: the fallback only
triggers when a copies-seeded venv fails its probe.

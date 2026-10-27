# Oh My Harness Repository Instructions

## Authority Map

- `agents/global-instructions.md` owns the global behavior distributed to every selected harness. This root file owns only repository-local routing and deltas; keep global policy out of it.
- `content-manifest.json` owns exported content, compositions and runtime requirements. ATM owns target policy and installation; use its pinned Rust export/import core, never add a second installer.
- `plugins/*/skills/*/SKILL.md` is the canonical repository skill catalog. Plugin manifests, marketplace state, generated metadata, caches, and harness directories are projections.
- `README.md` owns content release and validation entry points. Architecture decisions and migration invariants belong in `docs/adr/`.

## Conditional Guidance

- Before renaming, replacing, or migrating any repository-owned identifier, path, field, event, skill, or instruction identity, read `docs/agents/internal-identifier-evolution.md` and classify every scoped match before editing.
- When changing a plugin's packaged content, finish all source edits first, run the owning tests, then run `scripts/update_plugin_generations.py` once and validate the resulting single current identity.
- For anything under `plugins/mattpocock-skills/`, follow its scoped `AGENTS.md` for the locally maintained selection and upstream attribution.

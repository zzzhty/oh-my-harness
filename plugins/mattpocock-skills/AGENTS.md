## Matt Pocock upstream mirror

- Treat every file under `skills/` as an unchanged, upstream-owned mirror. Do not edit, translate, compress, reformat, patch, or generate files inside that tree.
- Generic requests to modify or improve local skills exclude this plugin's `skills/` tree. Apply them only to repository-owned skills unless the user explicitly requests an upstream sync.
- Keep local Codex adaptation outside `skills/`: the `.codex-plugin` wrapper and Watcher metadata, version/distribution identity, this instruction file, the generated README, and repository-owned updater/checker/tests.
- Update the mirror only through `scripts/update_mattpocock_skills.py`. Do not manually edit or rebaseline `.codex-plugin/upstream-lock.json`.
- If upstream-lock validation reports drift, stop before replacement and inspect the scoped Git diff. Restore the mirror or route the behavior change upstream; do not preserve it through a shim, alias, fallback, or local source patch.

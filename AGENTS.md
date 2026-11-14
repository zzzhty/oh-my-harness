# Oh My Harness Repository Instructions

## Authority Map

- `agents/global-instructions.md` owns the global behavior distributed to every selected harness. This root file owns only repository-local routing and deltas; keep global policy out of it.
- `content-manifest.json` owns exported content, compositions and runtime requirements. OMH owns the standalone Python distributor and the shared runtime protocol as its sole distribution channel; the retired Rust export/import core is historical. See ADR 0031 (and ADR 0030 for runtime bindings) before changing ownership or runtime bindings.
- `plugins/*/skills/*/SKILL.md` is the canonical repository skill catalog. Plugin manifests, marketplace state, generated metadata, caches, and harness directories are projections.
- `README.md` owns content release and validation entry points. Architecture decisions and migration invariants belong in `docs/adr/`.

## Conditional Guidance

- Before renaming, replacing, or migrating any repository-owned identifier, path, field, event, skill, or instruction identity, read `docs/agents/internal-identifier-evolution.md` and classify every scoped match before editing.
- When changing a plugin's packaged content, finish all source edits first, run the owning tests, then run `scripts/update_plugin_generations.py` once and validate the resulting single current identity.
- For anything under `plugins/mattpocock-skills/`, follow its scoped `AGENTS.md` for the locally maintained selection and upstream attribution.

## Rules and what enforces them

After a change, run `python scripts/check_architecture.py` before finishing. CI runs that same command. It exits 1 on errors; file-length warnings do not fail the run. Do not raise `scripts/architecture_baseline.json` to admit a new violation.

| Rule | Enforced by |
| --- | --- |
| Explicit UTF-8 on Python text calls and PowerShell `Get-Content` | `scripts/check_architecture.py` (`text-io-utf8`). A file may not exceed its count in the baseline. New calls use `encoding="utf-8"`: `omh_runtime.launch` for path text, `doc_alignment.audit_repo.run_git` for subprocess, `plugins/workflow/scripts/run.ps1` for `Get-Content`. |
| CLI stdout and stderr reconfigured to UTF-8 | `scripts/check_architecture.py` (`cli-stdout-utf8`) on `omh.standalone.main` and `audit_docs.main` |
| Python files warn past 500 lines, fail past 1000, and baselined files may not grow | `scripts/check_architecture.py` (`file-length`). Ceilings are in the baseline. Put new behavior in a new module. |
| Closed commands use `parse_args`; `parse_known_args` only in `omh_runtime.main` | `scripts/check_architecture.py` (`closed-argv`) |
| `HARNESS_ROOTS`, `INSTRUCTIONS`, and `--harness` choices stay one set; `omp`, `copilot`, and `gemini` are not canonical | `scripts/check_architecture.py` (`harness-identity`) reading `omh/standalone.py` |
| `omh/` imports only the standard library | `scripts/check_architecture.py` (`distributor-stdlib`). Developer packages stay in `requirements.txt` and `scripts/`. |
| Pyflakes and Bugbear findings | `ruff.toml` through the same script (`ruff`). The baseline lists the grandfathered findings exactly. |
| Plugin generation identity | `python scripts/check_plugin_generations.py` |
| Packaged content edits | Owning tests, then `scripts/update_plugin_generations.py` once. Do not edit generations by hand. |
| Whitespace | `git diff --check` |
| Behavior | The `unittest` suites in `README.md` |

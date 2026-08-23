# My Codex

Registry-managed distribution of personal development skills and global instructions across coding harnesses, including the local Codex marketplace.

This repository is the development mainline for the plugins and personal Codex configuration listed below. Edit the source copies here, then reinstall or refresh the Codex plugin cache when a change should be available to new Codex sessions.

`AGENTS.md` is also maintained here and distributed to the global instructions path owned by the selected harness.

## Plugins

- `watcher`: observes Codex skill usage, audits documentation drift, and packages `doc-alignment`, `housekeeping`, `skill-maintainer`, and `skill-compressor` workflows.
- `workflow`: packages reusable workflow skills, including continuation-ready long-running goal plans with frozen YOLO non-stops and runtime hard stops, SOP execution harnesses, prompt/strategy loops, explicit subagent orchestration, and standalone summaries.
- `mattpocock-skills`: packages the unchanged published skill tree and native Codex metadata from `mattpocock/skills`.

The old `plugins/doc-watcher` and `plugins/skill-watcher` source trees were removed after the Watcher migration. Git history remains the recovery path for those retired plugin sources.

## Harness Distributions

`plugins/*/skills/*/SKILL.md` is the canonical skill catalog. The frontmatter `name` is the bare catalog name even when a physical directory has a different name; marketplace state, plugin caches, and user-level directories are projections, not source authority.

Every refresh and closure check selects one complete distribution with `--harness`. The strict JSON authority is `.agents/harnesses/registry.json`, validated by `.agents/harnesses/registry.schema.json` and `scripts/harness_registry.py`. The registry owns root resolution, the skills driver, global instructions, platform materialization, reconciliation, excluded skill roots, and optional runtime extras. The default is `codex`.

| Harness | Skills | Global instructions |
| --- | --- | --- |
| `codex` | Exact `.agents/plugins/install-manifest.json` package set through Codex marketplace install | `$CODEX_HOME/AGENTS.md` |
| `zcode` | `~/.zcode/skills` projection | `~/.zcode/AGENTS.md` |
| `claude-code` | `${CLAUDE_CONFIG_DIR:-~/.claude}/skills` projection | `${CLAUDE_CONFIG_DIR:-~/.claude}/CLAUDE.md` |
| `copilot-cli` | `${COPILOT_HOME:-~/.copilot}/skills` projection | `${COPILOT_HOME:-~/.copilot}/copilot-instructions.md` |
| `gemini-cli` | `${GEMINI_CLI_HOME:-$HOME}/.gemini/skills` projection | configured `context.fileName`, otherwise `GEMINI.md` |
| `opencode` | `~/.config/opencode/skills` projection | `~/.config/opencode/AGENTS.md` |

`codex` deliberately uses the existing marketplace/plugin driver, not `$CODEX_HOME/skills`. Its schema-v4 install manifest declares `harness: "codex"` and must cover every package that owns canonical skills. Each package manifest exposes exactly `./skills/`; source and cache identities are checked against the repository catalog. Plugin activation rolls back newly attempted packages when closure fails.

Directory projections use directory symlinks on POSIX and directory junctions on Windows. They manage only entries proven to target canonical skill directories in this checkout, prune only repository-owned stale links, preserve unrelated user skills, and refuse unmanaged same-name entries. A retry may recover an exact canonical empty ordinary directory left by an interrupted link creation; recovery rejects non-empty directories and reparse points and uses only non-recursive `rmdir()`. The unchanged `plugins/mattpocock-skills/skills/` mirror is never rewritten.

Instructions are part of every harness plan. A missing target requires confirmation, and `--yes` may confirm its creation. Replacing a different existing file always requires live confirmation; `--yes` does not authorize replacement. Directories, unknown reparse points, unmanaged symlinks, configured shadow files, and source or target changes after preflight fail closed. POSIX Codex instructions use a symlink; other current entries use atomic copies.

`~/.agents/skills` is an excluded skill root, not a harness: it cannot distribute `AGENTS.md` as part of the same bundle and may conflict with product-specific discovery. Refresh fails before mutation, and closure fails, when it contains a repository catalog identity or stale repository-owned projection. Unrelated user skills remain untouched. Codex marketplace packages expose `${plugin}:${catalog-name}`; other harnesses retain their native identity behavior, so a bare prompt reference is not a promise of one cross-harness runtime identity.

Source-package validation is independent of the selected harness:

```bash
PLUGIN_VALIDATOR="${PLUGIN_VALIDATOR:-${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py}"
"${CODEX_HOME:-$HOME/.codex}/venvs/my-codex/bin/python" "$PLUGIN_VALIDATOR" plugins/watcher
"${CODEX_HOME:-$HOME/.codex}/venvs/my-codex/bin/python" "$PLUGIN_VALIDATOR" plugins/workflow
"${CODEX_HOME:-$HOME/.codex}/venvs/my-codex/bin/python" scripts/update_mattpocock_skills.py --validate-only
```

Refresh and closure use the same selector:

```bash
"${CODEX_HOME:-$HOME/.codex}/venvs/my-codex/bin/python" scripts/refresh_my_codex.py --harness codex
"${CODEX_HOME:-$HOME/.codex}/venvs/my-codex/bin/python" scripts/check_my_codex.py --harness codex
"${CODEX_HOME:-$HOME/.codex}/venvs/my-codex/bin/python" scripts/refresh_my_codex.py --harness zcode
```

`scripts/sync_agents_skills.py` is the low-level directory-projection tool. It has no default target. Use the harness-aware refresh entry point for normal activation; supply the exact root when inspecting an already selected projection:

```bash
"${CODEX_HOME:-$HOME/.codex}/venvs/my-codex/bin/python" scripts/sync_agents_skills.py --target-root "$HOME/.zcode/skills" --check --prune
"${CODEX_HOME:-$HOME/.codex}/venvs/my-codex/bin/python" scripts/refresh_my_codex.py
```

To retire repository-owned links from the excluded `~/.agents/skills` root, preview first and then run the separately confirmed cleanup. It removes only links revalidated against this checkout and exact canonical empty interruption residues; unmanaged canonical names and a linked/reparse/mount target root remain hard stops:

```bash
"${CODEX_HOME:-$HOME/.codex}/venvs/my-codex/bin/python" scripts/sync_agents_skills.py --target-root "$HOME/.agents/skills" --remove-managed --dry-run
"${CODEX_HOME:-$HOME/.codex}/venvs/my-codex/bin/python" scripts/sync_agents_skills.py --target-root "$HOME/.agents/skills" --remove-managed --yes
```

Windows PowerShell:

```powershell
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$ToolingPython = Join-Path $CodexHome "venvs\my-codex\Scripts\python.exe"
& $ToolingPython scripts\sync_agents_skills.py --target-root (Join-Path $HOME ".agents\skills") --remove-managed --dry-run
& $ToolingPython scripts\sync_agents_skills.py --target-root (Join-Path $HOME ".agents\skills") --remove-managed --yes
```

## Matt Pocock Upstream Sync

The repo-owned updater for the `mattpocock-skills` package lives outside the Watcher runtime. From the repository root, run:

```bash
python3 scripts/bootstrap_tooling_env.py
"${CODEX_HOME:-$HOME/.codex}/venvs/my-codex/bin/python" scripts/update_mattpocock_skills.py
```

By default it selects the latest upstream semantic-version tag, clones the source under `~/.codex/sources`, and copies every skill published by the upstream manifest without content rewrites or omissions. It then regenerates only the local plugin wrapper and Watcher metadata, updates the cachebuster, and validates byte parity plus upstream's native Codex invocation contract. Use `--source-dir <upstream-checkout> --tag <vX.Y.Z>` to sync from an existing checkout, or `--validate-only` to check the currently packaged plugin without fetching or changing files.

Never edit `plugins/mattpocock-skills/skills/` directly. Its updater-owned upstream lock makes local drift fail validation and blocks an upstream refresh before that drift can be overwritten; local adaptation belongs only in the plugin wrapper, Watcher metadata, and repository-owned tooling around the unchanged mirror.

After reviewing the source diff, reconcile the complete Codex harness distribution:

```bash
"${CODEX_HOME:-$HOME/.codex}/venvs/my-codex/bin/python" scripts/refresh_my_codex.py --harness codex
```

## Orchestration Workflow

Use the `workflow` plugin's `$orchestrate-subagents` skill when the user invokes
it or explicitly asks for bounded Codex subagents or parallel agents. Ordinary
environment-authorized delegation does not invoke this skill by itself:

```text
Use $orchestrate-subagents to review this branch against main.
```

The same workflow can be requested in natural language, such as `Use parallel
subagents to review this branch against main.` The full workflow lives in
`plugins/workflow/skills/orchestrate-subagents/SKILL.md`. Keep root docs
limited to install, validation, and entry-point guidance.

The orchestration workflow uses Codex's built-in subagent roles, such as
`explorer`, `default`, and `worker`, with task-local assignment labels like
`code-mapper` and `test-verifier`. The managed support file lives in
`agents/operating-principles.md`; repo-facing notes live in
`docs/codex-agent-support.md`. Local custom-agent preset TOML is not maintained
in this repository.

## Local Install

For routine install or refresh, prefer the platform wrapper in
[Harness Refresh And Hook Debugging](#harness-refresh-and-hook-debugging). The manual
commands below are a fallback and should mirror
`.agents/plugins/install-manifest.json`.

Unix:

```bash
export MY_CODEX_ROOT="${MY_CODEX_ROOT:-$PWD}"
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export MY_CODEX_PYTHON="${MY_CODEX_PYTHON:-$CODEX_HOME/venvs/my-codex/bin/python}"
export PLUGIN_VALIDATOR="${PLUGIN_VALIDATOR:-$CODEX_HOME/skills/.system/plugin-creator/scripts/validate_plugin.py}"

codex plugin marketplace add "$MY_CODEX_ROOT"
codex plugin add watcher@my-codex
codex plugin add workflow@my-codex
codex plugin add mattpocock-skills@my-codex
```

Windows PowerShell:

```powershell
$env:MY_CODEX_ROOT = (Get-Location).Path
$env:CODEX_HOME = "$env:USERPROFILE\.codex"
$env:MY_CODEX_PYTHON = "$env:CODEX_HOME\venvs\my-codex\Scripts\python.exe"
$env:PLUGIN_VALIDATOR = "$env:CODEX_HOME\skills\.system\plugin-creator\scripts\validate_plugin.py"

Set-Location $env:MY_CODEX_ROOT
codex plugin marketplace add $env:MY_CODEX_ROOT
codex plugin add watcher@my-codex
codex plugin add workflow@my-codex
codex plugin add mattpocock-skills@my-codex
```

Install directly from this repository checkout. Do not clone or copy the repo to an extra local path just to install the marketplace.

Use the harness-aware refresh command for global instructions. It resolves the target from the registry and applies the required confirmation policy; do not force-copy over an existing instructions file.

## Tooling Runtime

Shared my-codex Python tooling uses a runtime venv outside plugin source trees:

Unix:

```bash
python3 scripts/bootstrap_tooling_env.py
```

Windows PowerShell:

```powershell
py scripts\bootstrap_tooling_env.py
```

The shared interpreter is:

```text
$MY_CODEX_PYTHON
```

Use this interpreter for Codex hooks, Watcher maintenance scripts, and skill/plugin validation that needs my-codex tooling dependencies.

## Windows/Unix Compatibility Notes

This repository is the Windows-oriented checkout of the original Unix-first `zzzhty/my-codex` workflow. The compatibility surface is intentionally narrow: it does not add separate plugins, skills, manifests, or top-level modules for Windows. Windows support lives in install documentation, shared tooling venv path selection, Watcher hook command generation, hook schema alignment, and Windows-aware error messages.

Key platform differences:

- Unix venv Python: `$CODEX_HOME/venvs/my-codex/bin/python`
- Windows venv Python: `$env:CODEX_HOME\venvs\my-codex\Scripts\python.exe`
- POSIX directory projections: directory symlinks
- Windows directory projections: directory junctions
- POSIX Codex instructions: symlink into `$CODEX_HOME/AGENTS.md`
- Windows and current non-Codex instructions: atomic copy into the registry-selected target

Windows skill projection does not require file-symlink privilege. The projection helper validates junction targets and uses a strictly validated non-recursive `rmdir()` only for an empty ordinary directory left by an interrupted link creation.

`scripts/bootstrap_tooling_env.py` is cross-platform and selects the venv interpreter by platform:

- Windows: `Scripts\python.exe`
- Unix: `bin/python`

The bootstrap resolves the selected base Python to its real executable before creating the venv. This prevents PATH aliases or uv-managed Python symlinks from producing a `pyvenv.cfg` that cannot locate the standard library. If an existing tooling venv cannot start, reports the wrong prefix, or was created from a different base interpreter, bootstrap rebuilds it and restores the previous directory if creation or dependency validation fails. `--dry-run` performs the same read-only health preflight and prints whether a rebuild would occur.

If a Watcher script fails because `PyYAML` is missing, refresh the shared tooling venv from the repository root:

Unix:

```bash
python3 scripts/bootstrap_tooling_env.py
```

Windows PowerShell:

```powershell
py scripts\bootstrap_tooling_env.py
```

## Harness Refresh And Hook Debugging

Refresh the selected harness with the platform wrapper:

Unix:

```bash
scripts/upgrade_my_codex.sh
# alternatives: --harness zcode, --harness claude-code, --harness copilot-cli, ...
# add --yes to confirm a missing instructions target or an exact Codex prune plan
```

Windows PowerShell:

```powershell
.\scripts\upgrade_my_codex.ps1
# alternatives: -Harness zcode, -Harness claude-code, -Harness copilot-cli, ...
# add -Yes to confirm a missing instructions target or an exact Codex prune plan
```

When no selector is supplied, the wrappers leave the choice to the registry default (currently `codex`). An explicit harness id is forwarded unchanged to refresh and check, and the bootstrap Python is used only to create or refresh the tooling venv. Harness defaults, choices, and paths are not duplicated in either wrapper. Global instructions are preflighted before skills or marketplace mutation.

For `codex`, refresh validates the complete manifest, marketplace policy, nested source-package containment, current cache shape, and marketplace source binding before mutation. Git installation is pinned to the validated checkout commit; explicit Git failures stop, while only automatic Git selection may fall back to the exact local checkout. Codex CLI resolution uses explicit `--codex`/`-CodexPath`, `CODEX_BIN`, `PATH`, standalone installs, then platform-managed fallbacks.

Codex stale-plugin reconciliation is on by default because the registry declares `managed-stale`. Only configured entries and cache directories inside the selected marketplace namespace are eligible. A nonempty exact plan is printed before mutation and requires confirmation; `--yes` or `-Yes` may confirm it. An enabled plugin visible only through the CLI and not proven by managed config/cache remains a hard failure. Other harnesses use only their registry-selected directory projection and never prune Codex plugins.

`--yes` never authorizes replacement of a different existing instructions file. That action always requires a live confirmation after the target type and content digest are shown.

Migrate legacy Watcher runtime roots explicitly before final checks:

```bash
"${CODEX_HOME:-$HOME/.codex}/venvs/my-codex/bin/python" plugins/watcher/scripts/watcher migrate-state --dry-run
"${CODEX_HOME:-$HOME/.codex}/venvs/my-codex/bin/python" plugins/watcher/scripts/watcher migrate-state --apply
```

This moves `$CODEX_HOME/skill-watcher/` to `$CODEX_HOME/watcher/skill/` and `$CODEX_HOME/doc-watcher/` to `$CODEX_HOME/watcher/doc/`. It refuses to merge when a target directory already exists.

Direct Python entry-point usage remains supported after `scripts/bootstrap_tooling_env.py` has created the shared tooling venv:

```bash
"${CODEX_HOME:-$HOME/.codex}/venvs/my-codex/bin/python" scripts/refresh_my_codex.py
# alternative: "${CODEX_HOME:-$HOME/.codex}/venvs/my-codex/bin/python" scripts/refresh_my_codex.py --harness zcode
```

Windows PowerShell:

```powershell
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$ToolingPython = Join-Path $CodexHome "venvs\my-codex\Scripts\python.exe"
& $ToolingPython scripts\refresh_my_codex.py
# alternative: & $ToolingPython scripts\refresh_my_codex.py --harness zcode
```

Run the final closure check after refresh:

Unix:

```bash
"${CODEX_HOME:-$HOME/.codex}/venvs/my-codex/bin/python" scripts/check_my_codex.py
# alternative: "${CODEX_HOME:-$HOME/.codex}/venvs/my-codex/bin/python" scripts/check_my_codex.py --harness zcode
```

Windows PowerShell:

```powershell
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$ToolingPython = Join-Path $CodexHome "venvs\my-codex\Scripts\python.exe"
& $ToolingPython scripts\check_my_codex.py
# alternative: & $ToolingPython scripts\check_my_codex.py --harness zcode
```

The check script verifies the selected harness skills and instructions plus the excluded-root policy. Codex closure also verifies the exact marketplace/source package set, manifest `./skills/` projection, enabled CLI state, cache identities, tooling Python, Watcher hooks, subagent support, source plugin validation, and Watcher doctor. Native directory harnesses verify their selected projection and instructions. The check is read-only.

After the helper refreshes hooks, open `/hooks` in Codex and trust the refreshed Watcher skill command hook definitions. Codex skips non-managed command hooks until the exact hook definition is trusted.

The refresh preflights global instructions before distribution mutation and verifies them after an atomic write. The final closure check reads the same registry-resolved plan.

Manual Windows PowerShell marketplace reinstall checklist:

```powershell
$env:MY_CODEX_ROOT = (Get-Location).Path
$env:CODEX_HOME = "$env:USERPROFILE\.codex"
$env:MY_CODEX_PYTHON = "$env:CODEX_HOME\venvs\my-codex\Scripts\python.exe"
$env:PLUGIN_VALIDATOR = "$env:CODEX_HOME\skills\.system\plugin-creator\scripts\validate_plugin.py"

py scripts\bootstrap_tooling_env.py
codex plugin marketplace add $env:MY_CODEX_ROOT
codex plugin add watcher@my-codex
codex plugin add workflow@my-codex
codex plugin add mattpocock-skills@my-codex
```

Watcher installs user-level Codex command hooks in `$CODEX_HOME/hooks.json`. It does not use plugin manifest hooks and does not modify `.codex-plugin/plugin.json`.

The generated hook handlers observe:

- `SessionStart`
- `UserPromptSubmit`
- `PostToolUse`
- `Stop`

`SessionStart` refreshes `$CODEX_HOME/watcher/skill/skill-metadata-cache.json` and is not persisted by default. The skill inventory comes only from the repository catalog under the explicit `--repo-root`; marketplace metadata, plugin manifests, plugin cache, and the runtime cache are not catalog authorities. Repository `.codex-plugin/skill-watcher.json` files are non-callable attribution overlays for namespaced Watcher identities, roles, aliases, supporting relationships, logical groups, and legacy mappings. Missing repository source, catalog failures, unknown overlay schemas, and invalid references fail visibly.

Expected command-hook schema:

```json
{
  "type": "command",
  "async": false,
  "command": "... watcher skill observe --repo-root <my-codex-root>",
  "timeoutSec": 10,
  "statusMessage": "Watcher skill: observe <event>"
}
```

Windows hook commands are rendered with Windows command-line quoting and should point at `Scripts\python.exe`. Unix hook commands use POSIX quoting and should point at `bin/python`.

Install or refresh Watcher skill hooks from the source checkout:

Unix:

```bash
"$MY_CODEX_PYTHON" "$MY_CODEX_ROOT/plugins/watcher/scripts/watcher" skill install-hook --repo-root "$MY_CODEX_ROOT" --dry-run
"$MY_CODEX_PYTHON" "$MY_CODEX_ROOT/plugins/watcher/scripts/watcher" skill install-hook --repo-root "$MY_CODEX_ROOT" --apply
```

Windows PowerShell:

```powershell
$python = "$env:USERPROFILE\.codex\venvs\my-codex\Scripts\python.exe"
& $python "$env:MY_CODEX_ROOT\plugins\watcher\scripts\watcher" skill install-hook --repo-root $env:MY_CODEX_ROOT --dry-run --python $python
& $python "$env:MY_CODEX_ROOT\plugins\watcher\scripts\watcher" skill install-hook --repo-root $env:MY_CODEX_ROOT --apply --python $python
```

After applying hooks, open `/hooks` in Codex and trust the Watcher skill command hook definitions. Codex skips non-managed command hooks until the exact hook definition is trusted.

Runtime Watcher skill state is written under `$CODEX_HOME/watcher/skill/`:

```text
logs/events.jsonl
reports/
proposals/
snapshots/
rejected/
backups/
turns/
```

The hook adapter records summaries, lengths, hashes, tool names, outcomes, and redacted metadata. It does not store full prompts, full assistant messages, full shell commands, full tool responses, file contents, secrets, or private business data.

Watcher monitors the canonical repository skill set by default and can be narrowed with `WATCHER_SKILL_MONITORED_SKILLS`. Installed hooks embed the explicit repository root, so repository and harness-projection execution share the same source runtime and do not depend on plugin cache or working-directory inference. Because Codex hook payloads do not provide a stable native skill id, attribution is recorded as `provided`, `prompt_mention`, `assistant_announcement`, or `unknown`. Successful tool calls are counted in transient turn state but are not persisted as individual records; failed tool calls and one `turn_summary` are persisted for active monitored skills.

When the user explicitly invokes a monitored skill, the adapter stores a redacted `user_skill_context` summary/hash for the extra information mentioned with that skill. This is intended as future skill-improvement evidence without retaining the raw prompt.

## Validation

Unix:

```bash
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
python3 -m json.tool .agents/plugins/install-manifest.json >/dev/null
python3 -m json.tool .agents/harnesses/registry.json >/dev/null
python3 -m json.tool .agents/harnesses/registry.schema.json >/dev/null
"$MY_CODEX_PYTHON" "$PLUGIN_VALIDATOR" "$MY_CODEX_ROOT/plugins/watcher"
"$MY_CODEX_PYTHON" "$PLUGIN_VALIDATOR" "$MY_CODEX_ROOT/plugins/workflow"
"$MY_CODEX_PYTHON" "$MY_CODEX_ROOT/scripts/update_mattpocock_skills.py" --validate-only
"$MY_CODEX_PYTHON" -m unittest discover -s tests -p 'test_*.py' -v
```

Windows PowerShell:

```powershell
& $env:MY_CODEX_PYTHON -m json.tool .agents\plugins\marketplace.json | Out-Null
& $env:MY_CODEX_PYTHON -m json.tool .agents\plugins\install-manifest.json | Out-Null
& $env:MY_CODEX_PYTHON -m json.tool .agents\harnesses\registry.json | Out-Null
& $env:MY_CODEX_PYTHON -m json.tool .agents\harnesses\registry.schema.json | Out-Null
& $env:MY_CODEX_PYTHON $env:PLUGIN_VALIDATOR "$env:MY_CODEX_ROOT\plugins\watcher"
& $env:MY_CODEX_PYTHON $env:PLUGIN_VALIDATOR "$env:MY_CODEX_ROOT\plugins\workflow"
& $env:MY_CODEX_PYTHON "$env:MY_CODEX_ROOT\scripts\update_mattpocock_skills.py" --validate-only
& $env:MY_CODEX_PYTHON -m unittest discover -s tests -p 'test_*.py' -v
```

## Layout

```text
.agents/plugins/marketplace.json
.agents/plugins/install-manifest.json
.agents/harnesses/registry.json
.agents/harnesses/registry.schema.json
plugins/
  watcher/
  workflow/
  mattpocock-skills/
requirements.txt
scripts/bootstrap_tooling_env.py
scripts/check_my_codex.py
scripts/harness_registry.py
scripts/harness_runtime.py
scripts/refresh_my_codex.py
scripts/sync_agents_skills.py
scripts/sync_codex_agents.py
scripts/sync_harness_instructions.py
scripts/update_mattpocock_skills.py
scripts/upgrade_my_codex.ps1
scripts/upgrade_my_codex.sh
tests/
agents/
```

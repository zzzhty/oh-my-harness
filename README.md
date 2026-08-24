# Oh My Harness

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

`codex` deliberately uses the existing marketplace/plugin driver, not `$CODEX_HOME/skills`. Its exact-shape install manifest declares `harness: "codex"` and must cover every package that owns canonical skills. The manifest has no independent schema-version field; its repository-owned reader rejects missing or unsupported fields. Each package manifest exposes exactly `./skills/`; source and cache identities are checked against the repository catalog. Plugin activation rolls back newly attempted packages when closure fails.

## Lifecycle Manager

`install.sh` and `install.ps1` are bootstrap-only. After the first installation,
all supported lifecycle management goes through `omh`:

```bash
omh install [HARNESS...]
omh refresh [HARNESS...]
omh refresh [HARNESS...] --repair
omh remove HARNESS... | --all
omh update --check
omh update
omh status
omh check
omh doctor
omh manager repair
omh manager uninstall
```

`omh refresh` never fetches remote source; it reconciles the current managed
release. `omh update` is the explicit remote transition and defaults to the
stable release channel, while `--channel main` follows `origin/main`.
Same-version content drift remains a hard failure during ordinary refresh and is
re-materialized only by explicit `--repair`. `remove` deletes only resources
whose manager ownership is proven.

The immutable `state/install.json` remains the initial bootstrap receipt.
Rolling manager state is kept in `manager.json`, `desired.json`, per-harness
receipts, and an update operation journal. Mutating lifecycle commands share one
manager lock.

## Release And Plugin Distribution Identity

`VERSION` is the canonical `oh-my-harness` release version. First-party plugins use that value as their base version; an upstream-locked mirror keeps its upstream base version. Every complete plugin version ends in `+codex.<generation>`, where `generation` is derived from the canonical plugin package content rather than a timestamp. `.agents/plugins/distribution-identity.json` records the full per-package SHA-256 values and the release-level bundle identity.

Use the repository-owned tools instead of editing cachebusters manually:

```bash
python3 scripts/update_plugin_generations.py
python3 scripts/check_plugin_generations.py
```

A source edit without a regenerated identity fails before Codex mutation. An already installed plugin is skipped only when its full cache content identity matches the source; same-version drift fails closed instead of silently retaining stale content.

Directory projections use directory symlinks on POSIX and directory junctions on Windows. They manage only entries proven to target canonical skill directories in this checkout, prune only repository-owned stale links, preserve unrelated user skills, and refuse unmanaged same-name entries. A retry may recover an exact canonical empty ordinary directory left by an interrupted link creation; recovery rejects non-empty directories and reparse points and uses only non-recursive `rmdir()`. The unchanged `plugins/mattpocock-skills/skills/` mirror is never rewritten.

Instructions are part of every harness plan. A missing target requires confirmation, and `--yes` may confirm its creation. Replacing a different existing file always requires live confirmation; `--yes` does not authorize replacement. Directories, unknown reparse points, unmanaged symlinks, configured shadow files, and source or target changes after preflight fail closed. POSIX Codex instructions use a symlink; other current entries use atomic copies.

`~/.agents/skills` is an excluded skill root, not a harness: it cannot distribute `AGENTS.md` as part of the same bundle and may conflict with product-specific discovery. Refresh fails before mutation, and closure fails, when it contains a repository catalog identity or stale repository-owned projection. Unrelated user skills remain untouched. Codex marketplace packages expose `${plugin}:${catalog-name}`; other harnesses retain their native identity behavior, so a bare prompt reference is not a promise of one cross-harness runtime identity.

Source-package validation is independent of the selected harness:

```bash
PLUGIN_VALIDATOR="${PLUGIN_VALIDATOR:-${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py}"
"${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python" "$PLUGIN_VALIDATOR" plugins/watcher
"${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python" "$PLUGIN_VALIDATOR" plugins/workflow
"${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python" scripts/update_mattpocock_skills.py --validate-only
"${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python" scripts/check_plugin_generations.py
```

The public lifecycle commands own refresh and closure; the Python helpers remain lower-level implementation surfaces:

```bash
omh refresh codex
omh check codex
omh refresh zcode
```

`scripts/sync_agents_skills.py` is the low-level directory-projection tool. It has no default target. Use the harness-aware refresh entry point for normal activation; supply the exact root when inspecting an already selected projection:

```bash
"${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python" scripts/sync_agents_skills.py --target-root "$HOME/.zcode/skills" --check --prune
"${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python" scripts/refresh_harness.py
```

To retire repository-owned links from the excluded `~/.agents/skills` root, preview first and then run the separately confirmed cleanup. It removes only links revalidated against this checkout and exact canonical empty interruption residues; unmanaged canonical names and a linked/reparse/mount target root remain hard stops:

```bash
"${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python" scripts/sync_agents_skills.py --target-root "$HOME/.agents/skills" --remove-managed --dry-run
"${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python" scripts/sync_agents_skills.py --target-root "$HOME/.agents/skills" --remove-managed --yes
```

Windows PowerShell:

```powershell
$ManagerHome = if ($env:OH_MY_HARNESS_HOME) { $env:OH_MY_HARNESS_HOME } else { Join-Path $HOME ".oh-my-harness" }
$ToolingPython = Join-Path $ManagerHome "venv\Scripts\python.exe"
& $ToolingPython scripts\sync_agents_skills.py --target-root (Join-Path $HOME ".agents\skills") --remove-managed --dry-run
& $ToolingPython scripts\sync_agents_skills.py --target-root (Join-Path $HOME ".agents\skills") --remove-managed --yes
```

## Matt Pocock Upstream Sync

The repo-owned updater for the `mattpocock-skills` package lives outside the Watcher runtime. From the repository root, run:

```bash
python3 scripts/bootstrap_tooling_env.py
"${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python" scripts/update_mattpocock_skills.py
```

By default it selects the latest upstream semantic-version tag, clones the source under `~/.codex/sources`, and copies every skill published by the upstream manifest without content rewrites or omissions. It then regenerates only the local plugin wrapper and Watcher metadata, regenerates the distribution identity, and validates byte parity plus upstream's native Codex invocation contract. Use `--source-dir <upstream-checkout> --tag <vX.Y.Z>` to sync from an existing checkout, or `--validate-only` to check the currently packaged plugin without fetching or changing files.

Never edit `plugins/mattpocock-skills/skills/` directly. Its updater-owned upstream lock makes local drift fail validation and blocks an upstream refresh before that drift can be overwritten; local adaptation belongs only in the plugin wrapper, Watcher metadata, and repository-owned tooling around the unchanged mirror.

After reviewing the source diff, reconcile the complete Codex harness distribution:

```bash
"${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python" scripts/refresh_harness.py --harness codex
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

The initializer creates one manager-owned installation under
`${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}`. It clones the current checkout's
`remote.origin.url` into `repo/`, rebuilds `venv/`, writes `state/install.json`,
and creates ordinary `oh-my-harness` and `omh` launchers under `bin/`. Pass
`--repository <url>` only when the initializer is not running from a checkout
with a configured origin.

`state/install.json` records one initialization lifecycle and its source
snapshot. It has no independent schema-version field, and its recorded
repository and revision are an installation receipt rather than rolling Git
authority. Failed-install recovery accepts only the current exact receipt fields
and repository-defined lifecycle state entries. When an installation record exists, an installer launched from either
the managed repository or another checkout automatically attempts strict
recovery of the exact managed `repo/`; neither the invoking checkout nor the
process working directory becomes installation authority. A checkout already
moved to the managed path with no incomplete installation record still requires
the explicit `--adopt-current-checkout` option before the initializer may claim
it.

Unix:

```bash
./install.sh --harness codex --yes
export PATH="${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/bin:$PATH"
omh --help
```

To relocate an existing authoritative checkout into the manager home, move it
first and then adopt that exact path. This is a one-time migration, not an
alternate install layout. When Codex instructions still point to the former
checkout, `--migrate-from-repo` permits only that exact symlink to enter the
normal replacement flow; answer the live replacement prompt after inspecting
the printed source and target. `--yes` still cannot approve this replacement.

Unix example:

```bash
old_repo="$HOME/.codex/my-codex"
manager_home="${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}"
mkdir -p "$manager_home"
mv "$old_repo" "$manager_home/repo"
cd "$manager_home/repo"
./install.sh --adopt-current-checkout --migrate-from-repo "$old_repo" --migrate-marketplace --yes
```

Windows PowerShell example:

```powershell
$OldRepo = Join-Path $HOME ".codex\my-codex"
$ManagerHome = if ($env:OH_MY_HARNESS_HOME) { $env:OH_MY_HARNESS_HOME } else { Join-Path $HOME ".oh-my-harness" }
New-Item -ItemType Directory -Force -Path $ManagerHome | Out-Null
Move-Item -LiteralPath $OldRepo -Destination (Join-Path $ManagerHome "repo")
Set-Location -LiteralPath (Join-Path $ManagerHome "repo")
.\install.ps1 --adopt-current-checkout --migrate-from-repo $OldRepo -MigrateMarketplace --yes
```

If initialization stops after writing `status: "installing"`, rerun the
same installer command from either the original external checkout or the
managed checkout. `--adopt-current-checkout` is not required for recovery.
Re-pass any workflow authorization still required by the failed operation, such
as `--migrate-marketplace --yes` on Unix or `-MigrateMarketplace` on Windows
PowerShell. Automatic recovery always uses the managed `repo/` and proceeds only
after the recorded repository, revision, harness, owned paths, launcher bytes,
and venv shape all match exactly; otherwise it stops without changing manager
state. If repairing the failed installer required advancing that managed
checkout, pass `--resume-fast-forward` explicitly. This narrow recovery accepts
only a clean checkout whose `HEAD` equals the requested `origin/<ref>`, whose
remote still matches the recorded repository, and whose recorded revision is an
ancestor of `HEAD`; every other recorded field and owned path remains exact.

```bash
./install.sh --resume-fast-forward --migrate-marketplace --yes
```

```powershell
.\install.ps1 -MigrateMarketplace --resume-fast-forward --yes
```

Expected installer failures are written to standard error as `error: <reason>`
and return a nonzero exit code. A failing child command includes its command and
exit code. The PowerShell install and upgrade wrappers preserve that exit code;
an upgrade stage reports `error: <stage> failed with exit code <code>` after the
child diagnostic, and neither wrapper replaces the reason with a `throw`
exception stack. Interactive terminals render errors and exit codes in bright
red and required actions or confirmation prompts in bright yellow. Redirected
output remains plain text; set `NO_COLOR` to disable emphasis explicitly.

Windows PowerShell:

```powershell
.\install.ps1 --harness codex --yes
$env:PATH = "$env:USERPROFILE\.oh-my-harness\bin;$env:PATH"
omh --help
```

The initializer does not edit shell profiles or the machine-wide `PATH`. Add the
manager `bin/` directory through the shell configuration you own. Both command
names dispatch to the same manager-home bootstrap shim; `oh-my-harness` is canonical and
`omh` is the short form. Neither launcher is a symlink.

The managed installation layout is:

```text
~/.oh-my-harness/
├── bootstrap/
│   └── omh_bootstrap.py
├── repo/
├── venv/
├── bin/
│   ├── oh-my-harness
│   └── omh
└── state/
    ├── install.json
    ├── manager.json
    ├── desired.json
    ├── harnesses/
    ├── operations/
    └── manager.lock
```

On Windows the two launcher files use the `.cmd` suffix. Development checkouts
may exist elsewhere, but installed hooks and marketplace state bind to the one
managed `repo/` checkout. A local marketplace may report that checkout with the
Windows extended-length `\\?\` prefix; source-binding checks treat equivalent
drive and UNC spellings as the same path while still rejecting a different
directory.

If initialization fails, `state/install.json` remains `installing`. Rerun the
same installer request from either checkout: recovery proceeds only when the
recorded identity, paths, revision, launcher set and launcher content still
match exactly. It refuses ready installations, links, unknown state entries and
changed state; normal updates to a ready installation use `omh update`.

Use the harness-aware refresh command for global instructions. It resolves the target from the registry and applies the required confirmation policy; do not force-copy over an existing instructions file.

## Tooling Runtime

Shared oh-my-harness Python tooling uses a runtime venv outside plugin source trees:

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
${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python
%USERPROFILE%\.oh-my-harness\venv\Scripts\python.exe
```

Use this interpreter for Codex hooks, Watcher maintenance scripts, and skill/plugin validation that needs oh-my-harness tooling dependencies.

## Windows/Unix Compatibility Notes

This repository evolved from the Unix-first `zzzhty/my-codex` workflow; that
name is historical, not a current product or marketplace alias. The
cross-platform compatibility surface is intentionally narrow: it does not add
separate plugins, skills, manifests, or top-level modules for Windows. Windows
support lives in install documentation, shared tooling venv path selection,
Watcher hook command generation, hook schema alignment, and Windows-aware error
messages.

Key platform differences:

- Unix venv Python: `${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python`
- Windows venv Python: `%USERPROFILE%\.oh-my-harness\venv\Scripts\python.exe` by default
- POSIX directory projections: directory symlinks
- Windows directory projections: directory junctions
- POSIX Codex instructions: symlink into `$CODEX_HOME/AGENTS.md`
- Windows and current non-Codex instructions: atomic copy into the registry-selected target

Windows skill projection does not require file-symlink privilege. The projection helper validates junction targets and uses a strictly validated non-recursive `rmdir()` only for an empty ordinary directory left by an interrupted link creation.

`scripts/bootstrap_tooling_env.py` is cross-platform and selects the venv interpreter by platform:

- Windows: `Scripts\python.exe`
- Unix: `bin/python`

The bootstrap resolves the selected base Python to its real executable before creating the venv. This prevents PATH aliases or uv-managed Python symlinks from producing a `pyvenv.cfg` that cannot locate the standard library. If an existing tooling venv cannot start, reports the wrong prefix, or was created from a different base interpreter, bootstrap rebuilds it and restores the previous directory if creation or dependency validation fails. `--dry-run` performs the same read-only health preflight and prints whether a rebuild would occur.

If a tooling command reports that `PyYAML` or the registry validator
`jsonschema` is missing, refresh the shared tooling venv from the repository
root:

Unix:

```bash
python3 scripts/bootstrap_tooling_env.py
```

Windows PowerShell:

```powershell
py scripts\bootstrap_tooling_env.py
```

## Harness Refresh And Hook Debugging

Use the lifecycle CLI directly after bootstrap:

```bash
omh refresh
omh refresh zcode
omh refresh codex --repair
omh check codex
```

With no subcommand, `omh` remains a compatibility alias for `omh refresh`; new
scripts should use the explicit form. `refresh` without targets reconciles the
desired harness set, while `install` without a target selects the registry
default (currently `codex`). The bootstrap shim only restores tooling and enters
the unified Python CLI; `omh --help` remains available without a tooling rebuild,
and harness defaults, choices, and paths remain registry authority. Global
instructions are preflighted before skills or marketplace mutation.

For `codex`, refresh validates the complete manifest, marketplace policy, nested source-package containment, current cache shape, and marketplace source binding before mutation. Git installation is pinned to the validated checkout commit; explicit Git failures stop, while only automatic Git selection may fall back to the exact local checkout. Codex CLI resolution uses explicit `--codex`/`-CodexPath`, `CODEX_BIN`, `PATH`, standalone installs, then platform-managed fallbacks.

Codex stale-plugin reconciliation is on by default because the registry declares `managed-stale`. Only configured entries and cache directories inside the selected marketplace namespace are eligible. A nonempty exact plan is printed before mutation and requires confirmation; `--yes` or `-Yes` may confirm it. An enabled plugin visible only through the CLI and not proven by managed config/cache remains a hard failure. Other harnesses use only their registry-selected directory projection and never prune Codex plugins.

The registry records `my-codex` only as the retired marketplace identity consumed
by the explicit one-time migration. A normal refresh stops after printing the
bounded legacy config/cache plan. Run
`omh refresh codex --migrate-marketplace --yes` to install and verify the new
marketplace, retire the old selectors and source, and remove the validated old
cache namespace. The closure check rejects any remaining retired state.
The registry `schemaVersion` is an ISO calendar date (`YYYY-MM-DD`), currently
`2026-08-22`; advance it only when the registry schema changes.

`--migrate-from-repo <absolute-path>` is independent of marketplace discovery:
it authorizes only recognition of an exact former repo-owned Codex instructions
symlink and, when relocation has already made that exact retired local
marketplace source unavailable, detaches only the broken source registration so
Codex discovery can continue. Retired selectors and cache remain until the new
marketplace passes closure. This does not make the former path a fallback
checkout or compatibility alias; dry-run stops at this detachment breakpoint.

`--yes` never authorizes replacement of a different existing instructions file. That action always requires a live confirmation after the target type and content digest are shown.

Migrate legacy Watcher runtime roots explicitly before final checks:

```bash
"${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python" plugins/watcher/scripts/watcher migrate-state --dry-run
"${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python" plugins/watcher/scripts/watcher migrate-state --apply
```

This moves `$CODEX_HOME/skill-watcher/` to `$CODEX_HOME/watcher/skill/` and `$CODEX_HOME/doc-watcher/` to `$CODEX_HOME/watcher/doc/`. It refuses to merge when a target directory already exists.

Direct Python entry-point usage remains supported after `scripts/bootstrap_tooling_env.py` has created the shared tooling venv:

```bash
"${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python" scripts/refresh_harness.py
# alternative: "${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python" scripts/refresh_harness.py --harness zcode
```

Windows PowerShell:

```powershell
$ManagerHome = if ($env:OH_MY_HARNESS_HOME) { $env:OH_MY_HARNESS_HOME } else { Join-Path $HOME ".oh-my-harness" }
$ToolingPython = Join-Path $ManagerHome "venv\Scripts\python.exe"
& $ToolingPython scripts\refresh_harness.py
# alternative: & $ToolingPython scripts\refresh_harness.py --harness zcode
```

Run the final closure check after refresh:

Unix:

```bash
"${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python" scripts/check_harness.py
# alternative: "${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python" scripts/check_harness.py --harness zcode
```

Windows PowerShell:

```powershell
$ManagerHome = if ($env:OH_MY_HARNESS_HOME) { $env:OH_MY_HARNESS_HOME } else { Join-Path $HOME ".oh-my-harness" }
$ToolingPython = Join-Path $ManagerHome "venv\Scripts\python.exe"
& $ToolingPython scripts\check_harness.py
# alternative: & $ToolingPython scripts\check_harness.py --harness zcode
```

The check script verifies the selected harness skills and instructions plus the excluded-root policy. Codex closure also verifies the exact marketplace/source package set, manifest `./skills/` projection, enabled CLI state, cache identities, tooling Python, Watcher hooks, subagent support, source plugin validation, and Watcher doctor. Native directory harnesses verify their selected projection and instructions. The check is read-only.

After the helper refreshes hooks, open `/hooks` in Codex and trust the refreshed Watcher skill command hook definitions. Codex skips non-managed command hooks until the exact hook definition is trusted.

The refresh preflights global instructions before distribution mutation and verifies them after an atomic write. The final closure check reads the same registry-resolved plan.

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
  "command": "... watcher skill observe --repo-root <oh-my-harness-root>",
  "timeoutSec": 10,
  "statusMessage": "Watcher skill: observe <event>"
}
```

Windows hook commands are rendered with Windows command-line quoting and should point at `Scripts\python.exe`. Unix hook commands use POSIX quoting and should point at `bin/python`.

Install or refresh Watcher skill hooks from the source checkout:

Unix:

```bash
"$OH_MY_HARNESS_PYTHON" "$OH_MY_HARNESS_ROOT/plugins/watcher/scripts/watcher" skill install-hook --repo-root "$OH_MY_HARNESS_ROOT" --dry-run
"$OH_MY_HARNESS_PYTHON" "$OH_MY_HARNESS_ROOT/plugins/watcher/scripts/watcher" skill install-hook --repo-root "$OH_MY_HARNESS_ROOT" --apply
```

Windows PowerShell:

```powershell
$python = "$env:USERPROFILE\.oh-my-harness\venv\Scripts\python.exe"
& $python "$env:OH_MY_HARNESS_ROOT\plugins\watcher\scripts\watcher" skill install-hook --repo-root $env:OH_MY_HARNESS_ROOT --dry-run --python $python
& $python "$env:OH_MY_HARNESS_ROOT\plugins\watcher\scripts\watcher" skill install-hook --repo-root $env:OH_MY_HARNESS_ROOT --apply --python $python
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
"$OH_MY_HARNESS_PYTHON" "$PLUGIN_VALIDATOR" "$OH_MY_HARNESS_ROOT/plugins/watcher"
"$OH_MY_HARNESS_PYTHON" "$PLUGIN_VALIDATOR" "$OH_MY_HARNESS_ROOT/plugins/workflow"
"$OH_MY_HARNESS_PYTHON" "$OH_MY_HARNESS_ROOT/scripts/update_mattpocock_skills.py" --validate-only
"$OH_MY_HARNESS_PYTHON" -m unittest discover -s tests -p 'test_*.py' -v
```

Windows PowerShell:

```powershell
& $env:OH_MY_HARNESS_PYTHON -m json.tool .agents\plugins\marketplace.json | Out-Null
& $env:OH_MY_HARNESS_PYTHON -m json.tool .agents\plugins\install-manifest.json | Out-Null
& $env:OH_MY_HARNESS_PYTHON -m json.tool .agents\harnesses\registry.json | Out-Null
& $env:OH_MY_HARNESS_PYTHON -m json.tool .agents\harnesses\registry.schema.json | Out-Null
& $env:OH_MY_HARNESS_PYTHON $env:PLUGIN_VALIDATOR "$env:OH_MY_HARNESS_ROOT\plugins\watcher"
& $env:OH_MY_HARNESS_PYTHON $env:PLUGIN_VALIDATOR "$env:OH_MY_HARNESS_ROOT\plugins\workflow"
& $env:OH_MY_HARNESS_PYTHON "$env:OH_MY_HARNESS_ROOT\scripts\update_mattpocock_skills.py" --validate-only
& $env:OH_MY_HARNESS_PYTHON -m unittest discover -s tests -p 'test_*.py' -v
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
scripts/check_harness.py
scripts/harness_registry.py
scripts/install_oh_my_harness.py
scripts/manager_paths.py
scripts/manager_state.py
scripts/omh.py
scripts/omh_bootstrap.py
scripts/remove_harness.py
scripts/refresh_harness.py
scripts/sync_agents_skills.py
scripts/sync_codex_agents.py
scripts/sync_harness_instructions.py
scripts/update_mattpocock_skills.py
scripts/upgrade_oh_my_harness.ps1
scripts/upgrade_oh_my_harness.sh
tests/
agents/
```

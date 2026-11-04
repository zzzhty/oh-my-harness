# Oh My Harness

OMH maintains versioned skills, helper resources and compositions. It can install
its skills independently through a small Python distributor. 
can distribute the same content through its Rust core and call OMH's runtime
implementation with explicit interpreter and deployment paths.

The default composition contains 29 skills in `maintenance`, `workflow` and
`mattpocock-skills`. Watcher collection, automatic hooks and historical report
readers remain retired. Preparing Python does not invoke skills or enable hooks.

## Standalone installation

From this checkout, use Python 3.11 or newer. The distributor uses only the
standard library; `requirements.txt` is for developer validation.

```sh
/absolute/python3 -B -m omh plan --harness codex
/absolute/python3 -B -m omh install --harness codex --offline
/absolute/python3 -B -m omh status --harness codex
/absolute/python3 -B -m omh update --harness codex --offline
/absolute/python3 -B -m omh uninstall --harness codex
```

`--harness codex` projects skill directories into `~/.codex/skills`;
`--harness claude-code` uses `~/.claude/skills`. `--skills-root /absolute/path/skills`
selects another directory. These standalone adapters install skills and their
resources; they do not edit client configuration or global instructions. Codex
uses directory skill names here. the previous owner's Codex adapter preserves native plugin
identities and installs its registry-selected instructions.

Standalone state defaults to `~/.oh-my-harness` (`--home` overrides it). Python
venvs live under its `runtimes/<group>/<identity>` directory. `--deployment-root`
changes venv storage, independently of the skill target. `--python` selects the
absolute bootstrap interpreter; otherwise an explicit `OMH_PYTHON` is used, then
the interpreter running the standalone command. There is no project-venv or PATH
search. `prepare` prepares runtimes without installing skills. `install` and
`update` may also prepare them. `plan` and `status` never create environments or
run pip. Commands require absolute paths for overrides.

Use `--external-venv /absolute/venv` to reuse a verified environment without
modifying it. Its Python version, imports and locked dependency versions must
satisfy every selected group. No environment is deleted by uninstall; managed
versions and failed partial attempts remain available for inspection/recovery.
Explicit prepare can resume an interrupted OMH-owned environment at the same
final path. A valid environment is reused based on its actual interpreter; unknown
incompatible directories are preserved. Helpers never repair environments.
Managed creation uses private executable copies; complete venvs are never moved. An offline group with dependencies needs hash-matching wheels under
`<home>/cache/wheels`; the current groups use only the standard library.

The target's `.omh-owner.json` records its sole owner, file digests and managed
paths. Updates restore missing files and can install an absent target. Unrelated
files and empty directories in a projected skill are preserved; only a conflicting
write or removal of a user-modified managed file blocks the transaction. A shared
`.omh-owner.lock` serializes both distributors. Failed writes roll back through
a durable journal; after a hard interruption use `python -B -m omh recover` with
the same `--home` and target. Uncommitted rollback preserves post-failure user
edits; committed recovery finishes cleanup without rejecting later user changes. Handoff
between OMH and is explicit: uninstall with the current owner, inspect the
target and recovery state, then install with the new owner. Neither takes over
an existing installation automatically.

## Python helpers in either mode

OMH owns one implementation for venv preparation, validation and helper startup:
`plugins/workflow/scripts/omh_runtime.py`, runtime protocol 1. It does not maintain
an installed-state database. Standalone supplies its defaults; supplies its
bootstrap Python, deployment root and optional external venv. remains the
only owner of the previous owner's target receipts and transactions. Static distribution
needs no Python.

The installation owner persists `.omh-runtime` beside the skill root (above the
native plugin cache for Codex). Both launchers read that stable binding:

```sh
sh /absolute/harness/.omh-runtime/run.sh workflow /absolute/skill/scripts/check_sop_ready.py /absolute/sop.md
```

On Windows, use `& 'C:\absolute\harness\.omh-runtime\run.ps1' workflow ...`.
Arguments are forwarded as argv, including spaces and empty values. Neither a
new agent session nor helper execution needs the original checkout or an install
process's environment. An explicit absolute `OMH_PYTHON` overrides the bound venv
for that invocation. Invalid overrides fail; validation never falls back or
installs dependencies. The runtime isolates Python-specific environment settings.
Each consuming skill documents its group and its own output/permission boundary.

## managed installation

the previous owner's Rust CLI owns local target policy, content acquisition, plans, receipts,
transactions and recovery. It calls OMH runtime code only for selected helper
preparation or execution. It never calls the standalone installer.

```sh
 harness import --lock /absolute/omh.lock.json --archive /absolute/omh.omh
 harness bootstrap --source /absolute/verified/cache
 harness plan install --harness claude-code,codex
 install skills --harness claude-code,codex
 harness runtime prepare workflow --python /absolute/python3 \
  --deployment-root /absolute/runtime-storage --offline
```

Use `sync --source` for an existing manager. Add `--external-venv` to reuse an
existing OMH or other venv; records external lifecycle ownership and never
removes it. Runtime preparation switches target bindings and receipt in one
Rust journal. The [runtime/ownership contract](docs/adr/0030-independent-distribution-and-shared-runtime.md)
and [compatibility audit](docs/runtime-compatibility-audit.md)
defines the boundary. Native client loading/invocation remains a separate
acceptance check from filesystem distribution and helper execution.

## Versions and validation

The latest published OMH content is **1.1.1, reissued on 2026-11-03**. Its source
checkout includes the standalone Python distributor; its content archive includes
the shared runtime provider. 
adopted the verified reissued assets. See the [release record](docs/releases/1.1.1.md)
for exact source and asset coordinates, CI coverage and the separately authorized
Linux Home refresh.

The reissue explicitly replaced the original 1.1.1 tag and assets. Old locks still
identify the superseded bytes and need a reviewed update; the version number alone
does not identify the payload. Existing installations change through their owner's
explicit plan/apply workflow. Publication does not migrate a Home installation.

The published [`v1.0.0`](https://github.com/zzzhty/oh-my-harness/releases/tag/v1.0.0)
records the earlier lifecycle and Watcher baseline. [`v1.1.0`](https://github.com/zzzhty/oh-my-harness/releases/tag/v1.1.0)
and the original 2026-10-30 1.1.1 publication record the content-publishing line; the reissue
adds independent distribution and the shared runtime. The withdrawn old
1.2.0 tag/release/assets were deleted, and are not a rollback coordinate. No old
Watcher, hooks, git self-updater or historical state migration is restored.

Use an isolated developer venv with `requirements.txt`:

```sh
python -B -m unittest discover -s tests -p 'test_*.py'
python -B -m unittest discover -s plugins/maintenance/tests -p 'test_*.py'
python -B -m unittest discover -s plugins/workflow/tests -p 'test_*.py'
```

After final packaged edits and owning tests, run
`python scripts/update_plugin_generations.py --release-version <version>` once,
then `python scripts/check_plugin_generations.py`. Plugin byte identity remains
`sha256-canonical-plugin-tree-v1`. `plugins/*/skills/*/SKILL.md` is authoring
source; caches and client projections are not.

`` pins the released Rust archive exporter. The archive
contract remains compatible; it carries the shared runtime as package resources,
and excludes the standalone installer. Export/import remains Rust-owned:

```sh
python scripts/check_content_export.py /absolute/
# Shared-runtime integration (includes binding and owner-handoff checks):
python scripts/check_content_export.py /absolute/compatible- --shared-runtime
```

The reissued 1.1.1 supplies runtime protocol 1. Historical content without its
provider remains statically distributable; explicit runtime preparation reports
`HARNESS_RUNTIME_PROVIDER_REQUIRED` until supporting content is selected. Native
CI covers standalone behavior and the previous owner's basic runtime/helper flow; the full paired
external-venv, handoff and relocation check has Linux evidence. Native client
skill discovery, model calls and interactive Home GUI use are outside the reissue's
acceptance claims. The [release record](docs/releases/1.1.1.md) separates these scopes.

For release archives, use the pinned ` harness export` with the exact clean
commit, repository and versioned release URL. Keep published versions' assets
immutable; the 2026-11-03 reissue was an explicitly authorized exception recorded
with both old and new coordinates. CI validates Python 3.11/3.12 on
Linux/macOS/Windows. See [ADR 0030](docs/adr/0030-independent-distribution-and-shared-runtime.md)
for the current decision; [ADR 0028](docs/adr/0028-versioned-content-publishing.md)
and [ADR 0029](docs/adr/0029-pure-hub-with-skill-owned-helpers.md) preserve the
superseded pure-Hub boundary and retirement history.

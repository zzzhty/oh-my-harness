# Oh My Harness

OMH maintains versioned skills, helper resources and compositions and installs
them through its own small standard-library Python distributor, `python -m omh`.
It is the sole distribution channel
([ADR 0031](docs/adr/0031-sole-standalone-distribution.md)).

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
`--harness claude-code` uses `~/.claude/skills`; `--harness grok` (Grok Build)
uses `~/.grok/skills`. `--skills-root /absolute/path/skills`
selects another directory. The distributor installs skills, their resources and
the harness global-instructions file ([ADR 0032](docs/adr/0032-standalone-instruction-projection.md)):
`agents/global-instructions.md` is projected as `AGENTS.md` (codex, grok) or
`CLAUDE.md` (claude-code) beside the skills root, as an ordinary owned managed
file with drift detection and uninstall cleanup. It does not edit client
configuration or install the Codex support note. Codex uses directory skill
names here. Grok also reads its global rules from `~/.grok/AGENTS.md` (capped
at 10,000 characters by Grok; the OMH source is well under) and, like codex,
shadowing rule files (`Claude.md`, `AGENT.md`) fail closed.

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
Managed creation uses private executable copies; complete venvs are never moved. A group with no requirements is created with `venv --without-pip`. An offline group with dependencies needs hash-matching wheels under
`<home>/cache/wheels`; the current groups use only the standard library.

On POSIX, `install` and `update` also write an `omh` launcher shim into
`~/.local/bin` (absolute `--bin-dir` overrides it), so daily use is just
`omh status` / `omh update`. The shim is a static pointer to the installing
checkout and interpreter — no state, no self-update, no PATH search; an unowned
existing `omh` there fails closed, and `uninstall` removes an owned one
([ADR 0033](docs/adr/0033-standalone-launcher-shim.md)). Windows uses the full
`python -B -m omh` command.

`omh status` without `--skills-root` summarizes **every installed target** the
home knows: each target's receipt is verified live and reported as
`installed` (with drift counts and recovery needs), `foreign`, `other-home` or
`missing`; the exit code is 0 only when every listed target is clean. The
default output is a human-readable summary; `--json` returns the machine form.
The home's `targets.json` index is maintained by install/update and pruned by
uninstall, and default harness roots (`~/.codex`, `~/.claude`) are probed
alongside it — the index is a hint, receipts stay the source of truth
([ADR 0034](docs/adr/0034-status-surface-and-target-index.md)).

The target's `.omh-owner.json` records its sole owner, file digests and managed
paths. Updates restore missing files and can install an absent target. Unrelated
files and empty directories in a projected skill are preserved; only a conflicting
write or removal of a user-modified managed file blocks the transaction. A shared
`.omh-owner.lock` serializes competing processes. Failed writes roll back through
a durable journal; after a hard interruption use `python -B -m omh recover` with
the same `--home` and target. Uncommitted rollback preserves post-failure user
edits; committed recovery finishes cleanup without rejecting later user changes.
The planner never takes over an existing installation automatically: a target
with another owner's receipt, or a native plugin configuration still referencing
the `oh-my-harness` marketplace coordinate, fails with
`HARNESS_OWNER_CONFLICT` until the current owner uninstalls explicitly. The
projected instructions file is fail-closed: an unowned existing
`AGENTS.md`/`CLAUDE.md`, a user-modified owned one, or a shadowing file such as
`AGENTS.override.md` fails with `HARNESS_CONFLICT` until the user resolves it;
`uninstall` removes the owned file.

## Python helpers

OMH owns one implementation for venv preparation, validation and helper startup:
`plugins/workflow/scripts/omh_runtime.py`, runtime protocol 1. It does not maintain
an installed-state database. The standalone CLI supplies the defaults and records
its own receipts.

The installer persists `.omh-runtime` beside the skill root. Both launchers read
that stable binding:

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

## Migrating a previously managed installation

A previously managed home is migrated by owner handoff: uninstall with that
previous owner, complete
its recovery, verify the target holds no owner receipt and no lingering native
plugin configuration, then run the standalone install above. The standalone
planner's `HARNESS_OWNER_CONFLICT` guard marks any skipped step. The historical
runtime/ownership boundary is preserved by
[ADR 0030](docs/adr/0030-independent-distribution-and-shared-runtime.md) and the
[compatibility audit](docs/runtime-compatibility-audit.md).

## Versions and validation

The latest published OMH content is **1.1.1, reissued on 2026-11-03**. Its source
checkout includes the standalone Python distributor and the shared runtime
provider. See the [release record](docs/releases/1.1.1.md) for exact source and
asset coordinates, CI coverage and the separately authorized Linux Home refresh.

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

`scripts/check_standalone_distribution.py` exercises the distributor end to end
in an isolated home: read-only `plan`, `install`, `status`, installed helper
execution through the persisted `.omh-runtime` launchers, idempotent `update`
and `uninstall`. CI runs it alongside the unit suites on Python 3.11/3.12 across
Linux/macOS/Windows:

```sh
python scripts/check_standalone_distribution.py
```

The reissued 1.1.1 supplies runtime protocol 1. Historical content without its
provider remains statically distributable; explicit runtime preparation reports
`HARNESS_RUNTIME_PROVIDER_REQUIRED` until supporting content is selected. Deep
standalone behavior (external venvs, shared locks, interruption recovery,
partial preparation) is covered by `tests/test_standalone.py`. Native client
skill discovery, model calls and interactive Home GUI use are outside the
reissue's acceptance claims. The [release record](docs/releases/1.1.1.md)
separates these scopes.

A release is a tagged source checkout; installation starts from a verified
source tree through the standalone CLI. The historical `.omh` archives and
`omh.lock.json` are a retired archive path;
published assets remain immutable. The 2026-11-03 reissue was an explicitly
authorized exception recorded with both old and new coordinates.
See [ADR 0031](docs/adr/0031-sole-standalone-distribution.md) for the current
decision; [ADR 0030](docs/adr/0030-independent-distribution-and-shared-runtime.md),
[ADR 0028](docs/adr/0028-versioned-content-publishing.md)
and [ADR 0029](docs/adr/0029-pure-hub-with-skill-owned-helpers.md) preserve the
superseded distribution history.

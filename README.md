# Oh My Harness

OMH maintains versioned skills, helper resources and compositions and installs
them through its own small standard-library Python distributor, `python -m omh`.
It is the sole distribution channel
([ADR 0031](docs/adr/0031-sole-standalone-distribution.md)).

The default composition contains 29 skills in `maintenance`, `workflow` and
`mattpocock-skills`. Watcher collection, automatic hooks and historical report
readers remain retired. Preparing Python does not invoke skills or enable hooks.

## Standalone installation

On a host, bootstrap with one command (needs `git`, `curl` and
Python ≥ 3.11; [ADR 0036](docs/adr/0036-bootstrap-installer-script.md)).

POSIX:

```sh
curl -fsSL https://raw.githubusercontent.com/zzzhty/oh-my-harness/main/install.sh | \
  OMH_HARNESS=codex,claude-code sh
```

Windows (PowerShell 5.1 or PowerShell 7):

```powershell
$env:OMH_HARNESS = 'codex,claude-code'
irm https://raw.githubusercontent.com/zzzhty/oh-my-harness/main/install.ps1 -OutFile $env:TEMP\omh-install.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File $env:TEMP\omh-install.ps1
```

The installer probes the interpreter, verifies the release's `omh-<tag>.ref`
asset against the tag, clones into `~/.oh-my-harness/repo` (on Windows, the
profile directory Python uses as the home), and installs one target per
listed harness. Afterwards the host needs one command:
`omh update [--to <tag>]` upgrades in place (ref verification, fetch,
checkout, refresh of every indexed target). On Windows, run that as
`python -B -m omh update` from the managed clone. From a developer checkout
it refuses with `OMH_SOURCE_NOT_MANAGED` and points at `omh refresh`, which
re-projects targets from the current checkout. Re-running `install.sh` or
`install.ps1` locally does the same upgrade without curl.

From a developer checkout, use Python 3.11 or newer directly (the distributor
uses only the standard library; `requirements.txt` is for developer
validation):

```sh
cd /absolute/path/to/oh-my-harness   # this checkout; Python 3.11 or newer
python3 -B -m omh plan --harness codex
python3 -B -m omh install --harness codex --offline
python3 -B -m omh status
python3 -B -m omh refresh --harness codex
python3 -B -m omh uninstall --harness codex
```

After the first install, daily use is the short `omh <command>` form through
the launcher shim (POSIX; see below).

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
`refresh` may also prepare them. `plan` and `status` never create environments or
run pip. Each command takes only its own flags — `omh <command> --help` lists
them; `--source`/`--home` may come before or after the command
([ADR 0035](docs/adr/0035-standalone-cli-grammar-and-readable-output.md)).
Every command prints a human summary by default; `--json` returns the machine
form (for `plan`, the JSON `changes` list). `--operation install|refresh|uninstall`
selects which operation `plan` previews (default `install`), e.g.
`python3 -B -m omh plan --operation uninstall --harness codex`. `--source
/absolute/path` distributes content from a different checkout. Commands
require absolute paths for overrides. When the home knows other harnesses and
the default codex target is absent, target commands note the installed
harnesses on stderr.

Use `--external-venv /absolute/venv` to reuse a verified environment without
modifying it. Its Python version, imports and locked dependency versions must
satisfy every selected group. No environment is deleted by uninstall; managed
versions and failed partial attempts remain available for inspection/recovery.
Explicit prepare can resume an interrupted OMH-owned environment at the same
final path. A valid environment is reused based on its actual interpreter; unknown
incompatible directories are preserved. Helpers never repair environments.
Managed creation prefers private executable copies; relocated builds
(uv-managed CPython) fall back to a symlinked seeding verified in place
([ADR 0037](docs/adr/0037-venv-seeding-strategy.md)), and complete venvs are
never moved. A group with no requirements is created with `venv --without-pip`. An offline group with dependencies needs hash-matching wheels under
`<home>/cache/wheels`; the current groups use only the standard library.

On POSIX, `install` and `refresh` also write an `omh` launcher shim into
`~/.local/bin` (absolute `--bin-dir` overrides it), so daily use is just
`omh status` / `omh update`. The short command needs that directory on `PATH`;
if `~/.local/bin` is not on `PATH`, add it or pass `--bin-dir /absolute/dir`
pointing at a directory that is. The shim is a static pointer to the installing
checkout and interpreter — no state, no self-update, no PATH search; an unowned
existing `omh` there fails closed, and `uninstall` removes an owned one even
when other targets remain installed — rerun `install` to recreate it
([ADR 0033](docs/adr/0033-standalone-launcher-shim.md)). Windows uses the full
`python -B -m omh` command, including `python -B -m omh update` from the
managed clone.

`omh status` without `--skills-root` summarizes **every installed target** the
home knows: each target's receipt is verified live and reported as
`installed` (with drift counts and recovery needs), `foreign`, `other-home` or
`missing`; the exit code is 0 only when every listed target is clean. The
default output is a human-readable summary — each target is prefixed with `✓`
(clean), `!` (drift, or a foreign/other-home/missing receipt) or `✗`
(recovery pending, with the `omh recover` command to run) — and `--json`
returns the machine form. The home's `targets.json` index is maintained by
install/refresh and pruned by uninstall, and default harness roots (`~/.codex`,
`~/.claude`, `~/.grok`) are probed alongside it — the index is a hint,
receipts stay the source of truth
([ADR 0034](docs/adr/0034-status-surface-and-target-index.md)).

Runtime errors print one JSON object to **stderr** as
`{"error": {"code", "message"}}` and exit 1; stdout stays a parseable result
stream. Command-line usage errors print argparse text to stderr and exit 2.
`status` exits 0 only when every listed target is clean, 1 otherwise or on
error. Runtime preparation prints TTY-gated progress lines to stderr.

Error codes: `HARNESS_OWNER_CONFLICT` (another owner's receipt or native
configuration; explicit handoff required), `HARNESS_CONFLICT` (unowned or
user-modified managed file, shadowing rules, unowned launcher),
`HARNESS_RECOVERY_REQUIRED` (an interrupted transaction's journal exists;
run `recover` first), `HARNESS_RECOVERY_CONFLICT` (post-failure user edits
block rollback), `HARNESS_RUNTIME_*` (runtime provider: `HARNESS_RUNTIME_BUSY`
lock held, `HARNESS_RUNTIME_SPEC` non-absolute or linked path,
`HARNESS_RUNTIME_OFFLINE_MISSING` cached wheel absent, …),
`OMH_CONTENT_INVALID` (malformed source content: manifest, composition,
packages, skills), `OMH_FILE_INVALID` (an owned file is not an ordinary file
or exceeds distribution limits), `OMH_RECEIPT_INVALID` (target receipt or
recovery journal fails validation), `OMH_PATH_INVALID` (path shape or
manager/target separation violation), `OMH_SOURCE_NOT_MANAGED` (`update`
run from a checkout that is not the managed clone under the home),
`OMH_STATE_CHANGED` (the target changed
between planning and writing; re-run), `OMH_ENVIRONMENT_INVALID` (the
environment cannot support the run, e.g. stream reconfiguration), and
`OMH_INVALID` (malformed input or state without a more specific code).

The target's `.omh-owner.json` records its sole owner, file digests and managed
paths. Refreshes restore missing files and can install an absent target. Unrelated
files and empty directories in a projected skill are preserved; only a conflicting
write or removal of a user-modified managed file blocks the transaction. A shared
`.omh-owner.lock` serializes competing processes. Failed writes roll back through
a durable journal; after a hard interruption use `python -B -m omh recover` with
the same `--home` and target — pass the same `--harness` (or `--skills-root`) as
the interrupted command, since `recover` defaults to the codex target; it prints
`{"recovered": true}` on success. Uncommitted rollback preserves post-failure user
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

The protocol CLI behind the launchers (`omh_runtime.py prepare|verify|run`)
answers `prepare`/`verify` on **stdout** as `{"ok": ...}` or
`{"error": {"code", "message"}}` with **exit 0** — integrations read the
envelope, not the exit code ([ADR 0030](docs/adr/0030-independent-distribution-and-shared-runtime.md)).
`run` preserves the helper's own exit status and stdout as the caller's
result; its startup failures print the `{"error": ...}` envelope to **stderr**
with exit 1. Unknown or missing protocol arguments are usage errors (exit 2).
The standalone `omh` CLI keeps its separate contract: `--json` results on
stdout, error envelopes on stderr with exit 1.

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

The same CI job runs the repository architecture check. Run it locally before
finishing a change; it is the same command, and it needs the developer
dependencies in `requirements.txt` (including `ruff`). The distributor under
`omh/` does not import them.

```sh
python scripts/check_architecture.py
```

Findings name the violation, the fix, and the principle. File-size ceilings,
grandfathered locale text calls, and grandfathered ruff findings live in
`scripts/architecture_baseline.json`. Do not raise that file to admit a new
violation. The rule table is in `AGENTS.md`.

After final packaged edits and owning tests, run
`python scripts/update_plugin_generations.py --release-version <version>` once,
then `python scripts/check_plugin_generations.py`. Plugin byte identity remains
`sha256-canonical-plugin-tree-v1`. `plugins/*/skills/*/SKILL.md` is authoring
source; caches and client projections are not.

`scripts/check_standalone_distribution.py` exercises the distributor end to end
in an isolated home: read-only `plan`, `install`, `status`, installed helper
execution through the persisted `.omh-runtime` launchers, idempotent `refresh`
and `uninstall`. CI runs it alongside the unit suites on Python 3.11/3.12 across
Linux/macOS/Windows:

```sh
python scripts/check_standalone_distribution.py
```

Each release publishes one bootstrap asset: `omh-<tag>.ref`, a one-line file
holding the tag's commit SHA (`git rev-parse <tag>^{}`). `install.sh`,
`install.ps1`, and `omh update` verify the tag against it before touching
anything
([ADR 0036](docs/adr/0036-bootstrap-installer-script.md)).

On an existing managed clone, the installers stop if it contains local changes
or extra files (including ignored files), preserving the checkout for you to
resolve. Upgrades refresh every indexed skills root, including multiple custom
roots for the same harness. A malformed target index stops the upgrade instead
of silently falling back to a default installation directory.

The reissued 1.1.1 supplies runtime protocol 1. Historical content without its
provider remains statically distributable; explicit runtime preparation of
unsupported content fails closed with `OMH_CONTENT_INVALID` (an unsupported
manifest, composition or a manifest without `runtimeGroups`). Deep
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

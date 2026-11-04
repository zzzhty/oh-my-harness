# ADR 0030: Independent distribution and one shared Python runtime

Status: accepted for implementation, 2026-11-03. Release publication and any real
installation require separate actions. This supersedes the installer/runtime
exclusivity in ADR 0028 and ADR 0029. Their retirement of Watcher, hooks, old report
readers and git self-update remains in force.

> Lifecycle update — 2026-11-03: this decision was implemented and published in
> the [1.1.1 reissue](../releases/1.1.1.md), then adopted by ATM and applied in a
> separately authorized Linux Home refresh. References below to unpublished
> generations and fixed content pins describe the implementation phase. The
> architecture and ownership decision remains in force.

## Decision

OMH is independently usable. A standard-library Python entrypoint (`python -m omh`)
provides plan, install, update, uninstall, status, explicit runtime preparation and
recovery. It projects complete skill resources into a selected local skill root.
It owns its standalone target receipt, digest protection, OS lock and durable
rollback journal. It does not restore the historical lifecycle manager wholesale.

ATM retains Rust static distribution, registry adapters, native Codex packages,
plans, target receipts, transactions and recovery. Python venv creation, dependency
installation, validation and script startup have one owner: the OMH runtime
provider packaged in `plugins/workflow/scripts`. ATM calls this provider with
explicit arguments. It does not call `omh install`, and provider calls never
create OMH global installed state. Reusing the process does not require reusing a
physical venv.

## Runtime protocol 1

The provider accepts `prepare` and `verify` with `--request <JSON>` as one argv
value. Success is `{"ok": <PreparedRuntime>}`; failure is
`{"error":{"code":...,"message":...}}`. These protocol responses exit zero so
an integration can read the error code; malformed processes, timeout or transport
failures remain process errors. Helper `run` preserves the helper's actual exit
status and output. No shell command is built from Python or script arguments.

| Parameter | Meaning |
| --- | --- |
| `bundleRoot` | Absolute verified/trusted content root, used for relative dependency locks. |
| `spec` | Existing runtime-group contract: ID, minimum Python, imports, optional hash-locked requirements. |
| `python` | Explicit absolute bootstrap interpreter, including when reusing a venv. No PATH lookup. |
| `deploymentRoot` | Venv storage only: final path is `<deploymentRoot>/<group>/<identity>`. Never a skill target. |
| `externalVenv` | Optional existing venv to validate without modification; its owner retains lifecycle responsibility. |
| `wheelCache`, `offline` | Explicit wheel source policy; pip uses isolated, hashed, binary-only requirements. |
| `prepared` | Recorded runtime reference; verification uses its group, root and Python path with actual version/dependency checks. |

Standalone supplies defaults under its own home and may use its command's current
interpreter. ATM requires `--python`, supplies its own default deployment root,
and exposes `--deployment-root` and `--external-venv`. Venvs are created at their
final identity paths; venv directories are never staged and renamed/copied.
A preparation descriptor is written before creation so explicit prepare can resume
an owned incomplete attempt. Valid environments are reused by actual interpreter
checks, independently of historical markers. Unknown incompatible nonempty paths
are preserved. Prior valid runtime versions survive failed new preparation. Ordinary execution/status do not invoke pip or download interpreters.
External environments are checked for venv membership, version, imports and exact
locked dependency versions and receive no marker, pip or bytecode writes.

Static Rust import still checks the dependency-lock grammar before any process can
run; that is content validation, not a second Python runtime manager. Protocol 1
lives with `workflow`; a composition using it must include that package. No new
content-manifest schema or archive identity is introduced.

## Persistent execution and transactions

The owner installs `.omh-runtime/{run.sh,run.ps1,omh_runtime.py,<group>.json,<group>.python}`
beside the skill root, above the native cache when present. These are generated
installation artifacts with receipt digests, not modifications to authored skills
or native package bytes. A new session reads them directly. Unprepared groups
have an explicit null binding and fail until prepared. Every consuming skill uses
the group launcher. `OMH_PYTHON` is an invocation-local absolute venv override; an
invalid override fails without fallback. Startup validates version/dependencies
and sanitizes Python environment settings before running the helper.

ATM projects these artifacts without Python. During explicit runtime preparation,
OMH prepares/verifies the environment, then ATM journals the content, binding and
receipt switch together. Failure retains the old target and receipt; unused new
or failed environments remain for inspection. Standalone follows the same rule
for target files. Cross-file visibility is not atomic during an active operation;
recovery restores the journaled before-images and refuses post-crash user edits.

Both distributors use the target's `.omh-owner.lock` and `.omh-owner.json` with
absolute physical target and manager identity. One physical harness root has one
owner even if adapters differ. An unowned file collision is a conflict; unrelated files in projected directories
are preserved. Legacy ATM
receipts gain the marker on an explicit operation; existing nonempty OMH/other
installs are not adopted automatically. Handoff requires the current owner's
uninstall and recovery completion before the next owner installs. Empty lock
files remain stable; they are never unlinked and recreated to bypass a lock.

Neither uninstall removes a managed or external venv. ATM's existing explicit
manager-home relocation rebuilds managed runtimes at final paths and switches
bindings/receipts with its handoff transaction; external runtimes still require
explicit resolution before relocation.

## Identifier inventory, compatibility and rollback

| Surface | Classification and treatment |
| --- | --- |
| `ATM_PAYLOAD_PYTHON`, local `atm_tooling_python`, workflow bare `python` examples | Cross-repository consumer migration authorized by the user. Current consumers move atomically to OMH launchers and `OMH_PYTHON`. No silent legacy-variable fallback. Historical release evidence stays intact. |
| New `.omh-runtime`, `.omh-owner.json`, `.omh-owner.lock`, standalone journal | New public installation contracts. Machine paths are owner-generated; source contains no machine binding. Same-owner repeat operations are idempotent. |
| Existing ATM receipt fields and `.atm-runtime.json` | Persisted identities retained. `deploymentRoot` is optional for new managed references; old marker files remain untouched; execution validates the actual interpreter without reading their formats. Missing provider content reports an explicit upgrade requirement. |
| Old installer identities, `.oh-my-harness` data, caches, old releases and ADRs | Historical/persisted evidence preserved. The new entrypoint uses a new bounded receipt and does not infer ownership from old data or restart retired hooks. |
| Content manifest/archive and plugin algorithm | Preserve existing schemas and algorithms. Regenerate package byte identities once after final packaged changes and owning tests. |

Rollback means selecting the prior verified source/lock through the owning
manager's explicit lifecycle. Do not rename an old cache, edit an old receipt,
move a venv or let two owners operate on one target. New generation metadata is
unpublished until the source revision and assets are separately approved. Current
published content pins stay fixed while these two worktrees are validated.

## Verification

Standalone tests cover defaults and explicit deployment, read-only status/plan,
repeat operations, file/directory drift, shared locks, first-install failure,
hard interruption and post-crash edits, future-session execution, hostile Python
environment settings, bad overrides, argv, external retention, final-path failures
and dependency checks. Native Windows junction and launcher cases run in Windows
CI; this Linux worktree cannot claim that execution.

Rust tests retain static distribution, source validation, adapters, ownership,
receipt schemas, journal recovery, migration, CLI and packaging gates. Protocol
bridge tests observe one JSON argv and provider errors. Real venv preparation,
external reuse, persistent helper startup, owner handoff and runtime relocation
are exercised by `check_content_export.py --shared-runtime` against the candidate
ATM executable in a temporary Home. Historical fake-Rust venv tests move to these
OMH-owned runtime tests and the cross-repository check.

## Compatibility simplification follow-up — 2026-11-03

The [compatibility audit](../runtime-compatibility-audit.md) records the removed
marker/version branches, duplicate bridge/preflight checks and safe recovery
behavior. File-based conflict protection replaces whole-directory drift rejection
in standalone projections. Owner fields are semantic identities; formatting and
local annotations do not confer a different owner. Target transactions still
compare exact before-images, and runtime/target overlap checks remain bidirectional.

## Publication and acceptance update — 2026-11-03

OMH [PR #5](https://github.com/zzzhty/oh-my-harness/pull/5) merged as
`cd7371a312139632f5fc83702a134932345e29b5`; the v1.1.1 tag and reissued assets
identify that source. ATM [PR #10](https://github.com/zzzhty/ai-tooling-manager/pull/10)
integrated the provider, and [PR #11](https://github.com/zzzhty/ai-tooling-manager/pull/11)
merged the verified public lock as `cb177c2a42486bd16afe3ba2abb2681f9228ac15`.
Publication, consumer-lock selection and Home application were distinct actions.

OMH's six native CI jobs and ATM's ten main CI jobs passed. The native ATM CLI
smoke now exercises both runtime groups and all four installed helper consumers
on Linux/macOS/Windows. Full paired external reuse, owner handoff and relocation
remain locally verified on Linux. The later Linux Home acceptance verified owned
files, preserved configuration, persistent helper startup and Python 3.13.15;
it did not test native client skill discovery, model calls or an interactive GUI
session. Exact coordinates and evidence are owned by the [release record](../releases/1.1.1.md).

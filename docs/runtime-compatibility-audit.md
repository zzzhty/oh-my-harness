# Runtime compatibility and recovery audit

Scope: the unpublished OMH standalone / shared-runtime implementation. The
2026-11-03 follow-up asks for useful recovery and less compatibility machinery.
Published locks, receipts, archives and retired-feature history are preserved.
The changes below replace the stricter draft behavior; they do not migrate a real
installation.

| Surface | Action and reason |
| --- | --- |
| `.omh-runtime.json` execution branches | Remove dual-format reading. Helper execution validates the selected interpreter's actual venv prefix, minimum version, imports and locked dependency versions. Old metadata is neither needed nor rewritten. |
| Runtime identity hex, exact `root/bin/python` spelling, marker/spec byte equality, separate `pyvenv.cfg` existence | Remove from runtime verification. These describe preparation provenance, not interpreter capability. Actual prefix/version/dependency probing is authoritative and accepts interpreter aliases. |
| Explicit `OMH_PYTHON` or bootstrap path | Retain absolute-path selection and execution failure. An invalid explicit selection never silently switches to another interpreter or PATH. The bootstrap's protocol minimum and an external helper venv's content minimum are distinct roles. |
| External venv aliases | Resolve the explicitly supplied root and validate it read-only. A symlink/junction used to name an external venv does not require modifying or rejecting that environment. |
| Interrupted managed preparation | Replace unconditional `INCOMPLETE` failure/manual cleanup with same-final-path retry. A preparation descriptor is written before building. A valid environment is reused without rebuilding; an incomplete OMH-owned attempt can be completed by explicit prepare. |
| Unknown directory in runtime storage | Reuse it only if its actual interpreter already satisfies the request. Do not rebuild an incompatible nonempty directory without an OMH preparation descriptor. This protects user content without requiring legacy marker formats. |
| Writes during managed retry | Retain a check of the trees venv may rewrite; with wheel installation, check the whole prefix because wheel data may address it. Do not follow external links/reparse points or overwrite hardlinked shared files. Standard POSIX Python aliases can be replaced with private executable copies; `lib64 -> lib` remains usable. Unrelated root entries are left alone in standard-library-only preparation. |
| Runtime deployment within content checkout | Remove the blanket source/deployment overlap prohibition. An explicitly selected `.runtime-envs` directory under a checkout is valid; it is not automatic project-venv discovery. Runtime storage must still be separate from the actual skill target, in either operation order. |
| Standalone manager containing a client target | Permit a target under `<manager>/clients/...` with runtime storage in a separate sibling directory. Do not require unrelated absolute directory trees. |
| Standalone preflight | Remove the first complete projection/hash/plan pass. Check owner identity before preparation, then build one file plan with final bindings. The transaction still compares before-images immediately before writes. |
| Missing managed files / update before first install | Restore absent files on update; update may install an absent target. Uninstall tolerates already-absent files. These cases need no destructive fallback or new ownership inference. |
| Additional files and empty directories in projected skills | Preserve them and continue. Conflict only when a planned write/delete would affect an unowned file or a changed managed file. Cleanup derives ancestors from previously owned file paths, never inventories unknown directories for deletion. A file already equal to the requested new bytes needs no overwrite conflict. |
| Hardlinked source/target reads | Allow them. Target replacement is atomic and does not mutate another hardlink in place. Keep protection where a subprocess may actually rewrite a shared file, and on the mutable OS lock file. |
| Committed recovery | Finish cleanup without requiring old content bytes to match: later user edits are already outside rollback. Skip missing paths, files and linked/reparse paths instead of removing them or blocking cleanup. Uncommitted rollback still checks before/after images to preserve post-crash user changes. |
| Owner marker formatting and annotations | Compare owner/schema/manager/target fields, not serialized bytes. Preserve existing formatting and unrelated metadata when identity is unchanged; explicit manager handoff changes the manager field. Foreign ownership remains a conflict. |
| Uninstalled target removal | No target directory/lock is created for a genuine no-op. An existing receipt without a marker still requires the shared target lock and owner guard while its files are removed. |
| Native pre-marker installation detection | Keep known native plugin entries as evidence requiring explicit handoff. Remove cache-directory and marketplace-entry-only guesses: inert content is not installation authority. An unrelated malformed config is not a reason to block skills-only projection. No client config is edited. |
| Runtime bridge | Remove duplicate write-path/spec validation and Python/pip environment sanitization, unused verify forwarding and the unused `INCOMPLETE` error mapping. Static import still validates locks without Python; OMH owns runtime checks and child environment policy. Bootstrap uses `-I -B`. |
| Pip error handling | Stop translating every failure into missing offline wheels. Preserve timeouts and interpreter errors; a nonzero offline pip result retains the offline-dependency error. Pip configuration remains disabled, hashes enforced, binary-only, and subprocess argv is preserved. |
| Published receipts missing `deploymentRoot` | Retain the optional read and use recorded runtime `root` for target-overlap checks. These records actually exist; they do not need relabeling or a second state database. |
| Historical content missing the runtime provider | Retain Python-free static distribution and omit unsupported binding artifacts. Explicit runtime preparation reports the missing capability; there is no substitute engine or automatic source/download selection. |
| Existing legacy adoption, manager relocation and retired-hook cleanup | Retain the established explicit receipt/journal flows for published data. Do not restore collectors or old install commands, or add aliases for retired environment variables. |
| OS locks, target digests, journal before-images, argv, timeouts, dependency checks and pip isolation | Retain: each protects a demonstrated correctness or user-file boundary. Do not replace these with silent fallback or a second implementation. |

The new preparation descriptor is ownership evidence for an explicit retry, not
a promise that environment creation completed. Ordinary helper execution never
repairs an environment, installs packages, or consults historical marker formats.
A failed new-content preparation leaves prior valid runtime versions and target
receipts usable; explicit repair may rewrite a managed environment that was
already invalid. External environments are always read-only.

Identifier/consumer inventory: `HARNESS_RUNTIME_INCOMPLETE` disappears from the
unpublished provider and its Rust error mapping/test stub; the historical code
and archives stay unchanged. The unused Rust `runtime::verify` forwarding API has
no current callers; actual verification remains in OMH and the protocol's verify
operation. `PreparedRuntime` fields, protocol 1, archive schemas and generation
algorithms retain their names. unrecognized legacy marker files remain untouched, while
runtime execution no longer interprets their format. Target owner JSON fields
retain their meaning and journal guards retain exact observed bytes at apply.

Affected checks are the standalone/runtime module, Rust distribution runtime and
service suites, and the existing temporary-Home cross-repository integration.
The previous broad validation is preserved as historical evidence; this follow-up
does not rerun frontend, native GUI, unrelated content workflows or the full Rust
suite. Windows/macOS native execution remains a separate coverage limit.

---
status: accepted
---

# Reuse validated plugin source and bound Windows copy retries

The observed Codex `plugin add` error combines `failed to copy plugin file` with
`(os error 5)`. Fresh isolated Codex homes also reproduce it, read-only attributes
and later ACL checks do not explain it, and retries sometimes succeed. These
observations do not identify a responsible OS component, security product, or
Codex defect. Local sources also sometimes fail, so changing sources is not a
complete remedy.

## Source and retry policy

Default marketplace registration reuses the already validated canonical checkout
rather than obtaining the same Git tree again. Source binding, complete package
identity validation, and post-install closure remain mandatory. Explicit Git
source/ref requests retain canonical-remote, freshness, clean-checkout and pinned
revision checks, and never fall back to local on failure.

Only on Windows, only for `plugin add`, and only when a nonzero result contains
both exact error markers (case insensitive), retry the same command at most
three times total, sleeping 0.5 then 1 second. Re-evaluate the error on every
failure; a different error stops immediately. Do not restart the complete update,
mutate ACLs, delete caches, or automatically repair a drifted package. Final
failure propagates to existing activation/update rollback. Command success is
not transaction success: closure still gates completed operation and receipts.

Report actual command output, selector, expected package version when known,
stage, attempt and exit status. The validated source path is not a claim about
Codex's internal temporary copy source/destination. Preserve those actual paths
only when Codex itself reports them; do not fabricate a staging path.

The supported complete upgrade remains `omh update --channel main` (or the saved
channel via `omh update`). A plugin-level upgrade still uses Codex Copy. Repair
and reinstall recover a recorded revision; they cannot install this fix as an
upgrade substitute.

## Separate instructions issue

Git blob bytes and checkout-materialized bytes are distinct under attributes and
`core.autocrlf`. Instruction copy ownership must compare exact target bytes with
verified materialized source evidence. Immutable Git-source identity remains
separate; never normalize arbitrary target content or reset ownership from an
unverified existing target. Update and rollback must preserve user-edited files.

The journal keeps `instructionsSource` unchanged as immutable Git-blob evidence
for checkpoint validation and old-manager compatibility. Each side separately
records `instructionsMaterializedSha256`: Git's exact checkout result using an
isolated index and empty worktree, the revision's attributes, and the repository's
conversion configuration. New resume/recovery fills this field for old journals
from Git evidence, never the installed target. Recorded evidence is revalidated;
conversion drift fails closed rather than replacing its baseline. Refresh uses
the materialized digest instead of accepting an LF/CRLF equivalence class.

On a graceful resumed-update failure, the new executable restores old copy bytes
before an older caller re-enters its rollback executable. Both registries must
resolve the same target and copy strategy. Every existing copy must match an
exact old or new materialized digest; preflight all copies before restoring any.
Existing atomic replacement and race revalidation still apply. Multiple logical
harnesses sharing one physical copy are preflighted separately and written once
only when source path, source digest and target snapshot agree. Conflicts fail
before any writes; logical harness receipts remain distinct. Changed targets
are preserved, and the update/rollback journal remains the failure authority.
Explicit recovery running the new code performs this bridge before switching
back to the old revision as well.

This cannot retrofit code into an already-running old manager. An abrupt kill
that leaves recovery executing solely from an old checkout can still require a
fixed recovery executable. An explicit downgrade to an old manager can still
refuse converted copies; it must roll back safely rather than broaden ownership.
These cases are not evidence of successful old-manager recovery or downgrade.

Behavior tests simulate copy denial deterministically; Git newline conversion
fixtures exercise actual Git materialization. Neither is evidence of a real
Windows Codex integration run or of elimination of the intermittent upstream
failure.

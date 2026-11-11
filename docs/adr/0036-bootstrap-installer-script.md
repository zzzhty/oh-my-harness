---
status: accepted
---

# Bootstrap installer script

Multiple hosts each need an OMH installation, and cloning a checkout by hand
on every machine no longer scales. The historical lifecycle manager (self-
update, state database, refresh --repair) stays retired: what is missing is
not manager capability but source acquisition. Decision: a stateless POSIX
`install.sh` at the repository root, reachable at
`https://raw.githubusercontent.com/zzzhty/oh-my-harness/main/install.sh`,
that fetches a verified release checkout and delegates to the existing
standalone CLI. It runs once and exits — no state, no daemon, no self-update.

1. **Acquisition with verification.** The script resolves a version from
   `OMH_VERSION` or one unauthenticated `releases/latest` API call, downloads
   the release's own source archive asset (`omh-<tag>.src.tar.gz`), and
   verifies its sha256 against the sibling digest asset
   (`omh-<tag>.src.tar.gz.sha256`), both served from predictable
   `releases/download/<tag>/` URLs — no API call for either, and both are
   immutable with their release. The archive is packed by the release
   process on purpose: GitHub's auto-generated codeload archives are not
   byte-stable by contract, so a digest over them could silently break on
   regeneration. Each release therefore gains two publication steps: upload
   the archive and its digest. The script itself is trusted via TLS and can
   be pinned to `refs/tags/<tag>/install.sh`. ADR 0031's "release = tagged
   source checkout, installed from a verified source tree" is unchanged:
   the installer only acquires and verifies.
2. **Placement and versioning.** The checkout lands in
   `~/.oh-my-harness/src/<tag>/` — inside the manager home, outside every
   target (the existing home/target separation checks apply unchanged).
   Versions coexist; nothing is pruned automatically, matching the
   no-deletion philosophy. Running `omh install` from a new checkout
   re-points the launcher shim at it under the existing ADR 0033 ownership
   rules; an unowned shim still fails closed. Upgrade to a new version =
   re-run the installer with the new tag (idempotent); rollback = re-run an
   older tag. This is the stateless equivalent of the retired git
   self-updater: upgrades stay explicit, never drift.
3. **Interpreter policy.** The script probes `python3` for ≥ 3.11 and
   validates that it can seed a `venv --copies` standard-library environment,
   failing closed with the process tail. Reason: relocated builds (e.g.
   uv-managed CPython with a private compile prefix) can satisfy the version
   check while their copied venv interpreters cannot locate the standard
   library — observed on the reference machine, where existing runtimes work
   but fresh preparation must pass `--python /usr/bin/python3`. `OMH_PYTHON`
   passes through to the CLI's existing chain (`--python`, then `OMH_PYTHON`,
   then the launching interpreter). The installer never installs Python.
4. **Parameters and fleet use.** `OMH_VERSION`, `OMH_HARNESS` (comma list,
   default `codex`), `OMH_HOME`, `OMH_REPO`, plus local-tarball fixture hooks
   for testing. Each host keeps its autonomous home, receipts and locks —
   no central fleet state, by design; fleet consistency comes from pinning
   `OMH_VERSION` in configuration management, and the CLI's `--json`/stderr/
   exit-code contract (ADR 0035) makes the wrapper script-friendly. Windows
   and non-GitHub hosts keep the documented manual path.

The installer never mutates targets itself; every mutation still goes through
the standalone CLI as the sole distribution channel.

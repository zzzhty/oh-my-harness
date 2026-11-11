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
   `OMH_VERSION` or one unauthenticated `releases/latest` API call, then
   clones over HTTPS with `git clone --branch <tag>` — hosts require git.
   Verification pins content to the release record: each release publishes
   one asset, `omh-<tag>.ref`, a one-line file holding the tag's commit SHA
   (`git rev-parse <tag>^{}`); the script compares `git ls-remote
   refs/tags/<tag>^{}` against it before cloning and `git rev-parse HEAD`
   after checkout. Tags can be reissued (the 1.1.1 reissue replaced its
   tag), so upgrades fetch with `--tags --force`. The release process
   gains one step: upload the ref asset. The script itself is trusted via
   TLS and can be pinned to `refs/tags/<tag>/install.sh`. ADR 0031's
   "release = tagged source checkout, installed from a verified source
   tree" is unchanged: the installer only acquires and verifies.
2. **Placement and upgrade form.** One clone lives at `~/.oh-my-harness/repo`
   — directly inside the manager home, beside its siblings (`runtimes/`,
   `cache/`, `transactions/`, the state files), and outside every target
   (the existing home/target separation checks apply unchanged); migrating
   an existing host is moving its clone there and re-running `install` to
   re-point the shim. Upgrading is the native git flow — `git fetch --tags
   --force && git checkout <tag> && omh update` — either re-run by the
   installer (it detects the existing clone and performs the same steps,
   after the same ref verification) or typed directly on the host without
   curl. Rollback is checking out an older tag. Versions no longer
   coexist as sibling directories; the launcher shim keeps pointing at
   the same path across upgrades, and `omh update` refreshes installed
   targets from the re-checked-out source. Deleting the checkout still
   breaks `omh` by design (ADR 0033 pointer semantics). Upgrades stay
   explicit — the stateless replacement for the retired git self-updater.
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
   default `codex`), `OMH_HOME`, `OMH_REPO` (accepts local paths, which is
   also the fixture hook for testing), `OMH_REF_URL` for the verification
   asset. Each host keeps its autonomous home, receipts and locks —
   no central fleet state, by design; fleet consistency comes from pinning
   `OMH_VERSION` in configuration management, and the CLI's `--json`/stderr/
   exit-code contract (ADR 0035) makes the wrapper script-friendly. Hosts
   upgrade without curl through the native git flow. Windows and non-GitHub
   hosts keep the documented manual path.

The installer never mutates targets itself; every mutation still goes through
the standalone CLI as the sole distribution channel.

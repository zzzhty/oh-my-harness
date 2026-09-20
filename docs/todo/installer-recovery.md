# Installer recovery (PR #21)

Scope: complete the explicit installer repair/reinstall entry point, publish the
feature branch and close PR #21 as requested. The real managed installation is
not a test target; merge and managed activation are outside this handoff.

## Plan

1. Classify fresh, incomplete, ready and legacy-ready installs in shared Python;
   require a deliberate repair/reinstall choice for ready installs.
2. Reuse the manager bootstrap, locking, update recovery and harness closure.
   Preserve immutable receipts, desired policy, unknown files and user data.
3. Cover both public wrappers, cancellation, invalid ownership/state, legacy
   current-revision migration, exact incomplete recovery and reinstall failure.
4. Align README/ADR, remove the PR's temporary snapshot workflow, run affected
   checks and record coverage here.

## Contract inventory

- Public installer flags (`--repair`, adoption and fast-forward flags): preserve
  identities; make repair explicit and add mutually exclusive `--reinstall`.
- `state/install.json`: immutable persisted initial receipt; only the original
  `installing` to `ready` completion may write it.
- `manager.json` / `desired.json`: existing persisted lifecycle owners and schema;
  preserve current values. A legacy ready install has neither; derive them from
  its verified current managed checkout, never the invoking checkout or old SHA.
- Managed paths, launchers, update journal and ownership checks: retain existing
  identities and contracts. Reinstall stays at the recorded revision and uses
  existing recovery owners, with replaced managed components backed up.

## Progress

- PR fetched at `a42079ec8a056dc5f1537fbd9f05a7bb84b78898`; only a temporary
  snapshot workflow was present. Development and managed checkouts were clean.
- Found automatic repair bypassing incomplete-install validation and repair
  rewriting ready install receipts. Both are in the implementation scope.
- Local implementation complete: explicit selection; strict incomplete recovery;
  current-revision legacy migration; exact-version reinstall with checkout/runtime
  backups; receipt/policy preservation; read-only previews including import caches.
- Removed the temporary snapshot workflow. README and ADR 0017 describe the
  resulting behavior. PowerShell relies on persisted user PATH and reopening the
  terminal, so help/cancellation cannot alter session PATH.

## Validation (2026-09-20, macOS / Python 3.13.15)

Use `/Users/max/.oh-my-harness/venv/bin/python -B` with
`PYTHONDONTWRITEBYTECODE=1`. All runs use disposable manager homes; the actual
managed checkout remains clean and was not activated or changed.

- Root unittest discovery: 305 tests, 6 platform skips, no failures, before the
  final recovery-boundary refinements. Unaffected results remain applicable.
- Final affected coverage: `test_installer_recovery*.py` (18 tests),
  `test_install_oh_my_harness.py` (27 tests, 2 skips),
  `test_manager_commands.py` (11 tests), and `test_install_wrappers.py`
  (4 tests, 2 skips): 60 tests total, 4 platform skips, no failures.
- Public integration exercised initial install, repair, reinstall, missing-repo
  recovery, legacy migration, public `omh check`, exact-revision retention and
  preservation of unrelated skills, receipt, policy and backup contents.
  Dependencies were provisioned offline into real disposable venvs; this is not
  evidence of a live pip/network installation. Managed-checkout dry runs were
  also exercised without `PYTHONDONTWRITEBYTECODE` to verify no import caches.
- `git diff --check` and `sh -n install.sh` passed.
- Native Windows/PowerShell and Linux execution remain unverified for this diff;
  the existing lifecycle CI matrix owns those checks after publication.

## Handoff

The implementation is on `fix/installer-repair-reinstall`, based on PR #21's
`a42079e`. After local validation, the user requested committing and pushing the
changes, then closing PR #21. Retain the feature branch; do not merge it or
activate the managed installation. The PR records the resulting commit and
publication status. Native cross-platform CI remains unverified unless a run
against that published commit completes successfully.

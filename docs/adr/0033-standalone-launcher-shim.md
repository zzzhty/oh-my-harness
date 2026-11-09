---
status: accepted
---

# Standalone launcher shim

The standalone CLI is invoked as `python -B -m omh` from a source checkout.
For daily convenience, `install` and `update` also write a small POSIX shim
`omh` into `~/.local/bin` (overridable with an absolute `--bin-dir`), so the
usual commands become `omh status`, `omh update`, and so on.

## What the shim is

A generated `/bin/sh` script whose second line is the managed marker
`# oh-my-harness standalone launcher v1`. It exports `PYTHONPATH` pinned to the
installing source checkout, sets nothing else, and `exec`s the exact absolute
interpreter recorded at install time with `-B -m omh "$@"`. The inherited
`PYTHONPATH` is replaced, not extended: the CLI resolves against the checkout
deterministically.

It is a pointer, not a manager. This is the boundary against the retired 1.0.0
lifecycle manager (ADR 0028): the shim owns no repository checkout, no venv, no
installed-state database, no lock and no self-update. Updating means pulling
the checkout and running `omh update`; nothing refreshes itself. If the
checkout or interpreter disappears, the forwarded command fails with the
interpreter's own module-not-found error — the shim never searches `PATH`,
substitutes an interpreter, or falls back. The shim is not an owner and takes
no part in ownership decisions; receipts, journals and the owner lock are
unchanged.

## Lifecycle and conflicts

- `install` and `update` preflight the shim location before any mutation and
  rewrite it (idempotently, with the executable bit) after a committed
  transaction; its record lives in `<home>/shim.json`.
- An existing unowned `omh` file in the bin directory fails with
  `HARNESS_CONFLICT` before the transaction runs.
- `uninstall` removes the shim only when its second line is the managed
  marker, and removes the record. Removing one target while another remains
  also removes the shim; rerun `install` to recreate it.
- `prepare`, `plan` and `status` never touch the bin directory.
- Windows has no shim in this decision; use the full `python -B -m omh`
  command there.

# Oh My Harness — Content Hub

OMH maintains versioned skills, script resources, compositions and historical
report/audit helpers. [ATM](https://github.com/zzzhty/ai-tooling-manager) imports
and distributes these releases through one Rust core. OMH no longer installs a
Python lifecycle manager or maintains a second active home beside ATM.

The default composition contains 30 skills in `maintenance`, `workflow` and
`mattpocock-skills`. The four maintenance skills remain independent callable
workflows: doc-alignment, housekeeping, skill-maintainer and skill-compressor.
Skill-watcher collection and its hooks are retired. Historical reports, aliases,
logs and explicit audit tools remain supported; mentions, selections and declared
dependencies are not evidence of execution.

## Content and ownership

- `plugins/*/skills/*/SKILL.md` is the authored skill source. Invocation and
  permission boundaries stay with each skill; importing does not invoke it.
- `content-manifest.json` declares packages, the default composition and optional
  runtime groups. It contains no target paths or executable install instructions.
- The shared Rust exporter produces a `.omh` archive and a separate version lock
  pinning repository, revision, release asset and verified bytes. ATM keeps the
  installed receipt separately, protecting user changes and one physical owner.
- `runtimes/watcher` contains optional historical report/audit helpers. It consumes
  versioned `canonical-catalog.json`, without scanning an OMH checkout or importing
  the former Python installer. Attribution overlays are metadata, not hooks.
- `agents/global-instructions.md` owns distributed global policy; `AGENTS.md` owns
  local source routing. [CONTEXT.md](CONTEXT.md) defines the domain language.

ATM uses its own `~/.atm` cache, receipts and selected final-path Python venvs.
Static skill distribution needs no Python. Script runtimes use an explicitly
prepared interpreter; project `.venv` and global Python are outside its ownership.
Existing `.oh-my-harness` installations need an explicit ATM adoption/migration
with retained backups. Do not run historical installer commands or delete an old
manager until its receipts, target references and recovery state have been handled.

## Consume a locked release

Select and review the release lock before importing it. Example commands use
absolute paths and never enable hooks:

```sh
atm harness import --lock /absolute/omh.lock.json --archive /absolute/omh.omh
# Read the returned source path; selecting and applying it are separate steps.
atm harness sync --source /absolute/verified/cache
atm harness plan refresh --harness claude-code,codex
atm update skills --harness claude-code,codex
```

For a new ATM installation use `bootstrap --source` instead of `sync`, then
`plan install` and `install skills`. Omit `--archive` only to acquire the exact
HTTPS release artifact named by the locally selected lock. A complete verified
cache works offline. Client loading/invocation needs separate acceptance from
successful disk distribution. See [ATM's content contract](https://github.com/zzzhty/ai-tooling-manager/blob/main/docs/OMH_CONTENT_CONTRACT.md).

## Validate and export content

Use an isolated developer venv with `requirements.txt`. Developer tests use Python;
that does not make Python part of ATM's static distribution path.

```sh
python -m unittest discover -s tests -p 'test_*.py'
python -m unittest discover -s runtimes/watcher/tests -p 'test_*.py'
python -m unittest discover -s plugins/maintenance/tests -p 'test_*.py'
python -m unittest discover -s plugins/workflow/tests -p 'test_*.py'
```

After all packaged edits and their tests, update generations once with
`python scripts/update_plugin_generations.py --release-version <version>`, then
run `python scripts/check_plugin_generations.py`. Preserve upstream notices and
local adaptations. Generation identity verifies package bytes, not semantic
instruction equivalence.

`tooling/atm-revision.txt` pins the shared Rust exporter. Build `atm-cli` from that
ATM revision; do not copy its implementation into OMH. Run:

```sh
python scripts/check_content_export.py --atm /absolute/path/to/atm
```

This checks export, import, catalog-only runtime health and both client adapters
inside a temporary Home. To produce release artifacts, from a clean committed
checkout run the same pinned Rust executable:

```sh
atm harness export --source /absolute/oh-my-harness --output /absolute/omh.omh \
  --repository https://github.com/zzzhty/oh-my-harness --revision <full-commit-sha> \
  --url https://github.com/zzzhty/oh-my-harness/releases/download/v1.2.0/omh.omh
```

The exporter refuses existing outputs. Publish `omh.omh` and `omh.lock.json` on the
release for that exact tested revision; never replace an existing version's
assets. Normal CI validates Linux/macOS/Windows on Python 3.11/3.12. Release
publication is explicit after those checks pass.

## Decisions and history

[ADR 0028](docs/adr/0028-publish-content-through-atm.md) records the installer,
package and ownership transition and maps retired implementation tests to ATM's
Rust gates. [ADR 0027](docs/adr/0027-report-watcher-evidence-without-execution-claims.md)
owns historical report evidence semantics. Earlier ADRs, lifecycle runbooks and
`dev_docs/` remain historical evidence; they do not authorize restarting the retired
installer or collector. No server, accounts or marketplace service is required.

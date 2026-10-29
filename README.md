# Oh My Harness — Content Hub

OMH maintains versioned skills, their script resources and compositions. [ATM](https://github.com/zzzhty/ai-tooling-manager) imports
and distributes these releases through one Rust core. OMH no longer installs a
Python lifecycle manager or maintains a second active home beside ATM.

The default composition contains 29 skills in `maintenance`, `workflow` and
`mattpocock-skills`. The three maintenance skills remain independent callable
workflows: doc-alignment, housekeeping and skill-compressor.
The 1.1.0 boundary retires Watcher collection, hooks and historical report support.
Skill-owned auditing and new report generation remain supported. The retired skill-maintainer workflow is replaced by the existing
`mattpocock-skills:writing-for-agents` for agent-guidance authoring; no new
replacement skill or installation CLI is added.

## Independent release versions

OMH versions its content independently of the ATM application. **1.1.0** names
the pure Hub release line; ATM **0.2.0** consumes its exact revision and content lock.
Neither product's version requires the other product to use the same number.

The published historical [`v1.0.0` release](https://github.com/zzzhty/oh-my-harness/releases/tag/v1.0.0) records the last pre-Hub source baseline,
`e0ce46da5e1cbca5313a6db14401cdfa07b4d5a7`, including the Watcher evidence fix.
It is the last baseline containing the old distribution mechanism and Watcher
automatic collection hooks. It is not the current Hub and has no `.omh` content
assets. The obsolete `v1.2.0` tag, release and attached assets were removed during
the October 2026 history correction; they are not a retained recovery draft.
The published [`v1.1.0` release](https://github.com/zzzhty/oh-my-harness/releases/tag/v1.1.0)
records the corrected Hub baseline. Existing local backups and installed data
are separate from remote release availability.

Existing 1.2.0 caches, receipts and runtime directories keep their original
identities. Selecting 1.1.0 is an explicit ATM content migration: import its new
lock/archive, preview the target changes and apply them separately. Do not edit
installed receipts, relabel old caches or restore the retired Python installer.
Publishing this version does not migrate an existing Home installation.

## Distribution boundary

OMH publishes content and its contracts. It does not provide an installation CLI,
a Python installable package, a second distribution engine, or maintained hook
content. Audit and validation helpers belong to their consuming skills and are not
automatic hooks. Compatibility must not restore the retired collector. The official installer is the Rust `atm` CLI from the ATM repository; it can be built and used
without the desktop application. Python is needed only for explicitly selected
content helpers, not static skill distribution.

Users distributing the content without ATM maintain their own shell scripts,
client adapters and ownership rules. Those tools are outside OMH's compatibility
and installation policy. Do not treat a content release as permission to replace
client configuration or take ownership of an existing installation.

## Content and ownership

- `plugins/*/skills/*/SKILL.md` is the authored skill source. Invocation and
  permission boundaries stay with each skill; importing does not invoke it.
- `content-manifest.json` declares packages, the default composition and optional
  runtime groups. It contains no target paths or executable install instructions.
- The shared Rust exporter produces a `.omh` archive and a separate version lock
  pinning repository, revision, release asset and verified bytes. ATM keeps the
  installed receipt separately, protecting user changes and one physical owner.
- Skill-associated helpers are packaged inside the owning skill. `doc-alignment`
  declares its audit scripts and config; its explicit state directory does not
  discover or migrate historical Watcher data. Only the `maintenance` and
  `workflow` standard-library Python groups remain; no unused YAML venv is shipped.
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

This checks export, import, skill-owned helpers and both client adapters
inside a temporary Home. To produce release artifacts, from a clean committed
checkout run the same pinned Rust executable:

```sh
atm harness export --source /absolute/oh-my-harness --output /absolute/omh.omh \
  --repository https://github.com/zzzhty/oh-my-harness --revision <full-commit-sha> \
  --url https://github.com/zzzhty/oh-my-harness/releases/download/v1.1.0/omh.omh
```

The exporter refuses existing outputs. Publish `omh.omh` and `omh.lock.json` on the
release for that exact tested revision; never replace an existing version's
assets. Normal CI validates Linux/macOS/Windows on Python 3.11/3.12. Release
publication is explicit after those checks pass.

## Decisions and history

[ADR 0029](docs/adr/0029-pure-hub-with-skill-owned-helpers.md) records the 1.0/1.1
version boundary, retired capabilities and the skill-owned helper migration.

[ADR 0028](docs/adr/0028-publish-content-through-atm.md) records the installer,
package and ownership transition and maps retired implementation tests to ATM's
Rust gates. [ADR 0027](docs/adr/0027-report-watcher-evidence-without-execution-claims.md)
owns historical report evidence semantics. Earlier ADRs, retired lifecycle runbooks and dated pre-rebuild entries in
`dev_docs/` remain historical evidence; they do not authorize restarting the retired
installer or collector. Current upstream selections and validation are recorded in
[the upstream review record](dev_docs/mattpocock-upstream-review.md). No server, accounts or marketplace service is required.

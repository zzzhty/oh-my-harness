# Oh My Harness

This context describes the language used for canonical skill source, harness distributions, skill-owned documentation audits, and plugin-provided skill systems.

Definitions describe current repository behavior. Use the [ADR index](docs/adr/README.md) when earlier terminology or migration rationale is needed.

## Language

### Harness Distribution

**Canonical Skill Source**:
The version-controlled OMH content under plugins/*/skills/*/SKILL.md, from which versioned releases and client projections are derived.
_Avoid_: plugin cache authority, marketplace authority, installed source

**Catalog Skill Name**:
The bare name declared by a skill's `SKILL.md` frontmatter and used as the repository catalog key and directory-projection basename.
_Avoid_: harness-independent invocation identity, plugin-qualified identity, physical directory name

**Harness**:
A client target selected by the installation owner. The standalone distributor resolves it to a skills root and the native instructions filename.
_Avoid_: registry entry, independently selected instructions target

**Harness Plan**:
A read-only preview of changes for one resolved target and one operation (install, refresh, or uninstall), produced by `omh plan`. It does not prepare runtimes or take ownership.

**Harness Skill Projection**:
The managed exposure of canonical skill directories for harness-native discovery; it is neither source nor cache.
_Avoid_: direct source, copied catalog, plugin cache

**Harness Instructions Projection**:
The native global instructions file beside the skills root, derived from `agents/global-instructions.md` and owned through the same target receipt as the skills. See [standalone installation](README.md#standalone-installation) for filenames and conflict handling. Repository-root `AGENTS.md` is local routing, not the global source.

**Skill Request Reference**:
The name or explicit token used to request a skill. Invocation syntax belongs to the host; a catalog name does not guarantee identical syntax across harnesses.

**Distribution Package Identity**:
A content-derived identity for a complete package, separate from a skill name, an invocation token, or an installed-target receipt.

### Skill-owned helpers

**Audit Helper**:
A script shipped inside the skill whose workflow consumes it. The skill declares
its optional Python group and explicit output boundary; importing content never
runs the helper or enables hooks.

**Audit Checkpoint**:
State written to the doc-alignment caller's explicitly selected directory for
current commit thresholds and finding deltas. It does not discover or migrate
historical Watcher logs or reports.

Watcher collection, attribution aliases, historical report readers and the
skill-maintainer proposal pipeline are retired in 1.1.0. Historical source and
terminology remain in the 1.0.0 baseline and archival ADRs, not a current runtime.

### Content Release and Installation

**Content Manifest**:
OMH's versioned declaration of packages, internal resources, compositions and optional runtime requirements.
_Avoid_: installation receipt, target-path policy

**Release Ref**:
The commit SHA in the release's `omh-<tag>.ref` file, checked against the source tag before a managed bootstrap changes its checkout. It is not installed-target state.

**Install Receipt**:
The installation owner's record of actual target roots, owned resources, runtime references and recovery state. The OMH standalone distributor writes the current receipts; historical receipts remain persisted evidence until their homes are handed over.
_Avoid_: upstream manifest, content cache

**Composition**:
A named complete set of content packages in one release; native plugin identities always describe whole packages.
_Avoid_: partial native plugin, automatically enabled hooks

**Standalone Distribution**:
The Python distributor projects skills and global instructions using a target receipt, shared owner lock and recoverable file journal. Bootstrap and manager commands delegate target projection to it.

**Launcher Shim**:
The managed-marker `omh` pointer script in `~/.local/bin`, pinned to the installing checkout and interpreter. A static forwarding script, distinct from the optional Rust manager binary.

**Runtime Deployment Root**:
Storage for final-path Python venvs, distinct from a harness skill target. OMH owns the shared preparation/verification/startup implementation; the installation owner supplies defaults or explicit paths.

**Runtime Binding**:
Owner-generated `.omh-runtime` files that persist the interpreter and dependency contract across sessions. `OMH_PYTHON` is an explicit invocation override, never an automatic PATH fallback.

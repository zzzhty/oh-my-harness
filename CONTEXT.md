# OMH Content Hub

This context describes the language used for canonical skill source, harness distributions, Watcher usage data, documentation audits, and plugin-provided skill systems.

## Language

### Harness Distribution

**Canonical Skill Source**:
The version-controlled OMH content under plugins/*/skills/*/SKILL.md, from which versioned releases and client projections are derived.
_Avoid_: plugin cache authority, marketplace authority, installed source

**Catalog Skill Name**:
The bare name declared by a skill's `SKILL.md` frontmatter and used as the repository catalog key and directory-projection basename.
_Avoid_: harness-independent invocation identity, plugin-qualified identity, physical directory name

**Harness**:
A client target resolved and managed by ATM according to local policy; content imports do not select or enable targets.
_Avoid_: skills target plus instructions target, mode, product name without a registry entry

**Harness Registry**:
The ATM-owned local policy that declares supported target adapters and host paths. OMH content does not supply this policy.
_Avoid_: shell path table, command template registry, duplicated wrapper defaults

**Harness Plan**:
The validated, platform-resolved distribution plan produced from one Harness Registry entry.
_Avoid_: independently selected skills and instructions plans, implicit fallback plan

**Excluded Skill Root**:
A skill-discovery root intentionally outside every Harness Plan because it would duplicate catalog identities or conflict with product-specific discovery; registry-selected refresh and closure require canonical repository identities to be absent there.
_Avoid_: shared harness, partial harness, implicit cleanup target

**Harness Skill Projection**:
A managed user-level exposure of canonical skill directories for harness-native discovery; it is neither source nor cache.
_Avoid_: direct source, copied catalog, plugin cache

**Codex Marketplace Distribution**:
The `codex` harness skills driver that installs the exact skills-bearing package set selected by the Codex install manifest and requires every Excluded Skill Root to be clear of repository catalog identities.
_Avoid_: `$CODEX_HOME/skills` projection, optional partial plugin mode, directory projection

**Harness Instructions Projection**:
The registry-selected global instructions file derived from `agents/global-instructions.md`; a Harness Plan with managed instructions owns exactly one such projection, while an explicit skills-only plan owns none. Root `AGENTS.md` is repository-local routing, not a global instructions source.
_Avoid_: `~/.agents/AGENTS.md`, independently selected instructions harness, silent replacement

**Codex Invocation Identity**:
The plugin-qualified identity `${plugin}:${catalog-name}` that Codex exposes through the Codex Marketplace Distribution.
_Avoid_: bare catalog name, cross-harness identity promise, request reference, distribution package identity

**Skill Request Reference**:
A prompt-level name or explicit token used to request a skill; a bare reference may match a harness-native identity or resolve to a plugin-qualified Codex identity.
_Avoid_: harness-independent invocation identity, distribution identity

**Watcher Skill Identity**:
A namespaced durable identifier used for Watcher attribution and historical interpretation; it may share spelling with a Codex invocation identity while remaining a separate persisted concept.
_Avoid_: catalog skill name, request reference

**Distribution Package Identity**:
The installable plugin coordinate used to package and select a group of skills, separate from skill names and invocation identities.
_Avoid_: Codex invocation identity, Watcher skill identity

### Watcher Attribution and Runtime

**Primary Skill**:
A historical event field containing an asserted entry-skill attribution. Its source determines whether it is a selection assertion, text mention or unclassified observation; it does not prove execution.
_Avoid_: active skill, single skill context

**Supporting Skill**:
A historical attribution field for a declared dependency or asserted supporting role. Its presence does not prove that skill loaded or executed.
_Avoid_: secondary skill, indirect skill, dependency skill

**Effective Skill**:
A legacy persisted attribution label retained for reading old records. Current reports classify its evidence and leave execution unknown.
_Avoid_: combined usage, actual skill

**Effective Turns**:
A legacy count based on effective attribution fields, retained as historical terminology. Current reports use observed, mention, selection and dependency counts without execution claims.
_Avoid_: primary turns, skill mentions

**Primary Turns**:
The legacy count of turn summaries with a primary attribution field; an attribution count does not establish skill execution.
_Avoid_: effective turns, raw events

**Supporting Turns**:
The legacy count of turn summaries with supporting attribution fields; these can reflect declared dependencies only.
_Avoid_: primary turns, mentioned turns

**Supporting-only Skill**:
A legacy report label for a skill with supporting records and no primary records. Current reports describe dependency observations.
_Avoid_: unused skill, zero-hit skill

**Zero Effective Usage**:
A legacy report label for missing primary/supporting observations in a window. It cannot establish that a skill was unused.
_Avoid_: zero primary usage, low usage

**Skill Dependency Map**:
A declared relationship that lists which supporting skills belong to a primary skill's workflow.
_Avoid_: inferred dependency, text-matched dependency

**Mentioned Skill**:
A skill name or alias observed in runtime text that may provide attribution evidence but does not by itself prove workflow use.
_Avoid_: supporting skill, effective skill

**Skill Attribution Overlay**:
A repository-owned, non-callable declaration at `.codex-plugin/skill-watcher.json` that attaches Watcher roles, aliases, legacy names, logical groups, and supporting-skill relationships to identities derived from the canonical skill catalog.
_Avoid_: callable catalog, plugin manifest authority, marketplace enumeration

**Incremental Metadata Index**:
A repository-owned attribution layer added beside upstream skill instructions to improve attribution and reporting without changing the skill instructions themselves or enumerating callable skills.
_Avoid_: behavior patch, upstream skill edit

**Typed Alias**:
An alias with an explicit kind and matching strategy so runtime matching can distinguish exact skill names, slugs, phrases, and risky natural-language terms.
_Avoid_: substring alias, untyped alias

**Skill Role**:
A metadata classification that explains how a skill is normally used in a skill system: entrypoint, wrapper, discipline, or specialized.
_Avoid_: usage count bucket, deletion signal

**Runtime Metadata Cache**:
A historical metadata cache or explicit projection of the versioned canonical catalog JSON, used by reports. No SessionStart collector refreshes it.
_Avoid_: callable source of truth, plugin-cache authority, hand-maintained allowlist

**Skill Attribution**:
The structured explanation of why a turn is associated with primary, supporting, effective, or mentioned skills.
_Avoid_: skill name, active skill

**Turn Summary**:
A persisted turn-level observation used by historical reports. It may contain mentions, selection assertions, dependencies and unknown outcomes; it does not prove execution.
_Avoid_: raw event aggregate, tool event count

**Tool Failure Observation**:
A record that a tool call failed during a turn; it is diagnostic evidence, not a task outcome by itself.
_Avoid_: skill failure, task failure

**Watcher Skill Schema Migration**:
An explicit reset of Watcher skill-domain runtime state from one event schema to another, with old logs archived rather than mixed with new events.
_Avoid_: automatic compatibility, mixed-schema log

**Watcher Consolidation**:
The historical packaging decision that combined shared helpers; current maintenance skills retain distinct invocation boundaries after the runtime split.
_Avoid_: skill merger, giant watcher skill

**Watcher Runtime Root**:
The consolidated runtime state root at `$CODEX_HOME/watcher/`, with domain-specific state under `skill/` and `doc/`.
_Avoid_: shared flat reports directory, old per-plugin runtime root

**Watcher Plugin**:
The retired packaging that combined maintenance skills and Watcher runtime. Current callable skills live in maintenance; historical report/audit helpers live in runtimes/watcher.
_Avoid_: doc-watcher as umbrella, skill-watcher as umbrella

**Legacy Attribution Name**:
An old skill identity kept only as reporting and migration metadata so historical or residual signals can resolve to the current canonical watcher skill.
_Avoid_: active skill name, compatibility entrypoint

**Watcher CLI**:
The explicit report/audit entrypoint runtimes/watcher/scripts/watcher, organized by skill and doc domains. Skill observation and hook installation are retired.
_Avoid_: many top-level watcher wrappers, flat universal report command

### Content Release and Installation

**Content Manifest**:
OMH's versioned declaration of packages, internal resources, compositions and optional runtime requirements.
_Avoid_: installation receipt, target-path policy

**Version Lock**:
A locally selected immutable source revision, release artifact and verified content inventory; generated by the shared Rust exporter.
_Avoid_: latest-version selector, install state

**Install Receipt**:
ATM's record of actual target roots, owned resources, runtime references and recovery state.
_Avoid_: upstream manifest, content cache

**Composition**:
A named complete set of content packages in one release; native plugin identities always describe whole packages.
_Avoid_: partial native plugin, automatically enabled hooks

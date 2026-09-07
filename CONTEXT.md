# Watcher

This context describes the language used for canonical skill source, harness distributions, Watcher usage data, documentation audits, and plugin-provided skill systems.

## Language

### Harness Distribution

**Canonical Skill Source**:
The version-controlled repository content from which every discovery or distribution projection is derived.
_Avoid_: plugin cache authority, marketplace authority, installed source

**Catalog Skill Name**:
The bare name declared by a skill's `SKILL.md` frontmatter and used as the repository catalog key and directory-projection basename.
_Avoid_: harness-independent invocation identity, plugin-qualified identity, physical directory name

**Harness**:
A named distribution target that owns one complete plan for skills, global instructions, root resolution, materialization, reconciliation, and optional runtime extras.
_Avoid_: skills target plus instructions target, mode, product name without a registry entry

**Harness Registry**:
The strict repository-owned JSON authority at `.agents/harnesses/registry.json` that declares supported harnesses and their structured distribution behavior.
_Avoid_: shell path table, command template registry, duplicated wrapper defaults

**Harness Plan**:
The validated, platform-resolved distribution plan produced from one Harness Registry entry.
_Avoid_: independently selected skills and instructions plans, implicit fallback plan

**Excluded Skill Root**:
A skill-discovery root that is intentionally outside every Harness Plan because it cannot carry the complete skills-and-instructions bundle or would duplicate catalog identities; registry-selected refresh and closure require canonical repository identities to be absent there.
_Avoid_: shared harness, partial harness, implicit cleanup target

**Harness Skill Projection**:
A managed user-level exposure of canonical skill directories for harness-native discovery; it is neither source nor cache.
_Avoid_: direct source, copied catalog, plugin cache

**Codex Marketplace Distribution**:
The `codex` harness skills driver that installs the exact skills-bearing package set selected by the Codex install manifest and requires every Excluded Skill Root to be clear of repository catalog identities.
_Avoid_: `$CODEX_HOME/skills` projection, optional partial plugin mode, directory projection

**Harness Instructions Projection**:
The registry-selected global instructions file derived from `agents/global-instructions.md`; every Harness Plan owns exactly one such projection. Root `AGENTS.md` is repository-local routing, not a global instructions source.
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
The entry skill that a turn is directly attributed to through an explicit signal or the strongest detected match.
_Avoid_: active skill, single skill context

**Supporting Skill**:
A skill that is directly used or required by the primary skill's workflow but is not the turn's entry point.
_Avoid_: secondary skill, indirect skill, dependency skill

**Effective Skill**:
Any skill whose discipline was exercised in a turn, including both the primary skill and supporting skills.
_Avoid_: combined usage, actual skill

**Effective Turns**:
The count of turn summaries where a skill appears as either the primary skill or a supporting skill.
_Avoid_: primary turns, skill mentions

**Primary Turns**:
The count of turn summaries where a skill is the primary skill.
_Avoid_: effective turns, raw events

**Supporting Turns**:
The count of turn summaries where a skill appears as a supporting skill.
_Avoid_: primary turns, mentioned turns

**Supporting-only Skill**:
A skill with no primary turns but at least one supporting turn in the reporting window.
_Avoid_: unused skill, zero-hit skill

**Zero Effective Usage**:
A reporting result where a skill has no primary turns and no supporting turns in the reporting window.
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
A Watcher-generated runtime projection of the canonical repository catalog plus skill attribution overlays, used by hooks and reports after SessionStart.
_Avoid_: callable source of truth, plugin-cache authority, hand-maintained allowlist

**Skill Attribution**:
The structured explanation of why a turn is associated with primary, supporting, effective, or mentioned skills.
_Avoid_: skill name, active skill

**Turn Summary**:
The turn-level usage fact emitted at the end of a monitored turn and used as the default source for usage reporting.
_Avoid_: raw event aggregate, tool event count

**Tool Failure Observation**:
A record that a tool call failed during a turn; it is diagnostic evidence, not a task outcome by itself.
_Avoid_: skill failure, task failure

**Watcher Skill Schema Migration**:
An explicit reset of Watcher skill-domain runtime state from one event schema to another, with old logs archived rather than mixed with new events.
_Avoid_: automatic compatibility, mixed-schema log

**Watcher Consolidation**:
Combining watcher plugin packaging, shared runtime helpers, validation, and maintenance surfaces while preserving separate skill invocation boundaries.
_Avoid_: skill merger, giant watcher skill

**Watcher Runtime Root**:
The consolidated runtime state root at `$CODEX_HOME/watcher/`, with domain-specific state under `skill/` and `doc/`.
_Avoid_: shared flat reports directory, old per-plugin runtime root

**Watcher Plugin**:
The canonical plugin package named `watcher` that owns both documentation audit and skill usage watcher domains.
_Avoid_: doc-watcher as umbrella, skill-watcher as umbrella

**Legacy Attribution Name**:
An old skill identity kept only as reporting and migration metadata so historical or residual signals can resolve to the current canonical watcher skill.
_Avoid_: active skill name, compatibility entrypoint

**Watcher CLI**:
The consolidated command entrypoint `scripts/watcher`, organized by domain subcommands such as `skill` and `doc`.
_Avoid_: many top-level watcher wrappers, flat universal report command

# Watcher

Watcher consolidates the former DocWatcher and Skill Watcher plugin surfaces into one package while preserving separate skill invocation boundaries.

The plugin owns two runtime domains:

```text
$CODEX_HOME/watcher/
├── doc/
│   ├── audits/
│   ├── reports/
│   └── repo-state.json
└── skill/
    ├── logs/events.jsonl
    ├── reports/
    ├── proposals/
    ├── turns/
    ├── schema-version.json
    └── skill-metadata-cache.json
```

On `SessionStart`, Watcher rebuilds `skill-metadata-cache.json` from the repository-authoritative callable catalog at `scripts/repo_skill_catalog.py` under one explicit oh-my-harness repository root. Marketplace metadata, plugin manifests, plugin cache, and the runtime cache never enumerate callable skills. A missing or invalid explicit repository root, canonical catalog failure, unsupported attribution-overlay schema, or invalid skill relationship stops the refresh visibly.

Repository-owned `.codex-plugin/skill-watcher.json` files are non-callable attribution overlays keyed by durable namespaced Watcher identities. They retain roles, aliases, supporting-skill relationships, logical groups, and legacy mappings without defining the callable inventory. The `supporting_skills` overlay describes unconditional dependencies; alternatives and conditional branches remain undeclared. It does not prove those dependencies loaded or ran. Reports show these relationships as declared dependencies, not effective execution. Use `explicit-workflows` for skills whose contract requires explicit user selection or confirmation and `implicit-primitives` for skills the model may select from natural-language intent. Skill reports display current groups at report time; these categories do not establish historical selection or trigger policy. Only declared `legacy_names` mappings fold historical identities in the view, with raw identities and unmapped names retained. The cache is a projection of repository metadata, not a new authority.

Packaged skills:

- `doc-alignment`: audit or align documentation, scripts, skills, runbooks, operational entry points, and planning folders against current source of truth.
- `housekeeping`: remove inventoried disposable files, generated caches, stale runtime artifacts, and post-migration physical clutter while preserving durable state.
- `skill-maintainer`: analyze recorded skill evidence and propose bounded `SKILL.md` maintenance updates without automatic source mutation.
- `skill-compressor`: reduce skill or plugin instruction footprint while preserving operational semantics.

Current migration scope:

- Source skills and direct skill resources have moved under `plugins/watcher/skills/`.
- Report/audit scripts live behind the unified `plugins/watcher/scripts/watcher` entrypoint.
- Python implementations live in the named `scripts/watcher_runtime/skill` and `scripts/watcher_runtime/doc` packages; callers and tests use those modules through `main(argv)`, not direct script paths.
- The former DocWatcher cockpit backend/frontend and legacy patch/PR/provider/webhook surfaces were not migrated into the active plugin source. Git history remains the recovery path for those retired experiments.

Use the unified CLI from the Watcher plugin root:

```bash
export OH_MY_HARNESS_ROOT="$(git rev-parse --show-toplevel)"
omh_tooling_python="${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python"
"$omh_tooling_python" -B scripts/watcher doc report --config config/repos.example.json --print-report
"$omh_tooling_python" -B scripts/watcher skill report --since 7d
"$omh_tooling_python" -B scripts/watcher skill propose --skill watcher:doc-alignment --skill-dir skills/doc-alignment --since 7d
"$omh_tooling_python" -B scripts/watcher migrate-state --dry-run
```

### Skill evidence and report coverage

`skill report` and `skill summarize` retain their CLI flags and output paths.
Their tables count summarized-turn observations, not skill calls or false positives:

| Evidence | Meaning | Execution status |
| --- | --- | --- |
| `mention` | A name/alias matched prompt or assistant text, including comparisons, negations, tables and quotations. | Unknown |
| `selection` | A hook supplied `skill_name`/`skill`, or a manual collector recorded a selection assertion. | Unknown |
| `dependency` | A supporting relationship was recorded from metadata. | Unknown |
| `unclassified` | Historical attribution lacks a recognized evidence source. | Unknown |

This adapter has no supported host evidence for verified skill loading or invocation.
Even text such as “Use $skill” remains a mention unless a structured selection field
is present. No additional announcement, per-turn recording or transcript scan is
required. The existing bounded, redacted summary/hash policy remains in place;
full conversations, file contents and complete tool responses are not collected.

Only monitored evidence is persisted by default: prompt evidence, structured tool
failure observations and a Stop summary. Other tool events contribute transient
counts. Text such as “error” in a successful command's output is not failure evidence;
only recognized top-level integer process exit fields or boolean error status fields
are considered. Unsupported/text-only responses remain unknown. A tool failure is
an observation, never a skill failure or task outcome. Reports distinguish new
structured observations from historical failures with unspecified provenance.

Tables deduplicate by session/turn (falling back to event ID, then content hash);
the last summary for a repeated turn key wins. Exact duplicate event records are
removed within a report window. Evidence columns, skills and groups overlap and
must not be added as an execution total. Missing Stop, limited monitoring, filtered
events and unavailable native skill IDs prevent a complete denominator. Reports
count explicit `task_outcome` fields only, leave unknown unchanged and show no
success/failure rates. Old raw event outcomes remain visible separately.

Schema 2 and its historical attribution fields remain readable. `effective` is a
preserved compatibility field, not an execution claim; new text matches have no
primary and no effective/dependency expansion. Older `assistant_announcement`
records are interpreted as mentions. Legacy identity folding and current grouping
use the last repository-derived runtime metadata cache; without it, names remain
raw and groups are unavailable. Filters accept canonical and declared legacy names.
Logs, saved reports and existing incremental cursor keys are not rewritten. Old
report implementations do not understand new mention-only records; use this report
runtime to interpret both generations. See [ADR 0027](../../docs/adr/0027-report-watcher-evidence-without-execution-claims.md).

`skill propose` requires the exact log identity in `--skill`; a directory basename cannot identify a namespaced skill. It includes a report for the same identity and window, or reuses `--report <path>` when that report matches both. The generated worksheet preserves the source and snapshot and names a separate candidate file. Materialize the proposed edit there before running the printed validation command; worksheet generation itself performs no candidate validation. A no-change decision needs no candidate.

`config/repos.example.json` resolves the audited checkout from
`OH_MY_HARNESS_ROOT`. Keep that variable bound to the canonical Git worktree so
the same config remains valid when Watcher runs from either source or an
installed plugin cache.

Skill `observe`, `install-hook`, and `doctor` accept `--repo-root`; when omitted they require `OH_MY_HARNESS_ROOT`. Installed command hooks embed the resolved root explicitly, so SessionStart behavior does not depend on the process working directory, a plugin-cache path, or adapter-path inference. `$CODEX_HOME/watcher` remains runtime state only.

Doc audit configs may define multiple named profiles for one repository. Keep current authority,
generated/upstream site, and history scopes separate:

- use `profile: "current-authority"` with explicit `docs`, `authority_paths`, active
  `watch_terms`, and `link_validation.mode: "markdown-relative"`;
- use `profile: "upstream-site"` with the repository's owner checker through
  `link_validation.mode: "owner-command"` instead of applying generic Markdown rules to a
  framework-specific route or asset dialect;
- use `profile: "history"` with `finding_policy: "report-only"` and no active watch terms.

Treat `owner-command` as trusted, unsandboxed execution. Watcher invokes its argv without a
shell, keeps its configured working directory inside the repository, enforces a timeout, and
bounds captured output, but cannot prove that the command is read-only. Review the
repository-owned validation workflow before configuring it.

`authority_paths` is an existence check for configured authority entry points. It does not prove
semantic equality or precedence between documents. The legacy `source_of_truth` config key remains
read-compatible but is deprecated. `check_change_alignment: false` disables the code-without-doc
heuristic for profiles where that comparison is not meaningful.

### Repository skill-root discovery

When `docs` is omitted, Watcher scans the normal entry files and documentation directories plus the
first existing repository skill root in this default priority order:

1. `.agents/skills`
2. `.codex/skills`
3. `.github/skills`
4. `.claude/skills`
5. `.grok/skills`

Watcher checks each complete skill directory, so an empty `.agents/` parent does not shadow an
existing fallback such as `.codex/skills`. Profiles may override the order with a non-empty
`skill_root_candidates` string list. The one-off audit CLI provides the repeatable
`--skill-root-candidate` option for the same purpose.

Use `@repo-skills` as a semantic path in configured `docs` and as a prefix in
`authority_paths`. For example:

```json
{
  "docs": ["AGENTS.md", "@repo-skills"],
  "authority_paths": ["AGENTS.md", "@repo-skills/README.md"]
}
```

The token resolves per repository from the ordered candidates. Ordinary configured paths stay
fail-closed: a literal stale `.codex/skills` path is reported missing and is not silently redirected.
If multiple candidate roots exist, Watcher reports the selected root and the shadowed roots and emits
a Medium finding when the resolved skill scope participates in that profile. A resolved-root change
also changes the effective config hash so commit-dependent audits become due immediately.

This resolver does not locate the Watcher config file itself. A moved
`.codex/watcher-doc-audit.json` still requires the caller's `--config` path to be updated.

Run `"${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python" -B scripts/watcher migrate-state --apply` to move `$CODEX_HOME/skill-watcher/` to `$CODEX_HOME/watcher/skill/` and `$CODEX_HOME/doc-watcher/` to `$CODEX_HOME/watcher/doc/`. The migration refuses to merge if the target already exists.

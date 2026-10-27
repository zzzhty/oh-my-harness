# Documentation Audit

Trigger: read this reference for configured, scheduled, commit-dependent, or one-repository documentation audits. `../SKILL.md` remains the owner of mode selection and the read-only boundary.

## Select The Evidence Branch

If a current report already exists and no fresh audit was requested, review it directly under Report Review; do not generate or run fresh audit commands. Check its repository, revision or time window, profiles, and coverage against the requested scope, and disclose stale or missing evidence.

Otherwise follow Fresh Audit, then review the resulting report.

## Fresh Audit

Resolve this skill's directory, then run the commands below from that directory.
Set `DOC_ALIGNMENT_AUDIT_ROOT` to the target Git worktree for the example config.
Set `DOC_ALIGNMENT_STATE_DIR` to a dedicated output directory outside the target
repository. The helper requires this explicit state path (or `--state-dir`) and
never discovers or migrates old Watcher logs/reports. Use the exact prepared
`maintenance` interpreter from the ATM runtime receipt. These are skill audit
helpers; importing content or preparing Python never enables hooks.

```bash
atm_tooling_python="${ATM_PAYLOAD_PYTHON:?set explicit prepared payload interpreter}"
"$atm_tooling_python" -B scripts/audit_docs.py doctor --config config/repos.example.json
"$atm_tooling_python" -B scripts/audit_docs.py report --config config/repos.example.json --mode commit-dependent --mark-audited --digest
```

Run `scripts/audit_docs.py commit-counter` only when a separate threshold-status preview is needed; `doc report` computes eligibility itself.

Use `config/repos.json` when an approved private config exists. For one repository:

```bash
"$atm_tooling_python" -B scripts/audit_docs.py audit --repo <repo-path> --name <repo-name> --print-report
```

When commit-dependent report skips a repository, record it as skipped. Configuration changes can make a repository due below its commit threshold. A normal repository audit covers its configured profile set; use a profile selector only for an explicit narrow run and do not treat unselected profiles as disabled. If any repository fails, surface the repository, command or path, and exact failure text.

## Profiles And Trust Boundary

Use repository-owned named profiles when current authority, framework-owned site documentation, and history need different checks:

- current authority: active watch terms plus generic Markdown-relative link validation;
- framework-owned site documentation: its owning validator through `owner-command`;
- history: `report-only` findings with no active watch terms.

`owner-command` is trusted, unsandboxed execution. The audit helper constrains its working directory, timeout, and captured output, but it cannot prove the command is read-only. Inspect the repository-owned workflow before enabling it.

Configured `authority_paths` prove only that named entry points exist. They do not prove semantic precedence or equality. Keep change-alignment checks enabled when recent code changed without relevant docs; disable them only when that comparison is intentionally meaningless for the profile. The review workflow in `../SKILL.md` still decides alignment.

## Report Review

Review reports for:

- stale active guidance or history mixed into current navigation;
- mismatched product, command, path, identity, ownership, or validation terms;
- recent behavior changes without current documentation;
- active watch-term hits;
- broken links and missing referenced files;
- resolved skill-root selection and shadowing when repository skill roots participate in the profile.

Completion criterion: apply the selected evidence branch below.

- **Existing report review:** record the report source, applicability, findings, and coverage gaps. No new doctor or audit run is required; do not claim fresh verification.
- **Fresh audit:** doctor and the selected audit/report command complete or their exact failures are recorded; every due or skipped repository is accounted for, and profile trust boundaries are explicit.

Both branches hand findings to the common review workflow and preserve its target-repository read-only boundary.

### Repository skill-root discovery

When `docs` is omitted, The audit helper scans the normal entry files and documentation directories plus the
first existing repository skill root in this default priority order:

1. `.agents/skills`
2. `.codex/skills`
3. `.github/skills`
4. `.claude/skills`
5. `.grok/skills`

The audit helper checks each complete skill directory, so an empty `.agents/` parent does not shadow an
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
If multiple candidate roots exist, The audit helper reports the selected root and the shadowed roots and emits
a Medium finding when the resolved skill scope participates in that profile. A resolved-root change
also changes the effective config hash so commit-dependent audits become due immediately.

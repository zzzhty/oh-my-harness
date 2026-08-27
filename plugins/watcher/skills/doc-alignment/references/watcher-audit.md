# Watcher Doc Audit

Trigger: read this reference for configured, scheduled, commit-dependent, or one-repository Watcher document audits. `../SKILL.md` remains the owner of mode selection and the read-only boundary.

## Configured Audit

Before running config-driven commands, set `OH_MY_HARNESS_ROOT` to the
canonical Git worktree. The example config consumes that explicit root so the
same audit remains valid from the source plugin or an installed plugin cache.

From the Watcher plugin root, start with deterministic evidence:

```bash
omh_tooling_python="${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python"
"$omh_tooling_python" -B scripts/watcher doc doctor --config config/repos.example.json
"$omh_tooling_python" -B scripts/watcher doc commit-counter --config config/repos.example.json
"$omh_tooling_python" -B scripts/watcher doc report --config config/repos.example.json --mode commit-dependent --mark-audited --digest
```

Use `config/repos.json` when an approved private config exists. For one repository:

```bash
"$omh_tooling_python" -B scripts/watcher doc audit --repo <repo-path> --name <repo-name> --print-report
```

When commit-dependent report skips a repository, record it as skipped. Configuration changes can make a repository due below its commit threshold. A normal repository audit covers its configured profile set; use a profile selector only for an explicit narrow run and do not treat unselected profiles as disabled. If any repository fails, surface the repository, command or path, and exact failure text.

## Profiles And Trust Boundary

Use repository-owned named profiles when current authority, framework-owned site documentation, and history need different checks:

- current authority: active watch terms plus generic Markdown-relative link validation;
- framework-owned site documentation: its owning validator through `owner-command`;
- history: `report-only` findings with no active watch terms.

`owner-command` is trusted, unsandboxed execution. Watcher constrains its working directory, timeout, and captured output, but it cannot prove the command is read-only. Inspect the repository-owned workflow before enabling it.

Configured `authority_paths` prove only that named entry points exist. They do not prove semantic precedence or equality. Keep change-alignment checks enabled when recent code changed without relevant docs; disable them only when that comparison is intentionally meaningless for the profile. The review workflow in `../SKILL.md` still decides alignment.

## Report Review

If a current report already exists and no fresh audit was requested, skip audit command generation and review that report directly.

Review reports for:

- stale active guidance or history mixed into current navigation;
- mismatched product, command, path, identity, ownership, or validation terms;
- recent behavior changes without current documentation;
- active watch-term hits;
- broken links and missing referenced files;
- resolved skill-root selection and shadowing when repository skill roots participate in the profile.

Keep scheduled and report-only target repositories non-mutating. Watcher output belongs under `$CODEX_HOME/watcher/doc/` or the explicit output path.

Completion criterion: doctor and the selected audit/report command complete or their exact failures are recorded, every due or skipped repository is accounted for, profile trust boundaries are explicit, and report findings are handed to the common review workflow without mutating report-only targets.

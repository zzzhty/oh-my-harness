# Matt Pocock v1.3.2 release selection — 2026-10-29

> Follow-up — 2026-10-30: the selected changes were merged in [PR #3](https://github.com/zzzhty/oh-my-harness/pull/3), validated on all CI platforms and distributed to Home. The dated preparation results below retain their original scope; see [1.1.1 release notes](../docs/releases/1.1.1.md) for the release handoff.

## Scope and evidence

- User requested stale OMH wording corrections, selective upstream adoption and independent branch validation. No push, PR, merge, release, installation or history rewrite is part of this change.
- Local starting revision: `b0ea6081585558e3a31fcdc267175fbd3e5d22c9`; isolated branch `codex/mattpocock-v1.3.2-review`. This is a current post-rebuild review, unlike the dated archive entries in the older record.
- Trigger: [formal v1.3.2 release](https://github.com/mattpocock/skills/releases/tag/v1.3.2), published 2026-10-29 10:27:41 UTC (not draft/prerelease).
- Compared `v1.3.1` / `24fe0ef7737efae15c87225755e9f6f5965e4888` → `v1.3.2` / `d1478fcb140db0b93c0c8df17bcfd311844749d0`. Annotated target tag: `85cbec972d7a79c278c793d272f7fc715850fad4`. Both exact targets were resolved in a separate upstream checkout; release-after commits were excluded.
- [Published-range comparison](https://github.com/mattpocock/skills/compare/v1.3.1...v1.3.2): 51 commits, 72 net paths. All net paths are classified below: adopt 2, adapt 9, skip 60, defer 1. Counts describe upstream paths, not local files or whole-file replacement.
- Original v1.2.3 derivation, MIT attribution, 20 selected Matt skills and all invocation flags/native metadata remain unchanged. The completed range classification advances review coverage only; selected edits in this branch are not a published/synchronized release.

## Local selection and conflicts

Small behavior improvements are applied to their existing owners. The fresh-context change shared by five retained workflows is implemented once under `agents/global-instructions.md`'s Delegation policy. Existing optional delegation, bounded raw-evidence briefs, native harness controls, read-only assignments and failure reporting still apply. No new scheduler or mandatory agent count is introduced.

`ask-matt` reads a skill before describing it without invoking explicit-only workflows. Mutation evidence belongs to diagnosing-bugs, not permission to edit. `code-review` continues to cover committed, staged, unstaged and untracked work and never configures a tracker. `implement` retains harness-aware loading, missing-method blocking and preservation of unrelated staged content. `tdd` keeps routine test placement within agreed boundaries free from repeated approval. `grilling` does not turn a yes into unrelated authorization. Handoff keeps user-selected paths first. Teach preserves the workspace glossary and flexible quiz lengths.

The retained skill files `codebase-design/DESIGN-IT-TWICE.md`, `improve-codebase-architecture/SKILL.md` and `research/SKILL.md` do not need duplicate wording: their existing authorized delegation uses the shared global owner. Upstream docs are explanatory website copy, not new local skill owners. Upstream setup/triage automation and unselected skills are skipped, including in-progress chief-of-staff's additional wiki/scheduler and all-task delegation model.

## Deferred work carried forward

The v1.3.1 unresolved set remains three original paths at `24fe0ef7737efae15c87225755e9f6f5965e4888`: `docs/engineering/implement-spec.md`, `skills/engineering/implement-spec/SKILL.md`, and `skills/engineering/implement-spec/agents/openai.yaml`. The first v1.3.1 assessment and its detailed decision table remain unchanged. The new fresh-context modification to the skill is also deferred (commit `7739eaed7f8f3915437a8def198a6d0d7206dbc7`, included in v1.3.2). The website prose rewrite is skipped, not evidence that its original deferred skill was adopted.

Revisit only with evidence of a separate multi-worktree task-graph need and adequate frontier/cycle/blocker diagnosis, write isolation, serial integration, dirty-worktree safety, skip-versus-pass accounting and authorization. Review progress never clears this queue by itself.

## Current release wording correction

GitHub releases and remote tag refs were checked on 2026-10-29. Published v1.0.0 and v1.1.0 exist; the obsolete v1.2.0 tag/release/assets do not. Root README now states that fact rather than a planned v1.0.0 or retained v1.2.0 recovery draft. ADR 0029 preserves the original retention plan as historical and records that it was superseded. Plugin maintenance instructions use the current ATM lock/archive distribution path, not the retired OMH installer. This does not change remote releases, existing installed identities or recovery backups.

## Per-path classification

| Upstream path | Change | Decision | Rationale / local application |
| --- | --- | --- | --- |
| `.agents/adr/0002-ship-as-a-claude-code-plugin.md` | modified | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `.agents/install-block.md` | modified | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `.claude-plugin/plugin.json` | modified | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `.github/ISSUE_TEMPLATE/bug.yml` | added | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `.github/ISSUE_TEMPLATE/config.yml` | added | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `.github/ISSUE_TEMPLATE/idea.yml` | added | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `.github/workflows/needs-info.yml` | added | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `.github/workflows/triage-label.yml` | added | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `.out-of-scope/frozen-misc-skills.md` | added | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `.out-of-scope/harness-name-collisions.md` | added | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `.out-of-scope/lazy-load-writing-for-agents.md` | added | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `.out-of-scope/mainstream-issue-trackers-only.md` | modified | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `.out-of-scope/native-question-tool.md` | added | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `.out-of-scope/new-skills.md` | added | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `.out-of-scope/subagent-recursion.md` | added | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `CHANGELOG.md` | modified | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `CLAUDE.md` | modified | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `CONTRIBUTING.md` | added | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `README.md` | modified | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `SCOPE.md` | added | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `docs/agents/triage-labels.md` | added | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/ask-matt.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/code-review.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/codebase-design.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/diagnosing-bugs.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/domain-modeling.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/grill-with-docs.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/implement-spec.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/implement.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/improve-codebase-architecture.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/pr.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/prototype.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/research.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/resolving-merge-conflicts.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/retro.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/setup-matt-pocock-skills.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/tdd.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/to-spec.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/to-tickets.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/triage.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/wayfinder.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/engineering/wizard.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/productivity/grill-me.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/productivity/grilling.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/productivity/handoff.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/productivity/teach.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/productivity/to-questionnaire.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/productivity/wait-what.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `docs/productivity/writing-for-agents.md` | modified | skip | Upstream explanatory/site documentation; no local counterpart imported. Behavioral changes selected separately in canonical owners. |
| `package.json` | modified | skip | Upstream repository governance, packaging or release/site metadata; OMH keeps its own owners and versioning. |
| `skills/engineering/ask-matt/SKILL.md` | modified | adopt | Read actual skill before claims or skip recommendations; reading does not invoke it. |
| `skills/engineering/code-review/SKILL.md` | modified | adapt | Find applicable standards and collect real reports; retain read-only/full-worktree coverage. Fresh-context policy belongs to agents/global-instructions.md, not forced two-agent foreground execution. |
| `skills/engineering/codebase-design/DESIGN-IT-TWICE.md` | modified | adapt | Fresh-context intent applied once in agents/global-instructions.md; preserve proportional direct comparison and existing bounded briefs, no mandatory 3+ agents. |
| `skills/engineering/diagnosing-bugs/SKILL.md` | modified | adopt | Prove authorized forced-red mutation actually changed the original fixture. |
| `skills/engineering/implement-spec/SKILL.md` | modified | defer | Still outside selected catalog; fresh-context addition does not resolve task-graph, integration and permission gaps. Carry prior three deferred paths forward. |
| `skills/engineering/implement/SKILL.md` | modified | adapt | Resolve ticket/title and ambiguity. Harness-aware method loading already covers Skill-tool change; preserve missing-method stop and exact staging. |
| `skills/engineering/improve-codebase-architecture/SKILL.md` | modified | adapt | Fresh-context intent applied through existing global delegation owner; exploration remains optional and read-only. |
| `skills/engineering/research/SKILL.md` | modified | adapt | Fresh-context intent applied through existing global delegation owner; no mandatory background agent or artifact. |
| `skills/engineering/setup-matt-pocock-skills/SKILL.md` | modified | skip | Unselected/retired workflow or resource; no catalog expansion or tracker/environment setup authorized. |
| `skills/engineering/setup-matt-pocock-skills/issue-tracker-github.md` | modified | skip | Unselected/retired workflow or resource; no catalog expansion or tracker/environment setup authorized. |
| `skills/engineering/setup-matt-pocock-skills/issue-tracker-gitlab.md` | modified | skip | Unselected/retired workflow or resource; no catalog expansion or tracker/environment setup authorized. |
| `skills/engineering/setup-matt-pocock-skills/triage-labels.md` | modified | skip | Unselected/retired workflow or resource; no catalog expansion or tracker/environment setup authorized. |
| `skills/engineering/tdd/SKILL.md` | modified | adapt | State each proposed seam coverage and limits; retain confirmed boundaries, no routine reapproval. |
| `skills/engineering/to-tickets/SKILL.md` | modified | skip | Unselected/retired workflow or resource; no catalog expansion or tracker/environment setup authorized. |
| `skills/engineering/wayfinder/SKILL.md` | modified | skip | Unselected/retired workflow or resource; no catalog expansion or tracker/environment setup authorized. |
| `skills/engineering/wizard/template.sh` | modified | skip | Unselected/retired workflow or resource; no catalog expansion or tracker/environment setup authorized. |
| `skills/in-progress/chief-of-staff/SKILL.md` | added | skip | Unselected in-progress wiki/scheduling workflow would duplicate owners and expand scope. |
| `skills/in-progress/chief-of-staff/agents/openai.yaml` | added | skip | Unselected in-progress wiki/scheduling workflow would duplicate owners and expand scope. |
| `skills/in-progress/claude-handoff/SKILL.md` | modified | skip | Unselected/retired workflow or resource; no catalog expansion or tracker/environment setup authorized. |
| `skills/productivity/grilling/SKILL.md` | modified | adapt | Yes accepts the stated recommendation without expanding permission; fresh-context handled by global owner. |
| `skills/productivity/handoff/SKILL.md` | modified | adapt | Resolve OS temp default, preserve explicit destination priority and surface invalid temp path. |
| `skills/productivity/teach/SKILL.md` | modified | adapt | Separate invocation workspace from skill resources; rotate answer positions without exact-length rule or new glossary owner. |

## Validation

Checks below run in the isolated Linux cloud checkout, not on Home. Required Python dependencies were already available (PyYAML 6.0.3, jsonschema 4.26.0).

- `python -m unittest discover -s tests -p 'test_*.py'`: 27 passed.
- `python -m unittest discover -s plugins/maintenance/tests -p 'test_*.py'`: 29 passed.
- `python -m unittest discover -s plugins/workflow/tests -p 'test_*.py'`: 95 passed.
- `python -m compileall -q scripts tests plugins/maintenance plugins/workflow`: passed.
- `python scripts/validate_plugin.py plugins/<package>`: maintenance, workflow and mattpocock-skills all passed.
- A one-off source inventory compared all 20 Matt frontmatter records and native `agents/openai.yaml` bytes against the starting commit: unchanged. It compared the 72 decision rows against `git diff --name-only v1.3.1 v1.3.2`: exact unique coverage and 2/9/60/1 counts. It confirmed implement-spec and chief-of-staff remain outside the catalog. These are metadata/coverage checks, not proof of model behavior.
- Independent read-only review covered the complete source diff and untracked review record. No permission, invocation, staging or selected-upstream semantic regression was found. Two stale-document consistency findings were corrected: ADR 0012 now marks old installer/Watcher details as superseded, and the root README distinguishes historical entries from current upstream records. Final rereview confirmed both fixes, the generated identity-only diff and cached diff hygiene, with no remaining actionable finding. The reviewer independently ran the generation check. The reviewer ran separately but inherited parent context; this was not fresh/blind-context evaluation.
- After all packaged source edits and owning tests, `python scripts/update_plugin_generations.py --release-version 1.1.0` ran once. `python scripts/check_plugin_generations.py` passed. Matt generation is `b47830ab88423643`; bundle identity is `sha256:cee524d0fc349d3a27e629b91315df102f6e79c2b9cb7fcad3f58cb9b78fa443`. Maintenance/workflow package generations are unchanged. This is a local content generation, not a new release or replacement of published 1.1.0 assets.
- After generation, the 27 root tests and all three plugin validators passed again. `git diff --check` passed.
- **Blocked:** pinned ATM exporter acceptance (`tooling/atm-revision.txt`: `2ddd638bc0336aaf7ce12a2fa86292eadf355d7c`). This executor has no Rust `cargo`/`rustc` or verified pinned ATM binary; no substitute exporter was used. `scripts/check_content_export.py` was not run. Run the pinned exporter build and temporary-Home import/projection check before publication.
- **Not run:** macOS/Windows and Python-version CI matrix, native client model invocation, live Home installation. No remote branch/PR was created to trigger CI. Linux unit passes do not imply those results.

### Semantic counterexample review

This is source-level reasoning against the final instructions, not a model-behavior eval or execution of the described scenarios:

| Counterexample | Required outcome / owner |
| --- | --- |
| Router summary is stale; selected skill is explicit-only | Read actual SKILL, report missing resource if unavailable; do not silently invoke it. |
| Mutation command returned success but fixture is unchanged | Compare pristine/current data; do not credit the forced red as mutation evidence. Editing still needs authorization. |
| Review branch diff is empty but staged, unstaged or untracked task changes exist | Include every in-scope layer, without altering the user's staging state. |
| A reviewer was launched but has no completed report | Report incomplete coverage; do not invent a passed axis. |
| Tracker is missing, or ticket `#12` names more than one repository | No setup or external write; resolve ambiguity or report blocked ticket-dependent work. |
| Required tdd/code-review method is unavailable | Preserve existing dependency stop; do not substitute guessed method content. |
| Existing stage contains unrelated user content | Preserve it; exact-stage only task changes or report inability to isolate the commit. |
| TDD test uses an already agreed seam | Explain catches/misses as useful; no extra approval solely for routine placement. |
| Yes answers one recommended design choice | Accept that stated choice only; no inferred publication or permission expansion. |
| Explicit handoff directory differs from TMPDIR/TEMP | User destination wins; default temp resolution never silently writes into the workspace. |
| Teaching workspace contains its own glossary and skill formats live elsewhere | Write into invocation workspace, read formats from skill directory, retain one glossary owner and flexible answer lengths. |
| Harness cannot provide a fresh subagent context | Disclose lack of isolation; do not invent native support or make delegation mandatory. |

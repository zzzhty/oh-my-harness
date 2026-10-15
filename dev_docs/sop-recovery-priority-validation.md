# SOP recovery priority validation — 2026-10-15

Initial scope: local source maintenance on Home, based on main
`8b7b1e050f5f0701a557d28b099345d3e79f2a21`, branch
`fix/sop-recovery-priority`. No installed skills, user configuration or native
Goal runtime are execution targets. Publication was outside the initial
authorization. On 2026-10-15 the user subsequently authorized committing this
change, merging it into main and normal push, including the normal PR/CI route
when branch protection requires it. Installation remains outside scope.

## Evidence and frozen oracle

The baseline SOP Execute step 4 stops at the first failed required validation,
while Completion and the template permit step-local failure handling. This can
prevent an already declared and authorized repair from running. The Goal skill
already has adaptive recovery and phase gates; only its dependent-step wording
needs clarification.

The following oracle was fixed before source edits. Validation remains the same
after a recovery; a passing structural checker never grants action permissions.

| Case | Input / situation | Required outcome |
| --- | --- | --- |
| S1 Shared recovery | Required validation fails; the SOP declares an authorized shared diagnosis/repair path. | Pause dependent steps, apply that path, repeat the original validation, and resume dependencies only after it passes. |
| S2 Step-local recovery | A step declares one retry after diagnosis confirms a transient lock has cleared. | Use that bounded step-local path and unchanged revalidation; do not invent more attempts or invoke an unrelated shared repair. |
| S3 Exhaustion | The declared retry or repair limit is exhausted and validation still fails. | Stop the affected operation, report evidence and the needed input; do not borrow Goal's failure count. |
| S4 Permission gap | The apparent repair needs an out-of-scope write, external action or denied access. | Stop the affected action and report the missing authority; another tool or backend is not a workaround. |
| S5 Report-only | The SOP is report-only, and a proposed repair would write. | Keep recovery non-mutating; perform only declared authorized read-only diagnosis/retry, otherwise stop and report. |
| S6 User stop / safety | The user explicitly stops, or an explicit termination/safety condition occurs while recovery is available. | Honor the stop immediately; do not run that recovery. |
| S7 Terminating SOP | A Ready SOP explicitly stops on required validation failure and declares no recovery. | Stop and report; recovery and retries remain optional. |
| S8 Ready / structure | A SOP is Draft or lacks an existing required core section/step field. | Reject execution by default; do not add a new required recovery section, counter or schema. |
| G1 Authorized Goal repair | A required gate fails within the current milestone and an in-scope repair is authorized. | Pause dependent steps, continue current-milestone diagnosis/repair, and keep validation/review/advancement gates intact. |
| G2 Native stop / scope | The native runtime stops, an authorization boundary is reached, or a Sequence child remains incomplete. | Preserve the existing native hard stop and scope; do not reset counting, bypass access, advance a milestone or skip the child. |

## Candidate and review plan

Compare the no-change baseline with one minimal candidate: co-locate recovery
priority and its terminal boundaries in SOP Execute; align the optional template
guidance; clarify one Goal paragraph. Keep the immediate-stop SOP fixture and
existing checker behavior. Add a complete shared/step-local recovery fixture
and structural regression cases without exact-sentence instruction assertions.

Independent evaluation must cover both Standards and Spec, plus a separate
permission/safety counterexample pass. Report this semantic review separately
from structural checker tests. No live agent enactment or native Goal counting
is claimed by either static checks or document review.

## Validation results

- Baseline Workflow suite on unmodified main: 95 tests passed, no skips or
  existing failing tests observed. This structural baseline does not negate the
  source-level recovery contradiction above.
- Final candidate owning Workflow suite, rerun after the fixture correction:
  96 tests passed, no skips. The added test
  checks both complete SOP fixtures against Ready/Draft and existing required
  Allowed Actions, Validation and step output fields. It does not assert exact
  skill sentences or simulate an agent executing recovery.
- Readiness checks passed for the preserved terminating `ready_sop.md` and the
  new shared/step-local `ready_sop_with_recovery.md` fixture.
- SOP and Goal relative-link checks, Workflow plugin validation, and
  `git diff --check` passed.
- Runner: existing Python 3.13.15 tooling venv; test HOME/USERPROFILE and client
  environment overrides were isolated. No system component was installed.

Final integration results on Home Linux, after identity generation:

| Suite | Collected | Passed | Skipped | Failed |
| --- | ---: | ---: | ---: | ---: |
| Root `tests` | 462 | 453 | 9 | 0 |
| Watcher | 87 | 84 | 3 | 0 |
| Workflow (owning run before generation) | 96 | 96 | 0 | 0 |

The 12 skips are platform-dependent Windows batch/PowerShell, extended-path,
encoding and native case-insensitive-filesystem cases. They were not exercised
on this Linux host. No existing failing tests were observed in the baseline
Workflow or final suites. All three source-plugin validators, four README
JSON syntax checks, Python compilation for the CI source directories,
distribution identity validation and final diff hygiene passed. Compilation
used a temporary pycache prefix outside the repository.

Supporting logs are outside the repository at
`../validation/sop-recovery/` relative to its root. In particular,
`baseline-workflow-tests.log`, `postfix-owning-results.json`,
`postfix-workflow-owning.log`, `integration-results.json`,
`integration-root-tests.log`, `integration-watcher-tests.log`,
`distribution-generation.log` and `final-static-checks.log` retain the actual
results. Earlier candidate logs precede the fixture correction; the `postfix-`
logs describe the final packaged source.

## Independent semantic review

The first read-only Standards/Spec review covered all modified and untracked
source files, the baseline and S1–S8/G1–G2. Its separate permission/safety pass
found no additional boundary regression. It identified one P2 Spec issue in the
new fixture: the generic terminal clause could override Step 2's declared lock
recovery. The fixture now limits direct termination to failures covered by
neither declared recovery path. The same independent reviewer re-read the net
diff and all S1–S8/G1–G2 cases: no remaining Standards or Spec findings. The
separate permission/safety counterexamples still reject out-of-scope writes,
unauthorized external actions, denied-access workarounds, report-only writes,
recovery after a user/runtime stop, and skipping an incomplete Sequence child.

This finding was not caught by passing readiness/structure tests. Semantic review
does not establish live agent adherence or native Goal runtime behavior.

## Distribution and final scope

After the final packaged-source fix, fresh owning tests and semantic re-review,
`scripts/update_plugin_generations.py` ran exactly once for this change. The
read-only identity checker and an independent generated-only review both
confirmed the resulting single current identity:

- Workflow: `1.0.0+codex.45dfd6fc0590d8fe`
- Workflow content SHA-256:
  `45dfd6fc0590d8fe6a5038900ebe5c23a17cc715c90daaf07c4c0c6e1fcfa3cb`
- Bundle:
  `sha256:253c37ad00098629da98f089ba65da47dcdc1d39e1d109a76e42f0b8ba45da64`

Only Workflow's manifest and the distribution identity ledger changed as
generated files. Marketplace still points to `./plugins/workflow` and has no
separate version field. Matt, Watcher and release `VERSION` remain unchanged.

The source diff consists of SOP Execute/Completion guidance, its template,
one Goal paragraph, the Workflow README, changelog, the structural regression
test, one new recovery fixture and this local validation record. The previous
terminal SOP fixture, readiness checker/schema, Goal native counting,
references/templates, advancement and Sequence rules remain unchanged.

At the local-verification checkpoint, changes were uncommitted and unstaged on
`fix/sop-recovery-priority` at the recorded main base, with no publication or
installation performed. The user's later publication authorization is recorded
above; the corresponding Git history, PR and CI report capture that outcome.
No installation or real-user configuration change is part of this work. There
is no remaining local implementation blocker.
This is source/structure validation and independent semantic review, not a
live agent enactment, native Goal runtime test or macOS/Windows run. No claim
is made about native retry counting or runtime adherence.

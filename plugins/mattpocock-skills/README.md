# Matt Pocock Skills — OMH edition

A locally maintained selection of 20 engineering skills. The plugin keeps the `mattpocock-skills` namespace and each retained skill's invocation policy. Its source is owned by oh-my-harness; the plugin is not an unchanged upstream subscription.

## Source and attribution

Derived from [mattpocock/skills](https://github.com/mattpocock/skills), release `v1.2.3`, commit `6acc160e4e0cd062dbbbd7a1b26ae92855edf07e`. Matt Pocock's original work remains attributed under the included [MIT license](LICENSE). Local revisions are maintained in this repository.

[ADR 0012](../../docs/adr/0012-maintain-a-local-mattpocock-selection.md) records the ownership and distribution migration. Local versioning follows the repository `VERSION` plus the package content generation; the upstream release above records provenance, not the current package version.

## Entry points

Use $mattpocock-skills:ask-matt to help me choose the right skill for this task.

| Use | Skills |
| --- | --- |
| Discuss and design | grilling, grill-me, grill-with-docs, domain-modeling, codebase-design, improve-codebase-architecture |
| Implement and verify | implement, code-review, tdd, diagnosing-bugs, resolving-merge-conflicts |
| Work with issues and context | triage, to-spec, handoff, setup-matt-pocock-skills |
| Investigate, learn and maintain | research, prototype, teach, writing-for-agents |

Core/specialized labels in the selection proposal are maintenance priorities, not additional activation modes. Skills and their referenced resources live under `skills/`; `agents/openai.yaml` retains native Codex metadata, and existing frontmatter flags support the other harnesses that consume them.

`grill-with-docs` remains an explicit user entrypoint. A workflow with its own planning trigger, such as long-running-goal preflight, directly composes `grilling` and `domain-modeling`; it does not implicitly invoke the wrapper or obtain implementation authority from planning. Both methods must be available, and document creation follows domain-modeling's existing ownership and value rules.

The local selection retires to-questionnaire, to-tickets, wait-what, wayfinder and wizard. They are no longer callable in this distribution; their source remains in Git history and upstream. Existing user artifacts and historical logs are preserved.

## Maintenance

Edit the owning skill and its references directly. The local edition is the maintained source; upstream updates follow the comparison workflow below.

Follow the root [source validation and lifecycle instructions](../../README.md). Complete source edits and owning tests before generating the current plugin identity once. Install through the normal oh-my-harness distribution rather than copying skills into another discovery root.

## Upstream updates

1. Read the [upstream review record](../../dev_docs/mattpocock-upstream-review.md). Resolve the last fully reviewed revision and the target upstream release/ref to exact commits in a separate inspection checkout. Compare that upstream range, then compare relevant changes with the current local skills, references and metadata so local adaptations remain visible.
2. Classify changes as **adopt**, **adapt**, **skip** or **defer**, with the affected paths/commits and a short reason. Review additions, removals and previously unresolved changes too. New upstream skills and changes to retired skills are candidates for selection; they do not automatically enter the catalog.
3. When a source update is requested, apply the selected changes to their local owners within the existing authorization. Preserve local behavior and invocation policies unless their revision is part of the requested update. A comparison-only request produces findings without changing source skills. Do not replace the complete tree, replay an upstream release wholesale or introduce a patch overlay.
4. Record the compared commits, local starting revision, decisions, actual application and validation results. Advance the last fully reviewed revision only when the entire upstream range has been classified. Carry all unresolved items forward with their original paths/commits, including deferred changes and selected changes not yet applied or not passing validation. This records review coverage, not adoption of the whole release. A partial or unavailable comparison leaves that revision unchanged.
5. Validate applied changes and generate their distribution identity through the root maintenance workflow. Publication and installation use the ordinary local-edition lifecycle; `omh update` consumes this repository's selected result and does not pull skills directly from Matt's repository.

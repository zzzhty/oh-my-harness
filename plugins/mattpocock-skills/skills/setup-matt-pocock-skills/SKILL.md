---
name: setup-matt-pocock-skills
description: Configure missing repository tracker, triage-label and domain-document conventions for the selected engineering workflows.
disable-model-invocation: true
---

# Configure Repository Conventions

Configure the tracker, triage vocabulary and domain-document locations needed by the selected engineering workflows. Reuse existing conventions; setup is not a prerequisite for an ordinary review or implementation task whose inputs are already available.

## Inspect and resolve missing choices

Read the active repository instructions, remotes, existing `docs/agents/`, domain glossary/map and ADR layout. Identify which remaining workflows need configuration.

- Use the existing issue tracker when specified. Otherwise propose the backend indicated by the remote, or local Markdown when appropriate, and resolve the user's choice.
- If triage is used, reuse existing label mappings; only ask for genuinely undecided mappings. Default roles are in [triage-labels.md](triage-labels.md).
- Preserve existing domain-document locations. Use a single context by default; multiple contexts need an actual domain/layout reason, not just a package count.

Reuse choices already provided in the request or repository. Present any consequential unresolved choice before writing dependent configuration; do not add another blanket confirmation after those choices and the setup write scope are already authorized.

## Write the needed configuration

Update existing files in place, preserving user-owned sections. Use the active repository instruction file (`AGENTS.md` or the harness's native equivalent) for concise pointers to the new configuration; avoid creating a second competing instruction owner.

Use only the templates needed for the chosen backend:

- [issue-tracker-github.md](issue-tracker-github.md)
- [issue-tracker-gitlab.md](issue-tracker-gitlab.md)
- [issue-tracker-local.md](issue-tracker-local.md)
- [triage-labels.md](triage-labels.md), when triage needs label mappings
- [domain.md](domain.md), when domain-document conventions need recording

Write tracker configuration to `docs/agents/issue-tracker.md`, label mappings to `docs/agents/triage-labels.md`, and domain conventions to `docs/agents/domain.md`, unless this repository already owns them elsewhere. For another tracker, record the user's actual workflow. Preserve any existing PR/MR triage flag; a new external-PR discovery flag defaults off.

A configuration write does not itself create external labels, issues or comments. Perform such actions only when included in the user's authorization. Verify the written pointers and selected backend, then report what changed and which workflows consume it.

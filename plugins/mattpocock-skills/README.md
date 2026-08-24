# Matt Pocock Skills

Skill-only local Codex package of Matt Pocock's published skills.

Upstream: https://github.com/mattpocock/skills

Packaged from: `v1.2.3` (`6acc160e4e0cd062dbbbd7a1b26ae92855edf07e`)

## Skills

- `ask-matt`
- `code-review`
- `codebase-design`
- `diagnosing-bugs`
- `domain-modeling`
- `grill-me`
- `grill-with-docs`
- `grilling`
- `handoff`
- `implement`
- `improve-codebase-architecture`
- `prototype`
- `research`
- `resolving-merge-conflicts`
- `setup-matt-pocock-skills`
- `tdd`
- `teach`
- `to-questionnaire`
- `to-spec`
- `to-tickets`
- `triage`
- `wait-what`
- `wayfinder`
- `wizard`
- `writing-for-agents`

## Upstream Authority

Every directory under `skills/` is copied unchanged from the paths published in
the selected upstream `.claude-plugin/plugin.json`. This includes upstream's
native `agents/openai.yaml` Codex metadata and its dual-harness SKILL.md
frontmatter. The local updater does not generate Codex metadata, rewrite skill
invocations, omit published skills, or patch upstream behavior.

The local-only surfaces are the `.codex-plugin` wrapper, Watcher attribution
metadata, the updater-owned upstream content lock, version/distribution identity, this
README, and the scoped `AGENTS.md`. Never edit `skills/` or manually rebaseline
the lock; validation fails on drift before an upstream update can replace it.

## Updating From Upstream

From the `oh-my-harness` repository root, run:

```bash
python3 scripts/bootstrap_tooling_env.py
"${OH_MY_HARNESS_HOME:-$HOME/.oh-my-harness}/venv/bin/python" scripts/update_mattpocock_skills.py
```

The updater selects an upstream release, copies its published skills unchanged,
regenerates local wrapper metadata, regenerates the distribution identity, and validates the
upstream-native Codex invocation contract.

This plugin is the source of truth for these third-party skills in this Codex
setup. Do not maintain separate copies under `$CODEX_HOME/skills`.

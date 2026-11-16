---
name: skill-guide
description: Choose a skill only when the user explicitly invokes skill-guide or asks which skill fits. Prefer no skill when ordinary ability is enough. Navigation only; it does not run the chosen skill.
disable-model-invocation: true
---

# Skill Guide

Recommend a skill only when its instructions impose a constraint this task needs. Ordinary model ability needs no skill. Say so when that is the case.

Take candidates from the catalog the active harness has already exposed. Names and descriptions there are the available inventory. If the harness exposes no catalog, use only an authoritative installed-skill inventory it already provides, and only entries whose instructions you can read. Do not search the web, install skills, or scan unrelated files. A remembered name is not availability. Do not assume every oh-my-harness plugin is installed.

Prefer oh-my-harness skills from `maintenance`, `workflow`, and `mattpocock-skills` when the catalog or the skill's own instructions identify that origin. Consider an external skill only when it is already in that inventory and its real instructions can be read; otherwise omit it. If no verified candidate exists, say so.

Use exposed names and descriptions to choose the few candidates that might add a needed constraint. Read those skills' instructions before explaining them, recommending them, or recommending that one be skipped. Do not read the rest. A description is orientation, not the source of truth. When the harness provides `SKILL.md`, that file is the source of truth. Reading does not invoke the skill. If you cannot read a candidate, do not describe or recommend it.

Recommend the smallest selection that supplies the missing constraint, normally one skill. Name the constraint. Combine skills only when no single skill supplies every constraint the task needs. These are options, not a sequence.

Respect each skill's invocation policy. Recommend an explicit-only skill for the user to invoke. Recommending it does not activate it or grant its execution authority. Stop after the recommendation: do not execute a skill, chain skills, delegate, install, or take a remote action.

Adapted navigation boundaries are attributed in [NOTICE.md](NOTICE.md).

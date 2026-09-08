---
name: improve-codebase-architecture
description: Find architectural friction and propose focused module-design improvements, with an optional visual comparison.
disable-model-invocation: true
---

# Improve Codebase Architecture

Find architectural friction and propose changes that concentrate useful behavior behind clearer interfaces. `/codebase-design` owns the vocabulary and design principles; use the project's domain terms and relevant ADRs.

## Investigate

Follow the user's named module or problem. Otherwise use recent changes and repeated maintenance pain to select a bounded area. Trace callers, implementation and tests: where does one change require scattered edits, where do pass-through layers add little, and where can existing tests not exercise the real failure pattern?

Use the deletion test and dependency guidance from `/codebase-design`. Ground every candidate in actual code and a concrete benefit. An ADR conflict is worth surfacing when observed friction justifies revisiting the decision, not merely because another design is possible.

Independent read-only exploration can help for separable areas when delegation is authorized; it is not mandatory for a small investigation.

## Present the decision

For each useful candidate, show the affected paths, observed problem, proposed direction, expected benefit and trade-offs. Rank the candidates and recommend which deserves attention. Use a short Markdown report by default; use diagrams when relationships need them.

If the user requests a visual report or the comparison benefits from one, consult [HTML-REPORT.md](HTML-REPORT.md) as a scaffold, adapt it to the scope, and save the result to the requested destination or OS temporary directory. HTML and multiple alternate designs are not completion gates for every review.

A review ends with findings and recommendations. If further design or implementation is already in scope, continue on the agreed candidate; use `/grilling` only for consequential open decisions and `/domain-modeling` when new durable knowledge needs recording. For genuinely competing interfaces, use the design-it-twice reference in `/codebase-design`.

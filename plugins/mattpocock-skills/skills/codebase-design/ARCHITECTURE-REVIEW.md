# Architecture review

Use this reference only when the user explicitly asks to find architectural friction or review the architecture of existing code. Loading `codebase-design` for vocabulary, seam placement, or testability does not start this review and does not produce an HTML report.

This review is adapted from the former `improve-codebase-architecture` skill in this plugin. That skill's text remains under the plugin [MIT license](LICENSE).

Start from real friction: the module or problem the user named, or otherwise a bounded area shown by recent changes and repeated maintenance pain. Trace callers, implementation, and tests for scattered edits, pass-through layers, and tests that cannot exercise the real failure. Apply the deletion test and seam principles in [SKILL.md](SKILL.md). Ground every candidate in the code and a concrete benefit. Surface an ADR conflict only when that friction justifies revisiting the decision.

For each candidate worth proposing, name the affected paths, the observed problem, the direction, the benefit, and the trade-off. Rank them and recommend one. A short Markdown report is enough. Add a diagram when a relationship needs it.

Consult [HTML-REPORT.md](HTML-REPORT.md) only when the user asks for a visual report or the comparison needs one. Save it to the requested destination, or to the operating system's temporary directory when none is specified. An HTML report is not a completion gate.

The review ends as a proposal. It does not start implementation.

---
name: reframe
description: Reframe a hard-to-name problem from the supplied description and relevant evidence, then return a rewritten brief. Use only when explicitly selected.
disable-model-invocation: true
---

# Reframe

Return a clearer description of the problem, not a solution or a specification. Start from the user's own words and relevant files, code, or observations in scope. Keep confirmed goals and constraints intact.

If the same description fits materially different problems, name the plausible interpretations and one observable sign that separates them. State which fits the available evidence best, or leave the choice open when the evidence cannot distinguish them.

Teach only the terms that would change what the user asks for or builds. For each, explain in plain language what it names here and how it changes the next question. Prefer the repository's existing vocabulary when it fits. Borrow from another field only when the analogy clarifies a decision; say where it breaks. Open primary sources before citing them and verify they use the term in the relevant sense. If that check is unavailable, omit the citation and label any consequential inference or uncertainty.

Return one copyable brief and keep unresolved questions separate from established facts. Reading and rewriting do not authorize editing files, glossaries, ADRs, or trackers, running experiments, executing the brief, or invoking another skill. Stop after the brief.

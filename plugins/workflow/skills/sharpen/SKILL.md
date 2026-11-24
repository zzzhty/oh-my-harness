---
name: sharpen
description: Deepen a single, already understood task into a copyable prompt with better evidence and verification, without doing the task. Use only when explicitly selected.
disable-model-invocation: true
---

# Sharpen

Make the task deeper, not bigger. Preserve its goal, deliverable, constraints, non-goals, and explicit permission limits. If the goal itself remains ambiguous, expose the ambiguity rather than inventing a decision.

Before rewriting, identify:

- The consequential check or step a skilled practitioner would add within this scope.
- The firsthand material to inspect instead of relying on a summary.
- The concrete method or tool that fits the job.
- An observable result or independent check that can establish success.

Return one copyable prompt. Where a small experiment can decide between in-scope options, make it a conditional next step for the executing agent, only if already authorized, and ask for a recommendation based on the observed result. Leave product, preference, and permission decisions with the user; don't decide them by proxy.

Do not execute the rewritten task, run tests or prototypes, change files, publish or delegate. Don't invoke another skill. Stop after the rewritten prompt.

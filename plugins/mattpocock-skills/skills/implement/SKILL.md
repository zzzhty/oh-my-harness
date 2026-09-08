---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
disable-model-invocation: true
---

Implement the user's spec or tickets within the agreed scope. Reuse confirmed requirements and test boundaries; resolve only missing decisions that block the implementation.

Record the starting commit and relevant pre-existing work so this task's changes remain identifiable. Use `/tdd` for behaviors that warrant persistent tests and follow repository verification requirements. Run focused checks while iterating and broader required gates at completion.

Before finishing, use `/code-review` with the task/spec, starting commit and changed-file inventory. Explicitly include this task's committed, staged, unstaged and untracked changes; a comparison ending at HEAD alone cannot review uncommitted implementation.

Address actionable findings and report remaining limits. Commit when the user's existing authorization includes it. Stage only this task's changes and check the entire pending commit, including content staged before the task. If unrelated content cannot be excluded without altering the user's work or staging state, preserve that state and report the blocker.

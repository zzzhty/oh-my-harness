---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
disable-model-invocation: true
---

Implement the agreed spec or tickets. Resolve only a missing decision that blocks the work.

When given a ticket reference, resolve it through the existing authorized tracker and state its title before implementing. Ask when the reference is ambiguous. If it cannot be read, report the missing access and stop ticket-dependent work. This does not authorize tracker setup or external writes.

Record the starting commit and relevant pre-existing work so this task's changes stay identifiable.

Before finishing, load `code-review` and include this task's committed, staged, unstaged, and untracked changes. A comparison that ends at HEAD does not review uncommitted work.

Stage only this task's changes. Check the whole pending commit, including content staged before the task. If unrelated content cannot be excluded without altering the user's work or staging state, preserve that state and report the blocker.

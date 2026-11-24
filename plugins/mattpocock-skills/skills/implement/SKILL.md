---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
disable-model-invocation: true
---

Implement the agreed spec or tickets. Resolve only a missing decision that blocks the work.

When given a ticket reference, resolve it through the existing authorized tracker and state its title before implementing. Ask when the reference is ambiguous. If it cannot be read, report the missing access and stop ticket-dependent work. This does not authorize tracker setup or external writes.

Record the starting commit and relevant pre-existing work so this task's changes stay identifiable. Load `tdd` when the user or agreed spec explicitly requires test-first or red–green–refactor. Otherwise, verify changed behavior without automatically loading `tdd`.

Before finishing, load `code-review` and include this task's committed, staged, unstaged, and untracked changes. A comparison that ends at HEAD does not review uncommitted work. Fix actionable findings within scope, verify the fixes, and report unresolved findings or verification limits.

Leave this task's changes unstaged by default. Inspect staged and unstaged diffs separately, including when both touch the same file; preserve the user's work and staging state. If staging or committing is authorized, select only verified task changes, never whole files containing mixed changes, and inspect the entire pending commit. If task changes cannot be isolated or unrelated staged work cannot be kept out without disturbing the user's index, leave the index intact and report the blocker.

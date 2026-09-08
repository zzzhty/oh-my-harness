---
name: resolving-merge-conflicts
description: "Use when you need to resolve an in-progress git merge/rebase conflict."
---

Resolve an in-progress merge or rebase by understanding each side's intent from its history, linked task and surrounding code.

Inspect the operation state, unresolved paths and existing staged/unstaged work before editing. Resolve only conflicts within the requested operation. Preserve both intended behaviors when compatible; if the correct result needs a missing product decision, keep the conflict state and report the specific choice rather than guessing or aborting the operation.

Run the affected behavior checks and required repository gates. Stage only resolved paths or hunks belonging to this operation; never sweep unrelated work into the index or commit. Check the full pending commit scope, including anything staged before this task, before continuing the merge/rebase. If unrelated staged content cannot be kept out without changing user work, report that blocker.

Continue the authorized operation when the resolution and required checks are complete. Report the resulting state and any remaining conflicts or verification limits.

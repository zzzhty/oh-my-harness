---
name: writing-for-agents
description: Author and structure agent guidance (skills, AGENTS.md, CLAUDE.md). Use skill-compressor for behavior-preserving reduction and prompt-strategy-loop for intentional behavioral redesign.
---

# Writing for Agents

This skill places agent guidance. Put the trigger in the description and the procedure in the body. Point to a reference when a branch is large; a small skill needs no extra file. Each meaning has one home. Another skill may point at that home and keep only its own task-specific steps. A frequently used entrypoint may stay thin when it composes other skills for a real user intent.

A short text is not automatically better. Check triggers, required actions, and stop conditions, not only length.

`maintenance:skill-compressor` owns behavior-preserving reduction. `workflow:prompt-strategy-loop` owns an intentional change to routing, permissions, safety, failure, or validation. Send the edit to that owner; do not restate its workflow here.

For invocation metadata, read [SKILL-MECHANICS.md](SKILL-MECHANICS.md). Preserve the existing invocation policy unless the requested change includes it.

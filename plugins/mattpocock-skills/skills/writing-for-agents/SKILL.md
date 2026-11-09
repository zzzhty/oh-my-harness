---
name: writing-for-agents
description: Author and structure agent guidance (skills, AGENTS.md, CLAUDE.md). Use skill-compressor for behavior-preserving reduction and prompt-strategy-loop for intentional behavioral redesign.
---

# Writing for Agents

Write guidance that changes a useful decision or action. Assume a capable agent: preserve non-obvious conventions, operational constraints and reasons; remove repetition and generic advice that the environment already supplies.

This skill owns guidance authoring and information placement. `maintenance:skill-compressor` owns behavior-preserving reduction; `workflow:prompt-strategy-loop` owns intentional behavior changes. Reuse shared writing principles, but do not chain their complete workflows for one edit.

## Triggers and information placement

A **context pointer** names a resource and the condition for reading it. Put distinct task triggers in the description; keep detailed steps in the body. When a required reference is repeatedly missed, clarify its trigger before copying its contents into every caller.

Keep the shared workflow and completion criteria in the entrypoint. Put substantial branch-specific examples or procedures behind links with explicit reading conditions. Small skills need no extra router or reference file. Co-locate a concept's rules and exceptions so readers do not have to reconstruct them from scattered sections.

Each meaning has one owner. Another skill can reference a shared method while preserving its own task-specific steps. A short, frequently used entrypoint can earn its place through user intent even when it mostly composes other skills.

For skill invocation and metadata, read [SKILL-MECHANICS.md](SKILL-MECHANICS.md). Preserve existing invocation policy unless the requested change includes it.

## Behavior and scope

State the intended action and a checkable completion condition. Keep mandatory steps for actual contracts or demonstrated failures; let the agent choose proportional methods for open-ended work. Preserve existing authorization, user work, privacy, failure handling and required verification boundaries. Reuse decisions and permission already established in the task.

Prefer concrete positive directions. Retain explicit prohibitions where they protect a real boundary. Use familiar terms consistently; do not invent vocabulary merely to compress text or override the repository's domain language.

The environment is a source of truth: point to commands, configuration and existing documents instead of copying facts that are cheap to inspect. Keep the rationale and gotchas that those sources do not explain.

## Validate a revision

Before a consequential rewrite, state the observed problem and representative success/regression scenarios. Compare the existing guidance with the smallest useful candidate. Check triggers, required actions and stop conditions as well as word count; shorter text alone does not prove better behavior.

When routing, authorization, safety, failure, or validation behavior intentionally changes, apply `workflow:prompt-strategy-loop` and its Core Rule on independent review and proportional evaluation. If that method or required evaluation is unavailable, mark the behavior change unverified. Distinguish static/semantic review from actually running an agent through the task, and report unresolved coverage.

Split or merge documents when it clarifies ownership or a real mode boundary. Do not build multiple candidates or new reference hierarchies without an actual trade-off to resolve.

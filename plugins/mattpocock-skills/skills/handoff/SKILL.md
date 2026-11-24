---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up.
argument-hint: "What will the next session be used for?"
disable-model-invocation: true
---

Write a handoff so another session, directory, harness, or person can continue. Use the user's requested destination. Otherwise create a unique file in a private temporary directory accessible only to the current user (under `$TMPDIR` or `/tmp` on Unix; under `%TEMP%` on Windows). Resolve the destination before writing and verify it is outside repositories and shared workspaces and has owner-only access using permissions or ACLs; report the absolute path, and do not write it into the repository. If privacy cannot be established there, report the problem rather than using a shared location or the workspace. A handoff does not require a formal goal contract.

Cite existing specs, plans, ADRs, issues, commits, and diffs instead of copying them. Keep a decision's reason when those artifacts do not. Redact secrets and unnecessary personal information; point to credential locations without copying credential values.

Create a handoff when the user asks or the work actually crosses a continuation boundary. A phase change, a prototype, or a token count does not by itself require one. Creating the handoff does not authorize sending it.

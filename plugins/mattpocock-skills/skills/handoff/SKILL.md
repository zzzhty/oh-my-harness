---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up.
argument-hint: "What will the next session be used for?"
disable-model-invocation: true
---

Write a handoff so another session, directory, harness, or person can continue. Use the user's requested destination. Otherwise use the operating system's temporary directory (`$TMPDIR`, otherwise `/tmp`, on Unix; `%TEMP%` on Windows), report the absolute path, and do not write it into the repository. If that directory is unavailable, report the path problem rather than writing into the workspace. A handoff does not require a formal goal contract.

Cite existing specs, plans, ADRs, issues, commits, and diffs instead of copying them. Keep a decision's reason when those artifacts do not. Redact secrets and unnecessary personal information; point to credential locations without copying credential values.

Create a handoff when the user asks or the work actually crosses a continuation boundary. A phase change, a prototype, or a token count does not by itself require one. Creating the handoff does not authorize sending it.

---
name: to-spec
description: Synthesize the current discussion and repository evidence into an implementable spec without restarting an interview; publish to a tracker only when separately authorized.
disable-model-invocation: true
---

Synthesize the current discussion and repository evidence into an implementable spec. Reuse confirmed requirements, domain terms, and decisions. Ask only about a gap that blocks the spec; do not restart an interview.

Inspect the relevant code when the current implementation is not yet understood. `/codebase-design` owns seam principles. State a proposed interface change separately from an agreed decision.

Include independently verifiable acceptance criteria for the requested outcome. Use one line per criterion:

- [ ] **Condition/action:** <setup and action> → **Observable result:** <expected behavior> → **Verification:** <how to check>

A request to draft does not publish to a tracker or create tracker configuration. Publish to a tracker only when separately authorized, using the existing destination and its conventions. An incomplete spec is not ready for unattended implementation.

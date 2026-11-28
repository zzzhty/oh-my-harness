---
name: repo-lessons
description: Distill actionable lessons from evidence in the current repository and enforce proven recurring mistakes when possible. Use only when the user explicitly invokes repo-lessons or explicitly asks to encode repeated historical mistakes into structure or to distill repository lessons. Ordinary bugfixes and reviews are not a trigger.
---

# Repository Lessons

Distill lessons that change what the next agent does. Where evidence supports a recurring mistake, enforce the lesson at the strongest level that works. Use only when the user explicitly invokes `repo-lessons` or explicitly asks to encode repeated historical mistakes into structure or to distill repository lessons. A normal bugfix, review, or documentation edit is not a trigger.

Work only in the current repository. Do not fan out across other repositories. Do not start subagents unless the user explicitly requests them.

## Find classes

Inspect the original evidence and check the current SOP, tests, and repository guidance first. Group incidents by the wrong assumption and the action that would prevent recurrence, not by run, date, or symptom.

Write a lesson only when the evidence shows a concrete mistake that could recur: name the situation, the mistaken assumption, and what to do next time. A single verified incident can support a lesson or proposal, not a new enforced rule. If a current SOP or check already teaches or enforces the action, point to it rather than restating it. When authorized to write, use the existing lesson or guidance owner; without one, return the proposed wording. Link original evidence where useful; do not copy the incident chronology or create an archive, log, or evidence ledger. Do not delete original evidence.

Before promoting a lesson to a new repo-wide rule or automatic check, verify it still applies and inspect at least two distinct historical commits firsthand. They must substantiate separate occurrences of the same mistake. Other evidence can help locate or understand those commits but does not replace them. If two commits do not substantiate a class, do not add a rule for it. If no lesson or rule qualifies, change nothing and report which sources you read and why.

## Encode at the highest level that works

For a lesson that passes the enforcement gate and is authorized for implementation, prefer, in this order:

1. **Architecture.** Give the state one owner and the task one supported path, so the wrong path fails to build or cannot be reached. Delete the old path an agent would copy.
2. **Types.** Make the bad state unrepresentable.
3. **A lint or check script.** Use this when architecture and types cannot reject the mistake. The error names the fix: the file, type, function, or command to use instead.
4. **A test.** Use this when the mistake is behavior a static check cannot see.
5. **Docs or agent instructions, last.** Use these only for a judgment call that code cannot decide, and include an example of the failure. Skipping a paragraph does not fail a check, so do not stop at docs when a higher level works.

A workaround comment is not a fix. When the lesson is structural, the structure is the whole fix.

## Rules a check must carry

- Each finding prints three labeled lines: `Violation`, `Fix`, and `Principle`. `Fix` names what to use instead. `Principle` explains why the rule exists; do not include the supporting commits in check output.
- Local runs and CI run the same command. Do not add a check that only one of them executes.
- Put violations that already exist, and files that are already over a length limit, into a ratchet baseline. The baseline may only shrink: remove an entry or lower a ceiling when the tree no longer needs it. Do not raise it to admit a new violation.
- Each rule has a test built from the real pre-fix code. Minimize that code only when the smaller sample still exhibits the same class. The test proves the check fails on that code and that the current tree passes.
- Keep a rule-to-enforcer table in the repository's agent instruction file. Each row names the rule and the command, type, or test that enforces it. Do not put its historical evidence, commit IDs, or commit links in `AGENTS.md`. Remove a row when that mistake can no longer occur.

One working shape is a single check command, a baseline of grandfathered findings, and that table. A repository may already have this shape, for example `scripts/check_architecture.py`, `scripts/architecture_baseline.json`, and the rule table in its agent instructions. Extend that shape when it exists. Those paths are an example of the output, not required names in every repository, and they are not a reason to add a second command beside an existing one.

## Report

For each class, report whether you reused existing guidance, distilled a lesson, or added enforcement. For enforcement, report the chosen level and why higher levels did not work. You may cite the two supporting commits in the one-time change report. They establish necessity during discovery; no persistent evidence record is required. When you change nothing, report the sources you read and why no class qualified.

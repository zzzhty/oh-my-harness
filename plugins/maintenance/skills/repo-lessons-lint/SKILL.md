---
name: repo-lessons-lint
description: In the current repository, turn mistake classes that already occurred at least twice into checks that make a repeat impossible. Use only when the user explicitly invokes repo-lessons-lint or explicitly asks to encode repeated historical mistakes into structure. Ordinary bugfixes and reviews are not a trigger.
---

# Repository Lessons Lint

Make a repeated mistake impossible in the repository you are in. Use only when the user explicitly invokes `repo-lessons-lint` or explicitly asks to encode repeated historical mistakes into structure. A normal bugfix, review, or documentation edit is not a trigger.

Work only in the current repository. Do not fan out across other repositories. Do not start subagents unless the user explicitly requests them.

## Find classes

Read the history that can show the same mistake twice: commits, reverts, review comments, architectural decision records, and comments that explain a workaround. Group them into classes. A class exists only after the same mistake has occurred at least twice.

If that history is too short to show a repeat, or no class repeats, change nothing. Report which sources you read and why no class qualified.

## Encode at the highest level that works

Prefer, in this order:

1. **Architecture.** Give the state one owner and the task one supported path, so the wrong path fails to build or cannot be reached. Delete the old path an agent would copy.
2. **Types.** Make the bad state unrepresentable.
3. **A lint or check script.** Use this when architecture and types cannot reject the mistake. The error names the fix: the file, type, function, or command to use instead.
4. **A test.** Use this when the mistake is behavior a static check cannot see.
5. **Docs or agent instructions, last.** Use these only for a judgment call that code cannot decide, and include an example of the failure. Skipping a paragraph does not fail a check, so do not stop at docs when a higher level works.

A workaround comment is not a fix. When the lesson is structural, the structure is the whole fix.

## Rules a check must carry

- Every rule cites at least two historical commits as evidence. If you cannot cite two commits, do not add the rule. Name that gap in the report.
- Each finding prints three labeled lines: `Violation`, `Fix`, and `Principle`. `Fix` names what to use instead. `Principle` includes the two commit ids and why the rule exists.
- Local runs and CI run the same command. Do not add a check that only one of them executes.
- Put violations that already exist, and files that are already over a length limit, into a ratchet baseline. The baseline may only shrink: remove an entry or lower a ceiling when the tree no longer needs it. Do not raise it to admit a new violation.
- Each rule has a test built from the real pre-fix code. Minimize that code only when the smaller sample still exhibits the same class. The test proves the check fails on that code and that the current tree passes.
- Keep a rule-to-enforcer table in the repository's agent instruction file. Each row names the rule and the command, type, or test that enforces it. Remove a row when that mistake can no longer occur.

One working shape is a single check command, a baseline of grandfathered findings, and that table. A repository may already have this shape, for example `scripts/check_architecture.py`, `scripts/architecture_baseline.json`, and the rule table in its agent instructions. Extend that shape when it exists. Those paths are an example of the output, not required names in every repository, and they are not a reason to add a second command beside an existing one.

## Report

For each class, report the two commits, the level you used, and why each higher level could not express the rule. When you change nothing, report the sources you read and why no class qualified.

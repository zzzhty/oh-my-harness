---
name: diagnosing-bugs
description: Diagnosis loop for hard bugs and performance regressions. Use when the user says "diagnose"/"debug this", or reports something broken/throwing/failing/slow.
---

# Diagnosing Bugs

Build an evidence-backed explanation of the reported symptom. A request to diagnose or reproduce does not authorize a repair. Report the evidence and proposed fix unless implementing the fix is already in scope. Read relevant domain terms and ADRs when present.

## Evidence and feedback

Record expected versus observed behavior, the affected environment and relevant recent changes. Inspect code, configuration and existing logs to form falsifiable hypotheses; label inference separately from observation.

Choose a check that distinguishes the user's symptom from nearby failures: a focused test, CLI/HTTP/UI reproduction, sanitized trace replay, or comparison with a known-good version. For performance, establish a timing/profile baseline before changing code. For intermittent failures, record the conditions and observed frequency rather than calling a few green runs a fix.

Tighten or minimize the reproduction when doing so separates causes or makes iteration practical. A minimal input, fixed hypothesis count or seconds-long loop is not a prerequisite for every investigation. If reproduction is unavailable, continue with useful read-only evidence and state what remains unverified. Request only the missing access or observation that blocks the next necessary step; do not change production instrumentation without authorization.

Keep secrets out of displayed commands and artifacts: use environment variables for credentials, redact auth headers and quote only relevant output. If a redacted capture cannot answer the question, describe the missing signal without exposing the secret.

## Test the explanation

For each plausible cause, state a prediction and the observation that would falsify it. Test the strongest discriminator first; add competing hypotheses when the evidence leaves a real ambiguity. Change one relevant variable at a time.

Use debugger inspection, targeted temporary instrumentation, or a measured experiment. Mark instrumentation so it can be removed. A human-operated reproduction may use [the HITL template](scripts/hitl-loop.template.sh) when manual interaction is necessary; ordinary code/log investigation does not require that template. Ask for fixed-choice observations, not pasted logs, headers or credentials. Keep sign-in out of capture and inspect and redact any additional evidence before it reaches a terminal transcript, report, or shared artifact.

## Fix and verify

When two or more fixes that share one premise fail the same gate, write the premise in one sentence and test it directly before another fix. Choose an observation that would differ if the premise were false, then follow that evidence. If the premise is wrong, look for what the failures share that it did not predict. If the premise holds, the earlier fixes treated a consequence. Remove the condition that produces the failure instead of compensating for it with another cleanup, retry, or guard. See [NOTICE.md](NOTICE.md).

When repair is authorized and the evidence supports a cause, apply the smallest fix. When a persistent regression test protects a distinct failure mode, first make it fail on the original behavior and then pass with the fix. If an authorized experiment forces the red by mutating code or a fixture, compare it with a pristine copy to prove the mutation actually landed before trusting the failure. An unchanged fixture is not evidence of a successful mutation. Use the interface that reproduces the real failure pattern; a shallow test that cannot trigger it gives no assurance. When the test boundary itself needs design, load `codebase-design` through the active harness's supported skill-loading mechanism. If unavailable, report the dependency and the blocked design step; independent read-only investigation can continue.

Recheck the original scenario, not only a reduced fixture. If that verification is blocked, report the exact limit and available evidence instead of declaring the bug resolved. Preserve useful user artifacts and remove only the temporary instrumentation and disposable files created for this investigation.

Report the cause, observed result, remaining uncertainty, and any proposed or verified change. Recommend architectural follow-up only when the investigation demonstrates a missing test boundary or coupling problem; it does not automatically start another workflow.

# Host Handoff And Status

This workflow does not supply a scheduler, daemon, resume protocol, or status API. Inspect the active host's available tools. A foreground worker, a shell subprocess, and an ordinary subagent are not proof of durable detached execution.

## Background Dispatch

1. Establish that the host can accept and identify a task that continues outside the current turn and can be queried. If the user explicitly requested native Goal plus background, require a host route that actually supports the same Goal in detached execution and retains its lifecycle, gates and owner. Do not spawn two jobs.
2. Recheck the current user instruction and exact action scope. Hand off the brief's outcome, scope, verification, inputs and applicable restrictions; pass only authorized access. Keep the caller responsible for final integration and verification.
3. Save the accepted host task/run reference in the existing task record when possible. If the dispatch response is ambiguous, query the host for the accepted run before retrying; if you cannot determine acceptance, report that uncertainty rather than submitting again. Acknowledgment is not a running-state observation.

## Evidence And Reporting

Query the recorded host reference for current state (and check active instructions) before answering a background status request. Do not alter work for a status query. For a native Goal, use its own host state and goal record; for direct work, use observed actions and the existing checkpoint.

| Evidence | Report |
| --- | --- |
| Host accepted the task but has not reported execution | Submitted (or queued if the host says queued). |
| Host reports the identified run active | Running; cite the observed checkpoint if available. |
| Unable to query, stale observation only, or ambiguous dispatch | Current state unverified; state the last confirmed observation and reference, if any. |
| Host reports failed, cancelled, or paused | Report that state and what remains; do not restart as a side effect of checking. |
| Host reports success but exit/result evidence or acceptance checks are missing | Host finished; result not yet verified. |
| Host terminal success and requested artifact/outcome plus acceptance checks verified | Completed; give the evidence or artifact. |

If using workers, obtain host task/worker status from the native receipt or a targeted status query at a meaningful checkpoint or on request, rather than an ad hoc polling loop. Distinguish that observation from the worker's self-report; verify outputs independently before integration. A worker return or success is evidence for its assignment, not host status, proof of delivery, or completion of the integrated task.

For a direct task without a host run, use the actual check results and artifact rather than inventing a run status. If the user stops or supersedes work, use the host's supported cancellation only within authorization and verify its outcome; until observed, report cancellation requested, not cancelled. Never expose credentials, unrelated logs, or private worker notes in the task record or report.

# Scope And Authority

This workflow records and applies existing user permission. It cannot grant host
capabilities, silence a native approval prompt, or bypass sandbox or repository
policy. A host denial wins over a matching brief or earlier approval. Stop the
affected branch; continue only independent authorized work that can still help.

## Reuse A Decision, Not A Permission Label

| Record | Applies only to |
| --- | --- |
| Source of authority | The actual user decision or applicable standing rule, with reference or exact scope; never a summary without a source. |
| Covered effect | Action/tool, exact target and affected paths, data or destination; include working directory, important arguments, and potential external/irreversible effects when relevant. |
| Limits | Named exclusions, prerequisites, recipients, time/expiration or one-time scope, and when to stop. |
| Current state | Valid for the proposed action now, superseded/revoked, expired/exhausted, or unresolved. Recheck latest user direction before dispatch and after a pause, handoff, or scope change. |

Keep these details with the existing task record only when needed. Workers receive
the part that applies to their assignment. They may not extend permission, grant
permission to other workers, or route around a denial. If a worker cannot see
the authoritative decision, the parent resolves it before the affected action;
the worker reports the exact blocker instead of asking the user independently.

The parent groups only identical approval requests: same action, arguments that
matter, target, working directory, destination, side effects and authority
conditions. The same command text in different directories or against different
targets is not the same request. Do not re-ask an already authorized decision
that still covers the action, but honor each native approval requirement. If a
new decision is necessary, ask once with the concrete effect and preserve
conditional, limited, or negative answers. Revocation and expiry invalidate
cached authorization and prevent retries until new approval expressly covers them.

For a native Goal, its own planning preflight and runtime hard stops still own
authority. Do not copy a Goal's Ready permissions into an unrelated task, or
promote a direct/background brief to Ready.

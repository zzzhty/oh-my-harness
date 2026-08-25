# API Or Schema Inspection

Use this branch when claims depend on API compatibility, schema shape, serialization, migrations, clients, fixtures, or wire contracts. Keep UI-only and documentation-only work out unless it consumes the inspected contract.

## Candidate Assignments

Choose assignments by independent contract surface:

| `task_name` | Assignment prompt focus | Prompt permission |
| --- | --- | --- |
| `schema_mapper` | Map schemas, serializers, migrations, clients, fixtures, and tests. | `Permission: read-only` for the named contract and known consumers. |
| `compatibility_reviewer` | Assess backward, forward, rollout, and persisted-data compatibility. | `Permission: read-only` for exact current and prior contract evidence. |
| `official_assumption_checker` | Verify external API, configuration, version, or migration assumptions against authoritative material. | `Permission: read-only` for local source and approved external reads; no external writes. |
| `fixture_gap_reviewer` | Identify validation commands and missing fixture coverage. | `Permission: read-only` for fixtures, tests, and validation scripts. |

Every prompt names the contract version or source, known consumers, and the evidence needed before making a compatibility claim.

## Completion Criterion

Every compatibility claim cites exact schema, migration, serializer, client, fixture, or command evidence; inaccessible consumers and unresolved rollout risks remain explicit.

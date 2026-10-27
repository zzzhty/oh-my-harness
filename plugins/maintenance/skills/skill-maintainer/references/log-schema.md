> Historical schema reference: the automatic collector and its hooks are retired. Read retained records without restarting collection.

# Watcher Skill Log Schema

Watcher writes one redacted skill-domain JSON object per line to `$CODEX_HOME/watcher/skill/logs/events.jsonl`.

Core fields:

- `schema_version`: current value `2`; evidence clarification is additive and requires no log reset.
- `event_id`: collector-generated UUID when absent.
- `timestamp`: collector-generated UTC ISO-8601 timestamp when absent.
- `agent`: defaults to `codex`.
- `event_type`: lifecycle label such as `user_prompt_submit`, `post_tool_use`, `turn_summary`, `user_feedback`, or `failure`.
- `workspace`, `session_id`, `trigger_reason`.
- `tools_used`: array of tool or command names.
- `files_touched`: array of paths, without file contents.
- `outcome`: raw event observation such as `success`, `failure`, `partial`, or `unknown`; never a fallback task outcome. New tool observations use recognized structured status fields only, not text keywords.
- `task_outcome`: turn-level task outcome when known; do not infer it from tool failures alone.
- `failure_type`: optional category such as `tool_error`, `wrong_assumption`, `missed_validation`, `format_error`, or `user_correction`.
- `skill_attribution`: primary/supporting/effective/mentioned skill attribution.
- `tests_or_checks`: array of validation actions.
- `user_feedback` and `notes`: short factual summaries.
- `codex`: hook metadata, turn id, redacted summaries, and turn summaries.

Skill attribution fields:

- `skill_attribution.primary`: optional structured selection assertion (`provided` or manual), with name, source, role, alias and confidence. Confidence describes identity matching, not execution. New text-only evidence has `primary: null`. Historical primary fields remain readable and are classified by their recorded source.
- `skill_attribution.supporting`: dependency declarations (`manifest_dependency`), not observed loads/calls; alternatives and conditional branches remain undeclared.
- `skill_attribution.effective`: preserved compatibility field for primary plus declared supporting identities. It is not an execution total; new mention-only events leave it empty.
- `skill_attribution.mentioned`: all runtime text matches with `prompt_mention` or `assistant_mention` sources. Quotes, negations, frequency tables and comparisons are still only mentions; no catalog-first primary or execution order is inferred. Historical `assistant_announcement` is also a mention.
- `skill_attribution.execution_status`: `unknown`; the retired hooks supplied no supported evidence of skill loading/invocation. Missing historical values also mean unknown.
- `codex.user_skill_context`: redacted summary/hash of extra prompt context accompanying a structured selection. Text-only matches retain the ordinary bounded `prompt_summary`.
- `codex.turn_summary`: per-turn task outcome, tool counts, and tool failure observations written on `Stop`. Hook task outcomes remain `unknown`. `tool_failure_source` identifies new structured observations; absent historical provenance is reported as `unspecified_legacy`.
- `codex.tool_outcome_source`: `structured_tool_response` or `unavailable` for new tool observations. Missing historical sources are not upgraded.

Collectors must avoid full prompts, file contents, complete command transcripts, secrets, and private business data. Store summaries, hashes, counts, and explicit skill context signals instead.

Reports are read-only projections of these records. They fold only declared
`legacy_names`, retain raw identities and unmapped history, and treat current
logical groups as display categories, not historical trigger policy. Evidence
counts deduplicate summarized session/turn keys; the last repeated summary wins.
Unrecognized historical attribution is unclassified. The earlier single
`skill_name` shape is also readable as unclassified evidence. Explicit historical
`task_outcome` assertions are displayed without independently verifying provenance;
raw event `outcome` and failure labels cannot supply task results. Incomplete
coverage means no success/failure rate or execution count is available.

See [the evidence decision](https://github.com/zzzhty/oh-my-harness/blob/main/docs/adr/0027-report-watcher-evidence-without-execution-claims.md)
for compatibility and validation boundaries.

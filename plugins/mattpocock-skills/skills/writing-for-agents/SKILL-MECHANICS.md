# Skill Mechanics

Use the active harness's supported metadata and installed skill tooling. Keep the required `name` and `description`; preserve other supported fields and the existing invocation choice.

In this repository, `agents/openai.yaml` carries Codex UI metadata and `policy.allow_implicit_invocation`. A value of `false` keeps an entrypoint explicit-only. Some skills also carry `disable-model-invocation: true` for harnesses that consume that frontmatter; keep the two policies consistent when both are present.

Descriptions identify the capability and relevant trigger. Bodies supply the workflow, references supply conditional detail. Do not infer identical loading or cross-skill invocation behavior across every harness from a single frontmatter flag.

A router helps users select among entrypoints; it should not turn every task into a complete workflow. Recommend explicit-only entrypoints in accordance with the current harness and user request. Shared methods can remain independent skills or ordinary references where their actual consumers justify that structure.

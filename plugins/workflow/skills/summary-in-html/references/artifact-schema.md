# Summary Artifact Schema

Read this before writing the JSON consumed by `render_summary_html.py`.

## Location

Use the requested output path. For a custom HTML path, keep the JSON beside it and assets in a sibling `assets/` directory unless the user specifies otherwise. Without a requested path, place the HTML and JSON under `docs/summaries/` with the same scope-based stem and generated assets under `docs/summaries/assets/`.

## Common Object

Required or useful top-level fields:

- `title`
- optional `subtitle`, `scope_label`, and absolute `source_root`
- `evidence`: `{path, label?, role?}`
- `assets`: `{path, alt, caption}`
- `sections`
- `blind_spots`

Each section has a `title` and may include:

- `summary`
- `paragraphs` and `bullets` as string lists
- `files`: `{path, note?}`
- `code`: `{text, language?}`
- `completion_check` where the document contract requires one

Omit empty optional fields. Paths and required asset fields are non-empty. The renderer validates member types before writing HTML.

A minimal summary input is:

```json
{
  "title": "Workflow Plugin Summary",
  "scope_label": "plugins/workflow",
  "source_root": "/workspace/oh-my-harness",
  "evidence": [{"path": "workflow.inputs.json", "label": "Inventory"}],
  "sections": [
    {
      "title": "Purpose",
      "summary": "What this scope owns.",
      "files": [{"path": "plugins/workflow/README.md"}]
    }
  ],
  "blind_spots": ["Tests were not run."]
}
```

## Source Walkthrough

Read `source_walkthrough_contract.md`, set `document_type` to `source_walkthrough`, and record `source_revision`. Only complete handoff steps receive `completion_check`; overview and follow-up sections remain unnumbered. Include at least one evidence item with role `current_source`.

## Assets And Rendering

Include assets only when generated visuals were requested and the files exist; follow `visual_asset_contract.md`. The rendered page remains standalone with inline CSS, no remote fonts, and no external scripts.

---
status: accepted
---

# Versioned content publishing

OMH is a standalone harness. It also publishes versioned skills, helper
resources, and compositions that other tools may optionally consume as a
content source.

This decision retired the public Python installer entry points
(`.agents/harnesses/`, lifecycle scripts, `install.sh` / `install.ps1`) and
the skill-watcher collector and hooks. `content-manifest.json` remains the
versioned content contract: content IDs, internal resources, compositions,
and runtime requirements. Content does not specify host paths or post-install
scripts.

The default composition keeps the skills as complete native plugins.
Maintenance skills stay explicit callable workflows; report and audit helpers
stay optional. Importing or preparing a runtime does not enable hooks.

Plugin byte identity remains `sha256-canonical-plugin-tree-v1`. Historical
ADRs and evidence are kept; their operational entry points are not current
guidance.

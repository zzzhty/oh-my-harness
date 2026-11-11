---
status: accepted
---

# Standalone CLI grammar and readable output

A command-surface audit found every flag shared across one flat parser —
irrelevant combinations were silently accepted, `omh <command> --help`
printed the same wall of flags as `omh --help` — and raw JSON was the only
output of every command except `status`. Three changes:

1. **Subcommand grammar.** Each command owns its flag set through
   `add_subparsers`: `--source`/`--home` stay global and parse before or
   after the command; `--harness`/`--skills-root` belong to the target
   commands; the runtime flags (`--python`, `--external-venv`, `--offline`,
   `--deployment-root`) to `prepare`/`install`/`update`; `--bin-dir` to
   `install`/`update`; `--operation` to `plan`. Combinations the flat parser
   silently accepted (for example `--operation` on `status`) are now usage
   errors with exit 2. This amends ADR 0031's "no functionality is removed
   from the standalone CLI": rejected combinations were never meaningful, and
   every documented invocation keeps working unchanged.
2. **Readable by default, machine on request, everywhere.** Every command
   prints a short human summary; `--json` returns the machine form with the
   exact JSON shapes previously printed unconditionally. This extends ADR
   0034's status rule to the whole CLI and evolves its "plan remains a
   per-target preview and is unchanged" clause: `plan` still previews one
   target, and its `--json` shape is unchanged, but its default output is now
   a two-line change summary. Errors remain stderr JSON with exit 1; usage
   errors remain argparse text with exit 2.
3. **Default-target hint.** Target commands still default `--harness` to
   `codex` (historical default from ADR 0007's registry era). When the home
   index knows other harnesses and the default `~/.codex` root holds no
   receipt, the CLI prints a one-line note listing the installed harnesses on
   stderr before doing anything. The note is suppressed under `--json`.

Tests and `scripts/check_standalone_distribution.py` consume `--json`.

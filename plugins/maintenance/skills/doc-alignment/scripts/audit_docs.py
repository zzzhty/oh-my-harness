#!/usr/bin/env python3
"""Run the doc-alignment skill's audit helpers; this is not an installer."""

from __future__ import annotations

import argparse
import importlib
import sys

COMMANDS = {
    "audit": "audit_repo",
    "report": "report",
    "commit-counter": "commit_counter",
    "doctor": "doctor",
}


def main(argv: list[str] | None = None) -> int:
    # Paths and reports may contain Unicode even when Windows redirects output
    # through a legacy code page. Keep the helper's stream contract explicit.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=COMMANDS)
    # Let each helper own its detailed options and --help without importing it
    # during top-level help. No helper runs until its command is explicit.
    if not arguments or arguments[0] in {"-h", "--help"}:
        parser.print_help()
        return 0
    selected = parser.parse_args(arguments[:1])
    module = importlib.import_module(f"doc_alignment.{COMMANDS[selected.command]}")
    return int(module.main(arguments[1:]))


if __name__ == "__main__":
    raise SystemExit(main())

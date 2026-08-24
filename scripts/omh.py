#!/usr/bin/env python3
"""Public ``omh`` lifecycle-management entry point."""

from __future__ import annotations

from omh_manager.cli import cli


if __name__ == "__main__":
    raise SystemExit(cli())

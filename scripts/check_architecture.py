#!/usr/bin/env python3
"""Repository architecture checks. Local and CI run this same command.

    python scripts/check_architecture.py

Each finding prints Violation, Fix, and Principle. The script exits 1 when any
finding is an error. Warnings do not fail the run. Grandfathered sizes, locale
text calls, and ruff findings live in scripts/architecture_baseline.json.
Do not raise that file to admit a new violation.

The checker uses only the standard library. It shells out to ruff, a developer
dependency in requirements.txt, which omh/ does not import. Rule bodies live in
architecture_rules.py so this entry stays under the file-length warning.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from architecture_rules import (
    FILE_ERROR_LINES,
    FILE_WARN_LINES,
    Violation,
    _import_sites,
    _mapping,
    _violation,
    check_closed_argv,
    check_harness_identity,
    check_stdout_utf8,
    check_text_io,
    count_lines,
    iter_files,
    python_line_counts,
    relpath,
    text_io_counts,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = Path(__file__).resolve().parent / "architecture_baseline.json"
RUFF_CONFIG = REPO_ROOT / "ruff.toml"
__all__ = [
    "check",
    "count_lines",
    "exit_code",
    "load_baseline",
    "main",
    "ruff_fingerprint",
    "snapshot_baseline",
]


def ruff_fingerprint(path: str, code: str, message: str) -> str:
    return f"{path}|{code}|{message}"


def ruff_findings(root: Path) -> list[tuple[str, int, str, str]]:
    completed = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--config", str(RUFF_CONFIG), "--output-format", "json", str(root)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    stdout = completed.stdout.strip()
    if completed.returncode not in (0, 1) or not stdout.startswith("["):
        detail = (completed.stderr or completed.stdout or "ruff produced no JSON").strip()
        raise RuntimeError(detail)
    findings: list[tuple[str, int, str, str]] = []
    for item in json.loads(stdout):
        filename = Path(item["filename"])
        if not filename.is_absolute():
            filename = root / filename
        try:
            relative = relpath(root, filename)
        except ValueError:
            relative = filename.as_posix()
        findings.append((relative, int(item["location"]["row"]), str(item["code"]), str(item["message"])))
    return findings


def _ruff_list(baseline: dict[str, Any]) -> list[str]:
    value = baseline.get("ruff", [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("ruff must be a list of fingerprint strings")
    return list(value)


def load_baseline(path: Path = BASELINE_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("architecture baseline must be a JSON object")
    _mapping(data, "file_lines")
    _mapping(data, "text_io_utf8")
    _ruff_list(data)
    return data


def snapshot_baseline(root: Path | None = None) -> dict[str, Any]:
    """Current grandfathered state. Writing this over the baseline hides new violations."""
    root = REPO_ROOT if root is None else root
    return {
        "notes": (
            "Ratchet, not a waiver. file_lines values are ceilings for Python files "
            "already over 500 lines. text_io_utf8 values are the maximum number of "
            "locale-dependent text calls allowed in that file. ruff is the exact "
            "grandfathered finding multiset. Do not raise an entry to land a new violation."
        ),
        "file_lines": {
            path: count for path, count in sorted(python_line_counts(root).items()) if count > FILE_WARN_LINES
        },
        "text_io_utf8": dict(sorted(text_io_counts(root).items())),
        "ruff": sorted(
            ruff_fingerprint(path, code, message) for path, _line, code, message in ruff_findings(root)
        ),
    }


def check_file_length(root: Path, baseline: dict[str, Any]) -> list[Violation]:
    ceilings = _mapping(baseline, "file_lines")
    violations: list[Violation] = []
    for relative, lines in sorted(python_line_counts(root).items()):
        ceiling = ceilings.get(relative)
        if ceiling is not None:
            if lines > ceiling:
                violations.append(_violation(
                    "ERROR", relative, lines, "file-length",
                    f"File grew from its baseline of {ceiling} lines to {lines}.",
                    f"This file is capped at {ceiling} lines in scripts/architecture_baseline.json. "
                    "Move the new code into a new module. Do not raise the ceiling to land growth "
                    "that can live in a new file.",
                ))
            continue
        if lines > FILE_ERROR_LINES:
            violations.append(_violation(
                "ERROR", relative, lines, "file-length",
                f"New Python file exceeds {FILE_ERROR_LINES} lines ({lines}).",
                "Split this file before adding it. Put the extra behavior in a new module. "
                "A new Python file fails above 1000 lines and warns above 500.",
            ))
        elif lines > FILE_WARN_LINES:
            violations.append(_violation(
                "WARN", relative, lines, "file-length",
                f"New Python file exceeds {FILE_WARN_LINES} lines ({lines}).",
                "Split this file by concern before it reaches 1000 lines. It is not in "
                "scripts/architecture_baseline.json, so further growth stays a warning until 1000.",
            ))
    return violations


def check_distributor_stdlib(root: Path) -> list[Violation]:
    package = root / "omh"
    if not package.is_dir():
        return []
    violations: list[Violation] = []
    fix = (
        "Remove this import from omh/. Third-party packages stay in requirements.txt and scripts/ "
        "(scripts/validate_plugin.py is the developer yaml importer). omh/standalone.py imports only "
        "the standard library and loads plugins/workflow/scripts/omh_runtime.py with importlib."
    )
    for path in iter_files(package, ".py"):
        relative = relpath(root, path)
        try:
            sites = _import_sites(ast.parse(path.read_text(encoding="utf-8")))
        except SyntaxError:
            continue
        for line, module in sites:
            violations.append(_violation(
                "ERROR", relative, line, "distributor-stdlib",
                f"Distributor module imports third-party package {module}.",
                fix,
            ))
    return violations


def check_ruff(root: Path, baseline: dict[str, Any]) -> list[Violation]:
    allowed = Counter(_ruff_list(baseline))
    try:
        findings = ruff_findings(root)
    except (OSError, json.JSONDecodeError, RuntimeError) as exc:
        return [_violation(
            "ERROR", "ruff.toml", 1, "ruff",
            f"ruff could not run: {exc}",
            "Install developer dependencies with python -m pip install -r requirements.txt, "
            "then rerun python scripts/check_architecture.py. The checker invokes python -m ruff.",
        )]
    current: Counter[str] = Counter()
    details: dict[str, tuple[str, int, str, str]] = {}
    for path, line, code, message in findings:
        fingerprint = ruff_fingerprint(path, code, message)
        current[fingerprint] += 1
        details[fingerprint] = (path, line, code, message)
    violations: list[Violation] = []
    for fingerprint, count in sorted(current.items()):
        extra = count - allowed[fingerprint]
        if extra <= 0:
            continue
        path, line, code, message = details[fingerprint]
        violations.append(_violation(
            "ERROR", path, line, "ruff",
            f"{code} {message} ({extra} new; baseline allows {allowed[fingerprint]}).",
            "Fix this ruff finding in the file it names. Do not add it to the ruff list in "
            "scripts/architecture_baseline.json. The rule set is ruff.toml (F, E9, B).",
        ))
    for fingerprint, count in sorted(allowed.items()):
        stale = count - current[fingerprint]
        if stale <= 0:
            continue
        path = fingerprint.split("|", 1)[0]
        violations.append(_violation(
            "ERROR", path, 1, "ruff",
            f"Baseline entry no longer matches the tree ({stale} extra): {fingerprint}.",
            "Remove that entry from the ruff list in scripts/architecture_baseline.json after "
            "confirming the finding is gone.",
        ))
    return violations


def check(root: Path, baseline: dict[str, Any], *, ruff: bool = True) -> list[Violation]:
    violations = [
        *check_text_io(root, baseline),
        *check_stdout_utf8(root),
        *check_file_length(root, baseline),
        *check_closed_argv(root),
        *check_harness_identity(root),
        *check_distributor_stdlib(root),
    ]
    if ruff:
        violations.extend(check_ruff(root, baseline))
    violations.sort(key=lambda item: (item.path, item.line, item.rule, item.violation))
    return violations


def exit_code(violations: list[Violation]) -> int:
    return 1 if any(item.level == "ERROR" for item in violations) else 0


def main(argv: list[str] | None = None) -> int:
    if argv:
        raise SystemExit("python scripts/check_architecture.py takes no arguments")
    try:
        baseline = load_baseline()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        item = _violation(
            "ERROR", BASELINE_PATH.name, 1, "syntax",
            f"Architecture baseline could not be read: {exc}",
            "Restore scripts/architecture_baseline.json as the committed ratchet.",
        )
        print(item.render())
        print("[ARCH] Failed with 1 error(s), 0 warning(s).")
        return 1
    violations = check(REPO_ROOT, baseline)
    for item in violations:
        print(item.render())
    errors = sum(item.level == "ERROR" for item in violations)
    warnings = sum(item.level == "WARN" for item in violations)
    if errors:
        print(f"[ARCH] Failed with {errors} error(s), {warnings} warning(s).")
        return 1
    print(f"[ARCH] Passed with {warnings} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

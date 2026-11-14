"""Architecture rule implementations imported by scripts/check_architecture.py.

The entry command remains `python scripts/check_architecture.py`.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", ".mypy_cache", ".ruff_cache"}
FILE_WARN_LINES = 500
FILE_ERROR_LINES = 1000
# parse_known_args forwards helper argv only here. Every other command is closed.
KNOWN_ARGS_FILE = "plugins/workflow/scripts/omh_runtime.py"
KNOWN_ARGS_LIMIT = 1
# These entry points already had to grow an explicit UTF-8 stream reconfigure.
UTF8_ENTRYPOINTS = (
    "omh/standalone.py",
    "plugins/maintenance/skills/doc-alignment/scripts/audit_docs.py",
)
# Short ids that were made canonical and then reverted.
SHORT_CANONICAL = frozenset({"omp", "copilot", "gemini"})
SUBPROCESS_ATTRS = frozenset({
    "run", "check_output", "check_call", "Popen", "call", "getoutput", "getstatusoutput",
})
DISTINCT_SUBPROCESS_NAMES = frozenset({
    "check_output", "check_call", "Popen", "getoutput", "getstatusoutput",
})
GET_CONTENT = re.compile(r"(?i)(?<![-\w])Get-Content\b")
PS_ENCODING = re.compile(r"(?i)(?<![-\w])-Encoding\b")

PRINCIPLES = {
    "text-io-utf8": "Text reads and child-process output must name UTF-8. Locale decoding broke Unicode audit paths, Windows interpreter bindings, target indexes, and piped status text (557a629, 74f6145, 6ccb996, 5ec86f8).",
    "cli-stdout-utf8": "CLI stdout and stderr are UTF-8 on every platform, including Windows pipes that otherwise use the ANSI code page (557a629, 5ec86f8).",
    "file-length": "Python files stay readable: warn above 500 lines, fail above 1000, and a file already over 500 may not grow past its ceiling in scripts/architecture_baseline.json.",
    "closed-argv": "A closed command rejects unknown arguments. Inapplicable flags used to be silently ignored (ADR 0035, 99cde26), and parse_known_args turned typos into KeyError or NoneType protocol failures (d663090).",
    "harness-identity": "Canonical harness ids are one full-name set. Short ids were promoted and then reverted twice: copilot and gemini (ADR 0018, superseded by ADR 0023) and omp (ADR 0025, superseded by ADR 0026, commit 6e63ea0).",
    "distributor-stdlib": "python -m omh is the sole distributor and imports only the standard library (ADR 0031). The previous Python installer (CHANGELOG 1.2.0) and the Rust export/import core were both retired. requirements.txt is for developer validation only.",
    "ruff": "Pyflakes and Bugbear catch undefined names, unused imports, and loop-bound closures. Existing findings are an exact list in scripts/architecture_baseline.json. ruff is a developer dependency and is not imported by omh/.",
    "syntax": "The architecture check has to parse a Python file before it can apply the other rules.",
}

TEXT_IO_FIX = {
    "read_text": 'Pass encoding="utf-8" to this Path.read_text call, or use read_bytes() when the caller decodes explicitly. Follow omh_runtime.launch, which uses Path.read_text(encoding="utf-8").',
    "write_text": 'Pass encoding="utf-8" to this Path.write_text call. Follow omh_runtime.launch, which uses Path.read_text(encoding="utf-8") for the same UTF-8 contract.',
    "open": 'Pass encoding="utf-8" to this open or fdopen call unless the mode is binary. os.open is the file-descriptor syscall and is not a text read. Follow the UTF-8 contract in omh_runtime.launch.',
    "subprocess": 'Pass encoding="utf-8" and errors="replace" on this subprocess call. Follow doc_alignment.audit_repo.run_git.',
    "get-content": "Add -Encoding UTF8 to this Get-Content call. Follow plugins/workflow/scripts/run.ps1.",
}


@dataclass(frozen=True)
class Violation:
    level: str
    path: str
    line: int
    rule: str
    violation: str
    fix: str
    principle: str

    def render(self) -> str:
        return (
            f"[ARCH][{self.level}] {self.path}:{self.line}\n"
            f"  Violation: {self.rule}: {self.violation}\n"
            f"  Fix: {self.fix}\n"
            f"  Principle: {self.principle}\n"
        )


@dataclass(frozen=True)
class Site:
    line: int
    kind: str


def count_lines(text: str) -> int:
    """Line count matching wc -l for a file that ends in a newline."""
    if not text:
        return 0
    lines = text.count("\n")
    if not text.endswith("\n"):
        lines += 1
    return lines


def relpath(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def iter_files(root: Path, suffix: str) -> list[Path]:
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in SKIP_DIRS)
        for name in sorted(filenames):
            if name.endswith(suffix):
                found.append(Path(dirpath) / name)
    return found


def _keyword(call: ast.Call, name: str) -> ast.expr | None:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _encoding_provided(call: ast.Call, positional_index: int) -> bool:
    if _keyword(call, "encoding") is not None:
        return True
    return len(call.args) > positional_index


def _text_open_mode_index(func: ast.expr) -> int | None:
    """Positional index of the mode argument, or None when the call is not text open."""
    if isinstance(func, ast.Name) and func.id == "open":
        return 1
    if not isinstance(func, ast.Attribute):
        return None
    if func.attr == "fdopen":
        return 1
    if func.attr != "open":
        return None
    receiver = func.value.id if isinstance(func.value, ast.Name) else None
    if receiver == "os":
        return None
    if receiver in {"io", "builtins"}:
        return 1
    return 0


def _mode_is_binary(node: ast.expr | None) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and "b" in node.value


def _is_subprocess_text(func: ast.expr, call: ast.Call) -> bool:
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        is_subprocess = func.value.id == "subprocess" and func.attr in SUBPROCESS_ATTRS
    elif isinstance(func, ast.Name):
        is_subprocess = func.id in DISTINCT_SUBPROCESS_NAMES
    else:
        is_subprocess = False
    if not is_subprocess:
        return False
    requested = False
    for name in ("text", "universal_newlines"):
        node = _keyword(call, name)
        if node is None:
            continue
        if isinstance(node, ast.Constant) and node.value is False:
            continue
        requested = True
    return requested and _keyword(call, "encoding") is None


def python_text_sites(source: str) -> list[Site]:
    tree = ast.parse(source)
    sites: list[Site] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in {"read_text", "write_text"}:
            index = 0 if func.attr == "read_text" else 1
            if not _encoding_provided(node, index):
                sites.append(Site(node.lineno, func.attr))
            continue
        mode_index = _text_open_mode_index(func)
        if mode_index is not None:
            mode = _keyword(node, "mode")
            if mode is None and len(node.args) > mode_index:
                mode = node.args[mode_index]
            encoding_index = 3 if mode_index == 1 else 2
            if not _mode_is_binary(mode) and not _encoding_provided(node, encoding_index):
                sites.append(Site(node.lineno, "open"))
            continue
        if _is_subprocess_text(func, node):
            sites.append(Site(node.lineno, "subprocess"))
    return sites


def powershell_text_sites(source: str) -> list[Site]:
    logical: list[tuple[int, str]] = []
    buffer: list[str] = []
    start = 1
    for number, line in enumerate(source.splitlines(), 1):
        if not buffer:
            start = number
        buffer.append(line)
        if line.rstrip().endswith("`"):
            continue
        logical.append((start, "\n".join(buffer)))
        buffer = []
    if buffer:
        logical.append((start, "\n".join(buffer)))
    sites: list[Site] = []
    for number, chunk in logical:
        code = re.sub(r"(?m)#.*$", "", chunk)
        if GET_CONTENT.search(code) and not PS_ENCODING.search(code):
            sites.append(Site(number, "get-content"))
    return sites


def text_io_counts(root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in iter_files(root, ".py"):
        source = path.read_text(encoding="utf-8")
        try:
            count = len(python_text_sites(source))
        except SyntaxError:
            continue
        if count:
            counts[relpath(root, path)] = count
    for path in iter_files(root, ".ps1"):
        count = len(powershell_text_sites(path.read_text(encoding="utf-8")))
        if count:
            counts[relpath(root, path)] = count
    return counts


def python_line_counts(root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in iter_files(root, ".py"):
        counts[relpath(root, path)] = count_lines(path.read_text(encoding="utf-8"))
    return counts


def _call_has_utf8_reconfigure(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
        if name != "reconfigure":
            continue
        encoding = _keyword(node, "encoding")
        if isinstance(encoding, ast.Constant) and isinstance(encoding.value, str):
            if encoding.value.lower().replace("-", "") in {"utf8", "utf8sig"}:
                return True
    return False


def _literal_strings(node: ast.expr) -> set[str] | None:
    if isinstance(node, ast.Dict):
        values: set[str] = set()
        for key in node.keys:
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                return None
            values.add(key.value)
        return values
    if isinstance(node, (ast.List, ast.Set, ast.Tuple)):
        values = set()
        for elt in node.elts:
            if not isinstance(elt, ast.Constant) or not isinstance(elt.value, str):
                return None
            values.add(elt.value)
        return values
    return None


def _references_name(node: ast.AST, name: str) -> bool:
    return any(isinstance(child, ast.Name) and child.id == name for child in ast.walk(node))


def _harness_sets(tree: ast.AST) -> dict[str, tuple[int, set[str] | None]]:
    found: dict[str, tuple[int, set[str] | None]] = {}
    for node in ast.walk(tree):
        targets: list[ast.expr] = []
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
            value = node.value
        if value is None:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id in {"HARNESS_ROOTS", "INSTRUCTIONS"}:
                found[target.id] = (target.lineno, _literal_strings(value))
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        attr = func.attr if isinstance(func, ast.Attribute) else None
        if attr != "add_argument" or not node.args:
            continue
        first = node.args[0]
        if not isinstance(first, ast.Constant) or first.value != "--harness":
            continue
        for keyword in node.keywords:
            if keyword.arg != "choices":
                continue
            choices = _literal_strings(keyword.value)
            if choices is None and _references_name(keyword.value, "HARNESS_ROOTS"):
                choices = found.get("HARNESS_ROOTS", (0, None))[1]
            found["choices"] = (keyword.value.lineno, choices)
    return found


def _stdlib_root(alias: ast.alias) -> str:
    return alias.name.split(".", 1)[0]


def _import_sites(tree: ast.AST) -> list[tuple[int, str]]:
    allowed = sys.stdlib_module_names
    sites: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = node.names
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            modules = [ast.alias(name=node.module or "", asname=None)]
        else:
            continue
        for alias in modules:
            root_name = _stdlib_root(alias)
            if root_name and root_name not in allowed:
                sites.append((node.lineno, root_name))
    return sites


def _parse_known_args_lines(tree: ast.AST) -> list[int]:
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
        if name == "parse_known_args":
            lines.append(node.lineno)
    return lines

def _mapping(baseline: dict[str, Any], key: str) -> dict[str, int]:
    value = baseline.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object of path to count")
    mapping: dict[str, int] = {}
    for path, count in value.items():
        if not isinstance(path, str) or isinstance(count, bool) or not isinstance(count, int):
            raise ValueError(f"{key}[{path!r}] must be an integer count")
        mapping[path] = count
    return mapping

def _violation(level: str, path: str, line: int, rule: str, violation: str, fix: str) -> Violation:
    return Violation(level, path, line, rule, violation, fix, PRINCIPLES[rule])


def check_text_io(root: Path, baseline: dict[str, Any]) -> list[Violation]:
    allowed = _mapping(baseline, "text_io_utf8")
    found: dict[str, list[Site]] = {}
    violations: list[Violation] = []
    for path in iter_files(root, ".py"):
        relative = relpath(root, path)
        source = path.read_text(encoding="utf-8")
        try:
            sites = python_text_sites(source)
        except SyntaxError as exc:
            violations.append(_violation(
                "ERROR", relative, exc.lineno or 1, "syntax",
                f"Python syntax error: {exc.msg}",
                "Fix the syntax error so the architecture check can read this file.",
            ))
            continue
        if sites:
            found[relative] = sites
    for path in iter_files(root, ".ps1"):
        sites = powershell_text_sites(path.read_text(encoding="utf-8"))
        if sites:
            found[relpath(root, path)] = sites
    for relative, sites in sorted(found.items()):
        ceiling = allowed.get(relative, 0)
        if len(sites) <= ceiling:
            continue
        if ceiling == 0:
            for site in sites:
                violations.append(_violation(
                    "ERROR", relative, site.line, "text-io-utf8",
                    f"Locale-dependent text call ({site.kind}) with no explicit encoding.",
                    TEXT_IO_FIX[site.kind],
                ))
            continue
        lines = ", ".join(str(site.line) for site in sites)
        violations.append(_violation(
            "ERROR", relative, max(site.line for site in sites), "text-io-utf8",
            f"{len(sites)} locale-dependent text calls; the baseline allows {ceiling} (lines {lines}).",
            "Pass encoding=\"utf-8\" on the new call. Do not increase text_io_utf8 for this file in "
            "scripts/architecture_baseline.json. Path text calls follow omh_runtime.launch, subprocess "
            "calls follow doc_alignment.audit_repo.run_git, and Get-Content follows "
            "plugins/workflow/scripts/run.ps1.",
        ))
    return violations


def check_stdout_utf8(root: Path) -> list[Violation]:
    violations: list[Violation] = []
    for relative in UTF8_ENTRYPOINTS:
        path = root / relative
        if not path.is_file():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        if _call_has_utf8_reconfigure(tree):
            continue
        violations.append(_violation(
            "ERROR", relative, 1, "cli-stdout-utf8",
            "This entry point no longer reconfigures its text streams to UTF-8.",
            'Call reconfigure(encoding="utf-8") on sys.stdout and sys.stderr inside '
            "omh.standalone.main, and keep the same call in audit_docs.main.",
        ))
    return violations

def check_closed_argv(root: Path) -> list[Violation]:
    violations: list[Violation] = []
    fix = (
        "Use ArgumentParser.parse_args so unknown flags are usage errors and exit 2. "
        "The only parse_known_args that may remain is one call in omh_runtime.main "
        f"({KNOWN_ARGS_FILE}); only the run operation may forward leftover argv."
    )
    for path in iter_files(root, ".py"):
        relative = relpath(root, path)
        try:
            lines = _parse_known_args_lines(ast.parse(path.read_text(encoding="utf-8")))
        except SyntaxError:
            continue
        if relative == KNOWN_ARGS_FILE:
            if len(lines) > KNOWN_ARGS_LIMIT:
                violations.append(_violation(
                    "ERROR", relative, lines[KNOWN_ARGS_LIMIT], "closed-argv",
                    f"{len(lines)} parse_known_args calls; {KNOWN_ARGS_FILE} may contain only "
                    f"{KNOWN_ARGS_LIMIT}, and only the run operation may forward leftover argv.",
                    fix,
                ))
            continue
        for line in lines:
            violations.append(_violation(
                "ERROR", relative, line, "closed-argv",
                "parse_known_args lets unknown arguments through on a closed command.",
                fix,
            ))
    return violations


def check_harness_identity(root: Path) -> list[Violation]:
    path = root / "omh" / "standalone.py"
    if not path.is_file():
        return []
    try:
        found = _harness_sets(ast.parse(path.read_text(encoding="utf-8")))
    except SyntaxError:
        return []
    violations: list[Violation] = []
    if "HARNESS_ROOTS" not in found:
        violations.append(_violation(
            "ERROR", "omh/standalone.py", 1, "harness-identity",
            "HARNESS_ROOTS is missing.",
            "Restore HARNESS_ROOTS in omh/standalone.py as the single harness-id authority, "
            "and make INSTRUCTIONS and --harness choices the same set.",
        ))
        return violations
    sets = {name: values for name, (_line, values) in found.items()}
    comparable = {name: values for name, values in sets.items() if values is not None}
    denied = sorted(set().union(*comparable.values()) & SHORT_CANONICAL) if comparable else []
    if denied:
        line = min(found[name][0] for name in found if sets.get(name) and set(sets[name] or ()) & SHORT_CANONICAL)
        violations.append(_violation(
            "ERROR", "omh/standalone.py", line, "harness-identity",
            f"Short canonical harness id {', '.join(denied)} is present.",
            "Remove that short id from HARNESS_ROOTS, INSTRUCTIONS, and --harness choices in "
            "omh/standalone.py. Keep the three sets identical. omp, copilot, and gemini are not "
            "canonical ids.",
        ))
    present = [name for name in ("HARNESS_ROOTS", "INSTRUCTIONS", "choices") if name in comparable]
    if len(present) >= 2:
        anchor = comparable["HARNESS_ROOTS"] if "HARNESS_ROOTS" in comparable else comparable[present[0]]
        for name in present:
            if comparable[name] != anchor:
                violations.append(_violation(
                    "ERROR", "omh/standalone.py", found[name][0], "harness-identity",
                    f"{name} is {sorted(comparable[name] or ())}, while HARNESS_ROOTS is {sorted(anchor or ())}.",
                    "Make HARNESS_ROOTS, INSTRUCTIONS, and --harness choices in omh/standalone.py "
                    "the same set of ids. HARNESS_ROOTS is the authority.",
                ))
    return violations


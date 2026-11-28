"""Reject ad hoc version labels in current documentation identities."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import yaml
from markdown_it import MarkdownIt
from markdown_it.token import Token

from architecture_rules import Violation, iter_files

RULE = "doc-version-label"
DOC_ROOTS = ("agents", "docs", "dev_docs", "plugins")
HISTORICAL_DIRS = (
    "docs/releases/",
    "docs/adr/archive/",
    "docs/archive/",
    "dev_docs/archive/",
)
LABEL = re.compile(
    r"(?<![A-Za-z0-9])(?:v[0-9]+|rev(?:ision)?[ \t_+.-]*#?[ \t]*[0-9]+)"
    r"(?![A-Za-z0-9]|\.[0-9])",
    re.IGNORECASE,
)
MARKDOWN = MarkdownIt("commonmark")
ALLOW = re.compile(
    r"[ \t]*<!-- doc-version-label: allow ([^;\n]+); ([^<>\n]*\S[^<>\n]*) -->[ \t]*$"
)
FIX = (
    "Use a stable descriptive name. Identify a published release by its actual tag, "
    "or cite a commit, PR, or date for an iteration."
)
PRINCIPLE = "Git carries draft history; current docs should not create a second version scheme."


def without_front_matter(source: str) -> str:
    lines = source.splitlines(keepends=True)
    if lines and lines[0].rstrip() == "---":
        for index, line in enumerate(lines[1:], 1):
            if line.rstrip() in {"---", "..."}:
                # Delimiters alone also match ordinary Markdown. Require a YAML mapping.
                try:
                    metadata = yaml.compose("".join(lines[1:index]), Loader=yaml.SafeLoader)
                except yaml.YAMLError:
                    return source
                if isinstance(metadata, yaml.MappingNode):
                    return "\n" * (index + 1) + "".join(lines[index + 1:])
                return source
    return source


def heading_tokens(source: str) -> Iterator[tuple[int, list[Token]]]:
    tokens = MARKDOWN.parse(without_front_matter(source))
    for opening, inline in zip(tokens, tokens[1:], strict=False):
        if opening.type == "heading_open" and opening.map is not None and inline.type == "inline":
            yield opening.map[0] + 1, inline.children or []


def visible_text(tokens: list[Token]) -> str:
    parts = []
    for token in tokens:
        if token.type in {"text", "code_inline"}:
            parts.append(token.content)
        elif token.type in {"hardbreak", "softbreak"}:
            parts.append(" ")
        elif token.type == "image":
            parts.append(visible_text(token.children or []))
    return "".join(parts)


def labels(tokens: list[Token]) -> Iterator[str]:
    last = next((token for token in reversed(tokens) if token.type != "text" or token.content.strip()), None)
    exception = ALLOW.fullmatch(last.content) if last is not None and last.type == "html_inline" else None
    approved = exception[1].strip().casefold() if exception else ""
    for match in LABEL.finditer(visible_text(tokens)):
        if match[0].casefold() != approved:
            yield match[0]


def check_doc_version_labels(root: Path) -> list[Violation]:
    paths = list(root.glob("*.md"))
    for directory in DOC_ROOTS:
        paths.extend(iter_files(root / directory, ".md"))
    findings = []
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if (
            relative == "CHANGELOG.md"
            or relative.startswith(HISTORICAL_DIRS)
            or path.is_symlink()
            or not path.is_file()
        ):
            continue
        locations = [
            (1, "Filename", (match[0] for match in LABEL.finditer(path.stem))),
            *((line, "Heading", labels(tokens)) for line, tokens in heading_tokens(path.read_text(encoding="utf-8"))),
        ]
        for line, kind, tokens in locations:
            for token in tokens:
                findings.append(Violation(
                    "ERROR", relative, line, RULE, f"{kind} uses the ad hoc version label {token!r}.", FIX, PRINCIPLE,
                ))
    return findings

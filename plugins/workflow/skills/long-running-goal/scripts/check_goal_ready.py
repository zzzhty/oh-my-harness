#!/usr/bin/env python3
"""Lightweight readiness checks for a long-running-goal Markdown file."""

from __future__ import annotations

import argparse
import html
import ntpath
import posixpath
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

SHARED = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SHARED))

from markdown_contract import (  # noqa: E402
    missing_required_pattern_errors,
    placeholder_errors,
    render_errors,
    strip_fenced_blocks,
    strip_placeholder_example_blocks,
)


@dataclass(frozen=True)
class MilestoneState:
    name: str
    status: str
    review: str
    checkpoint: str


def _table_cells(line: str) -> list[str]:
    return [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]


def milestone_states(markdown_text: str) -> list[MilestoneState]:
    lines = markdown_text.splitlines()
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        header = [cell.casefold() for cell in _table_cells(line)]
        if len(header) < 4 or header[:4] not in (
            ["milestone", "status", "review", "checkpoint"],
            ["stage", "status", "review", "checkpoint"],
            ["阶段", "状态", "review", "checkpoint"],
        ):
            continue

        states: list[MilestoneState] = []
        for row in lines[index + 2 :]:
            if not row.lstrip().startswith("|"):
                break
            cells = _table_cells(row)
            if len(cells) < 4:
                continue
            name_match = re.match(r"(?i)^(M\d+|Close)(?:\s|$)", cells[0])
            if name_match:
                name = name_match.group(1)
                name = name.upper() if name.casefold() != "close" else "Close"
                states.append(MilestoneState(name, *cells[1:4]))
        return states
    return []


def h2_sections(markdown_text: str, heading_pattern: str) -> list[str]:
    matches = re.finditer(
        rf"(?ims)^##\s+(?:{heading_pattern})\s*$\n(?P<body>.*?)(?=^##\s+|\Z)",
        markdown_text,
    )
    return [match.group("body") for match in matches]


def h2_section(markdown_text: str, heading_pattern: str) -> str | None:
    sections = h2_sections(markdown_text, heading_pattern)
    return sections[0] if sections else None


def without_h2_sections(markdown_text: str, heading_pattern: str) -> str:
    return re.sub(
        rf"(?ims)^##\s+(?:{heading_pattern})\s*$\n.*?(?=^##\s+|\Z)",
        "",
        markdown_text,
    )


def _named_contract_field(
    line: str,
    labels: dict[str, str],
) -> tuple[str, str] | None:
    for label, pattern in labels.items():
        match = re.match(
            rf"(?i)^[ ]{{0,3}}(?:\d+\.\s*)?(?:{pattern})"
            rf"(?:\s*/[^:：\n]+)?\s*[:：]\s*(.*)$",
            line,
        )
        if match:
            return label, match.group(1)
    return None


def named_contract_fields(
    section_text: str,
    labels: dict[str, str],
    *,
    allow_indented_continuations: bool = True,
) -> dict[str, str]:
    collected: dict[str, list[str]] = {}
    current: str | None = None
    for line in section_text.splitlines():
        matched = _named_contract_field(line, labels)
        if matched:
            current, value = matched
            collected[current] = [value]
        elif not allow_indented_continuations and line.startswith(("    ", "\t")):
            current = None
        elif current is not None:
            collected[current].append(line)
    return {label: "\n".join(lines).strip() for label, lines in collected.items()}


def named_contract_field_counts(
    section_text: str,
    labels: dict[str, str],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in section_text.splitlines():
        matched = _named_contract_field(line, labels)
        if matched:
            label, _ = matched
            counts[label] = counts.get(label, 0) + 1
    return counts


TIME_ASSESSMENT_HEADING = r"Preflight\s+Time\s+Assessment|执行前耗时评估"
TIME_ASSESSMENT_LABELS = {
    "Assessment target": r"Assessment\s+target|评估目标",
    "Assessment mode": r"Assessment\s+mode|评估模式",
    "Rough elapsed-time estimate": r"Rough\s+elapsed-time\s+estimate|粗略耗时估算",
    "Basis or blocker": r"Basis\s+or\s+blocker|依据或阻碍",
    "Critical-path time-cost distribution": (
        r"Critical-path\s+time-cost\s+distribution|关键路径耗时分布"
    ),
}


def _scalar_contract_value(value: str) -> str:
    return value.strip().strip("`").strip()


def _first_contract_line(value: str) -> str:
    return value.splitlines()[0].strip() if value.splitlines() else ""


def _has_valid_iso_date(value: str) -> bool:
    for candidate in re.findall(r"(?<!\d)20\d{2}-\d{2}-\d{2}(?!\d)", value):
        try:
            date.fromisoformat(candidate)
        except ValueError:
            continue
        return True
    return False


def _rough_elapsed_range(value: str) -> tuple[float, float] | None:
    match = re.fullmatch(
        r"(?ix)\s*(?:about|approximately|roughly|approx\.?|约|大约|≈|~)?\s*"
        r"(?P<low>\d+(?:\.\d+)?)\s*(?:-|–|—|~|～|to|至|到)\s*"
        r"(?P<high>\d+(?:\.\d+)?)\s*"
        r"(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?|"
        r"business\s+days?|working\s+days?|"
        r"(?:个)?(?:工作日|工作天|秒|分钟|小时|天|周|月|年))\s*",
        _scalar_contract_value(value),
    )
    if not match:
        return None
    return float(match.group("low")), float(match.group("high"))


def _replace_inline_markdown_links(value: str) -> str:
    opening = re.compile(r"!?\[([^\]\n]+)\]\(")
    cursor = 0
    while match := opening.search(value, cursor):
        depth = 1
        index = match.end()
        while index < len(value) and depth:
            if value[index] == "\\":
                index += 2
                continue
            if value[index] == "(":
                depth += 1
            elif value[index] == ")":
                depth -= 1
            index += 1
        if depth:
            cursor = match.end()
            continue
        label = match.group(1)
        value = value[: match.start()] + label + value[index:]
        cursor = match.start() + len(label)
    return value


def _rendered_contract_fragment(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"\[([^\]]+)\]\s*\[[^\]]*\]", r"\1", value)
    value = _replace_inline_markdown_links(value)
    value = re.sub(r"!?(?:\[([^\]]+)\])\([^)]*\)", r"\1", value)
    value = re.sub(r"(?s)<[^>]*>", "", value)
    value = re.sub(r"[`*_~\[\]]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def _has_content_character(value: str) -> bool:
    return bool(re.search(r"[A-Za-z0-9\u3400-\u4dbf\u4e00-\u9fff]", value))


def _distribution_rows(value: str) -> tuple[list[str], list[str]]:
    valid: list[str] = []
    invalid: list[str] = []
    row_pattern = re.compile(
        r"(?i)^\s*[-*]\s*(?P<driver>\S.*?)\s+(?:—|–)\s+"
        r"(?P<band>Dominant|Material|Minor|Unknown|主导|显著|次要|未知)\s+"
        r"(?:—|–)\s+(?P<reason>\S.*?)\s*$"
    )
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = row_pattern.fullmatch(line)
        if not match:
            invalid.append(line)
            continue
        driver = _rendered_contract_fragment(match.group("driver")).casefold()
        reason = _rendered_contract_fragment(match.group("reason"))
        if (
            not _has_content_character(driver)
            or not _has_content_character(reason)
            or re.fullmatch(
                r"(?i)(?:tbd|unknown|n/?a|none|pending|待定|未知|无)",
                reason,
            )
        ):
            invalid.append(line)
            continue
        valid.append(driver)
    return valid, invalid


def _resolved_time_assessment_signal_count(value: str) -> int:
    fields = named_contract_fields(
        value,
        TIME_ASSESSMENT_LABELS,
        allow_indented_continuations=False,
    )
    count = sum(
        label in fields
        for label in (
            "Rough elapsed-time estimate",
            "Critical-path time-cost distribution",
        )
    )
    target = _scalar_contract_value(
        _first_contract_line(fields.get("Assessment target", ""))
    ).casefold()
    mode = _scalar_contract_value(
        _first_contract_line(fields.get("Assessment mode", ""))
    ).casefold()
    basis = _first_contract_line(fields.get("Basis or blocker", ""))
    return count + (target in {"ready-to-closed", "current-milestone-to-closed"}) + (
        mode in {"rough range", "distribution only"}
    ) + _has_valid_iso_date(basis)


def _matching_html_container_end(
    markdown_text: str,
    start: int,
    tag: str,
) -> int | None:
    token = re.compile(
        rf"(?is)<\s*(?P<closing>/)?\s*{re.escape(tag)}\b(?P<attrs>[^>]*)>"
    )
    depth = 1
    for match in token.finditer(markdown_text, start):
        if match.group("closing"):
            depth -= 1
            if depth == 0:
                return match.end()
        elif not re.search(r"/\s*$", match.group("attrs")):
            depth += 1
    return None


def _html_wrapped_time_assessment(markdown_text: str) -> bool:
    container_tags = {
        "article",
        "aside",
        "blockquote",
        "details",
        "dialog",
        "div",
        "fieldset",
        "figure",
        "footer",
        "form",
        "header",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "script",
        "section",
        "span",
        "style",
        "table",
        "tbody",
        "td",
        "template",
        "tfoot",
        "th",
        "thead",
        "tr",
        "ul",
    }
    void_tags = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
    opening = re.compile(
        r"(?is)<\s*(?P<tag>[A-Za-z][\w:-]*)\b(?P<attrs>[^>]*)>"
    )
    for match in opening.finditer(markdown_text):
        tag = match.group("tag")
        attrs = match.group("attrs")
        explicitly_hidden = bool(
            re.search(r"(?i)(?:^|\s)hidden(?:\s|=|$)", attrs)
            or re.search(r"(?i)aria-hidden\s*=\s*['\"]?true\b", attrs)
            or re.search(
                r"(?i)style\s*=\s*['\"][^'\"]*"
                r"(?:display\s*:\s*none|visibility\s*:\s*hidden)",
                attrs,
            )
        )
        if tag.casefold() in void_tags or re.search(r"/\s*$", attrs):
            continue
        closing_end = _matching_html_container_end(markdown_text, match.end(), tag)
        if closing_end is None and not (
            explicitly_hidden or tag.casefold() in container_tags
        ):
            continue
        end = closing_end if closing_end is not None else len(markdown_text)
        block = markdown_text[match.start() : end]
        if re.search(rf"(?im)^##\s+(?:{TIME_ASSESSMENT_HEADING})\s*$", block) or (
            _resolved_time_assessment_signal_count(block) >= 3
        ):
            return True
    return False


def preflight_time_assessment_mode(markdown_text: str) -> str | None:
    sections = h2_sections(markdown_text, TIME_ASSESSMENT_HEADING)
    if len(sections) != 1:
        return None
    fields = named_contract_fields(
        sections[0],
        TIME_ASSESSMENT_LABELS,
        allow_indented_continuations=False,
    )
    mode = _scalar_contract_value(fields.get("Assessment mode", "")).casefold()
    return mode if mode in {"rough range", "distribution only"} else None


def _time_assessment_signal_labels(markdown_text: str) -> set[str]:
    fields = named_contract_fields(
        markdown_text,
        TIME_ASSESSMENT_LABELS,
        allow_indented_continuations=False,
    )
    signals = {
        label
        for label in (
            "Rough elapsed-time estimate",
            "Critical-path time-cost distribution",
        )
        if label in fields
    }
    target = _scalar_contract_value(
        _first_contract_line(fields.get("Assessment target", ""))
    ).casefold()
    if target in {"ready-to-closed", "current-milestone-to-closed"}:
        signals.add("Assessment target")
    mode = _scalar_contract_value(
        _first_contract_line(fields.get("Assessment mode", ""))
    ).casefold()
    if mode in {"rough range", "distribution only"}:
        signals.add("Assessment mode")
    basis = _first_contract_line(fields.get("Basis or blocker", ""))
    if _has_valid_iso_date(basis):
        signals.add("Basis or blocker")
    return signals


def preflight_time_assessment_errors(
    markdown_text: str,
    *,
    raw_markdown_text: str | None = None,
) -> list[str]:
    hidden_errors: list[str] = []
    if raw_markdown_text is not None:
        contract_raw = strip_placeholder_example_blocks(raw_markdown_text)
        raw_sections = h2_sections(contract_raw, TIME_ASSESSMENT_HEADING)
        visible_sections = h2_sections(markdown_text, TIME_ASSESSMENT_HEADING)
        resolved_hidden_section = any(
            _resolved_time_assessment_signal_count(section) >= 3
            for section in raw_sections
        ) and len(raw_sections) > len(visible_sections)
        html_scan_text = re.sub(
            r"(?s)<!--.*?(?:-->|\Z)",
            "",
            strip_fenced_blocks(contract_raw),
        )
        if resolved_hidden_section or _html_wrapped_time_assessment(html_scan_text):
            hidden_errors.append(
                "Preflight Time Assessment must be visible Markdown, not hidden in "
                "a fence, comment, or HTML element"
            )

    sections = h2_sections(markdown_text, TIME_ASSESSMENT_HEADING)
    if not sections:
        if _time_assessment_signal_labels(markdown_text):
            return hidden_errors + [
                "Preflight Time Assessment fields must be inside exactly one "
                "Preflight Time Assessment section"
            ]
        return hidden_errors

    errors: list[str] = hidden_errors
    if len(sections) != 1:
        errors.append("Preflight Time Assessment must appear exactly once")
    field_counts = named_contract_field_counts(sections[0], TIME_ASSESSMENT_LABELS)
    for label, count in field_counts.items():
        if count > 1:
            errors.append(f"duplicate Preflight Time Assessment field: {label}")
    outside_signals = _time_assessment_signal_labels(
        without_h2_sections(markdown_text, TIME_ASSESSMENT_HEADING)
    )
    for label in sorted(outside_signals):
        errors.append(
            f"Preflight Time Assessment field appears outside its section: {label}"
        )
    fields = named_contract_fields(
        sections[0],
        TIME_ASSESSMENT_LABELS,
        allow_indented_continuations=False,
    )
    for label in TIME_ASSESSMENT_LABELS:
        if not _scalar_contract_value(fields.get(label, "")):
            errors.append(f"missing Preflight Time Assessment field: {label}")

    target = _scalar_contract_value(fields.get("Assessment target", "")).casefold()
    if target and target not in {"ready-to-closed", "current-milestone-to-closed"}:
        errors.append(
            "Assessment target must be Ready-to-Closed or current-milestone-to-Closed"
        )

    mode = _scalar_contract_value(fields.get("Assessment mode", "")).casefold()
    if mode and mode not in {"rough range", "distribution only"}:
        errors.append("Assessment mode must be Rough range or Distribution only")

    basis = _scalar_contract_value(fields.get("Basis or blocker", ""))
    if basis:
        if not _has_valid_iso_date(basis):
            errors.append("Basis or blocker must include a valid YYYY-MM-DD as-of date")
        basis_detail = _rendered_contract_fragment(re.sub(
            r"(?<!\d)20\d{2}-\d{2}-\d{2}(?!\d)", "", basis
        )).strip(
            " \t\r\n:;,.—-"
        )
        if not _has_content_character(basis_detail) or re.fullmatch(
            r"(?i)(?:tbd|unknown|n/?a|none|pending|待定|未知|无)", basis_detail
        ):
            errors.append("Basis or blocker must record concrete evidence or a blocker")

    estimate = _scalar_contract_value(
        fields.get("Rough elapsed-time estimate", "")
    )
    distribution = fields.get("Critical-path time-cost distribution", "").strip()
    if mode == "rough range":
        parsed_range = _rough_elapsed_range(estimate)
        if parsed_range is None:
            errors.append(
                "Rough range mode requires a low-high elapsed-time range with one unit"
            )
        elif parsed_range[0] >= parsed_range[1]:
            errors.append("Rough elapsed-time range must increase from low to high")
        normalized_distribution = _scalar_contract_value(distribution).rstrip(".").casefold()
        if normalized_distribution != "not required: rough range recorded":
            errors.append(
                "Rough range mode requires distribution: Not required: rough range recorded."
            )
    elif mode == "distribution only":
        if estimate.casefold() != "not quickly estimable":
            errors.append(
                "Distribution only mode requires estimate: Not quickly estimable"
            )
        if re.search(r"(?:—|–)\s*\d+(?:\.\d+)?%\s*(?:—|–)", distribution):
            errors.append(
                "Distribution only mode requires relative bands, not unmeasured percentages"
            )
        rows, invalid_rows = _distribution_rows(distribution)
        if invalid_rows:
            errors.append(
                "Critical-path distribution rows must use: "
                "- driver — Dominant/Material/Minor/Unknown — reason"
            )
        if len(set(rows)) < 2:
            errors.append(
                "Distribution only mode requires at least two concrete critical-path drivers"
            )

    return errors


def normalize_contractions(value: str) -> str:
    value = re.sub(r"(?i)\b(?:cannot|won['’]t)\b", " not", value)
    return re.sub(
        r"(?i)\b(?:was|were|is|are|has|have|had|could|would|should|did|does|do|ca)n['’]t\b",
        " not",
        value,
    )


def clauses(value: str) -> list[str]:
    return [
        part.strip()
        for part in re.split(
            r"(?i)[,.;\n]+|\band\b|\bbut\b|\bhowever\b",
            normalize_contractions(value),
        )
        if part.strip()
    ]


def clause_is_negated(value: str) -> bool:
    return bool(
        re.search(
            r"(?i)\b(?:no|not|never|without|cannot|forbid(?:den)?|"
            r"prohibit(?:ed)?|disallow(?:ed)?)\b",
            value,
        )
    )


def boundary_has_affirmative_watcher_action(value: str) -> bool:
    for clause in clauses(value):
        if not re.search(r"(?i)\bwatcher:housekeeping\b", clause):
            continue
        if re.search(
            r"(?i)\b(?:no|not|never|without)\b[^.;]{0,40}"
            r"(?:\bwatcher:housekeeping\b|\b(?:use|invoke|run|call|apply)\w*\b)|"
            r"\bwatcher:housekeeping\b[^.;]{0,40}"
            r"\b(?:no|not|never|prohibit(?:ed)?|forbid(?:den)?|disabled)\b",
            clause,
        ):
            continue
        if re.search(
            r"(?i)\b(?:use[sd]?|using|invoke[sd]?|run|runs|ran|call(?:s|ed)?|apply|applies)\b",
            clause,
        ):
            return True
    return False


def watcher_evidence_has_negative_status(value: str) -> bool:
    for clause in clauses(value):
        if not re.search(r"(?i)\bwatcher:housekeeping\b", clause):
            continue
        if re.search(
            r"(?i)(?:\bno\b[^.;]{0,12}\bwatcher:housekeeping\b[^.;]{0,25}"
            r"\b(?:action|invocation|execution|run|use[sd]?)\b|"
            r"\b(?:not|never)\b[^.;]{0,35}\b(?:use|invoke|run|execute)\w*\b"
            r"[^.;]{0,25}\bwatcher:housekeeping\b|"
            r"\bwithout\b[^.;]{0,25}\bwatcher:housekeeping\b)",
            clause,
        ):
            return True
        if re.search(
            r"(?i)\bwatcher:housekeeping\b[^A-Za-z0-9]{0,5}"
            r"(?:(?:was|is|remained)\s+)?"
            r"(?:unavailable|missing|failed|skipped|absent|bypassed|omitted|replaced)\b|"
            r"\bwatcher:housekeeping\b[^.;]{0,45}"
            r"\b(?:did\s+not|was\s+not|is\s+not|not|never)\b[^.;]{0,25}"
            r"\b(?:run|invoked|executed|used|occurred)\b|"
            r"\bwatcher:housekeeping\b[^.;]{0,35}"
            r"\b(?:only\s+planned|status(?:\s+was|\s+is|\s*[:=])?\s+unknown)\b",
            clause,
        ):
            return True
    return False


def boundary_permits_unbounded_deletion(value: str) -> bool:
    for clause in clauses(value):
        if clause_is_negated(clause):
            continue
        if re.search(r"(?i)\b(?:raw\s+recursive|recursive\s+delet)", clause):
            return True
        permission = r"(?:allow(?:ed|s)?|permit(?:ted|s)?|may|can|will)"
        deletion = r"(?:delete[sd]?|deletion|remove[sd]?|clean(?:ed|up)?|purge[sd]?)"
        if re.search(
            rf"(?i)(?:\b{permission}\b[^.;]{{0,60}}\b{deletion}\b|"
            rf"\b{deletion}\b[^.;]{{0,60}}\b{permission}\b)",
            clause,
        ):
            return True
    return False


def concrete_owner_root_entries(value: str) -> tuple[list[str], list[str]]:
    paths: list[str] = []
    invalid_entries: list[str] = []
    owner_label = (
        r"(?:goal|sequence|task)[- ]owned|owner[- ]specific|"
        r"目标专属|序列专属|任务专属"
    )
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.fullmatch(
            rf"(?i)(?:[-*]\s*)?(?:{owner_label})\s*[:：=]\s*(?P<path>.+?)\s*",
            line,
        )
        if not match:
            invalid_entries.append(line)
            continue
        path = match.group("path").strip()
        if len(path) >= 2 and (path[0], path[-1]) in {
            ("`", "`"),
            ('"', '"'),
            ("'", "'"),
        }:
            path = path[1:-1].strip()
        paths.append(path)
    return paths, invalid_entries


def normalized_absolute_owner_root(value: str) -> tuple[str | None, list[str]]:
    """Return a lexical absolute path and any contract violations.

    This deliberately validates the recorded string rather than resolving it on the
    checker host: a Windows goal must remain checkable on POSIX and vice versa.
    """

    errors: list[str] = []
    if re.search(
        r"(?i)%[A-Z_][A-Z0-9_]*%|\$\{?[A-Z_][A-Z0-9_]*\}?|"
        r"\b(?:gettempdir|os\.tmpdir|TBD|pending)\b|待解析|待记录",
        value,
    ):
        errors.append("unresolved")

    windows_path = bool(re.match(r"(?i)^[A-Z]:[\\/]", value) or value.startswith("\\\\"))
    path_module = ntpath if windows_path else posixpath
    segments = re.split(r"[\\/]" if windows_path else r"/", value)
    if any(segment in {".", ".."} for segment in segments):
        errors.append("dot-segment")

    if not path_module.isabs(value):
        errors.append("not-absolute")
        return None, errors

    normalized = path_module.normpath(value)
    if windows_path:
        drive, tail = ntpath.splitdrive(normalized)
        if drive and tail in {"", "\\", "/"}:
            errors.append("root")
        normalized = normalized.replace("\\", "/")
    elif normalized == "/":
        errors.append("root")

    return normalized, errors


def boundary_expands_child_policy(value: str) -> bool:
    """Recognize affirmative parent attempts to widen into child-owned policy."""

    for clause in clauses(value):
        if clause_is_negated(clause):
            continue
        if re.search(
            r"(?i)\b(?:override|inherit|widen|clean|include|cover|process|handle|"
            r"delete|remove)\w*\b[^.;]{0,80}\bchild(?:[- ]owned)?\b|"
            r"\bchild(?:[- ]owned)?\b[^.;]{0,80}"
            r"\b(?:overridden|inherited|widened|cleaned|included|covered|processed|"
            r"handled|deleted|removed)\b",
            clause,
        ):
            return True
    return False


def housekeeping_evidence_block(section_text: str) -> str | None:
    match = re.search(
        r"(?ims)^\s*(?:\d+\.\s*)?(?:Temporary cache\s*/\s*"
        r"housekeeping evidence|任务临时缓存(?:\s*/\s*housekeeping)?\s*证据)"
        r"\s*[:：]\s*(?P<evidence>\S.*?)"
        r"(?=^\s*(?:\d+\.\s*)?(?:Checkpoint evidence|检查点证据)"
        r"\s*[:：]|\Z)",
        section_text,
    )
    return match.group("evidence").strip() if match else None


def milestone_sections(markdown_text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    for match in re.finditer(
        r"(?ims)^#{2,3}\s+(?P<name>M\d+)\b[^\n]*\n"
        r"(?P<body>.*?)(?=^#{1,3}\s+|\Z)",
        markdown_text,
    ):
        sections.setdefault(match.group("name").casefold(), []).append(match.group("body"))
    return sections


def milestone_section_statuses(sections: dict[str, str]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for name, body in sections.items():
        status_match = re.search(
            r"(?im)^(?:Status|状态)\s*[:：]\s*`?([^`\n]+)`?\s*$",
            body,
        )
        if status_match:
            statuses[name] = status_match.group(1).strip()
    return statuses


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("goal_file", type=Path)
    parser.add_argument(
        "--allow-draft",
        action="store_true",
        help="Allow Draft status while still checking placeholders and structure.",
    )
    args = parser.parse_args()

    path = args.goal_file
    if not path.exists():
        print(f"missing goal file: {path}", file=sys.stderr)
        return 1

    text = path.read_text(encoding="utf-8")
    visible_text = re.sub(
        r"(?s)<!--.*?(?:-->|\Z)",
        "",
        strip_fenced_blocks(text),
    )
    errors: list[str] = []
    overall_statuses = re.findall(
        r"(?im)^(?:overall status|整体状态|goal status|目标状态)\s*[:：]\s*`?([^`\n]+)`?\s*$",
        visible_text,
    )
    normalized_overall_statuses = [status.strip().lower() for status in overall_statuses]

    errors.extend(placeholder_errors(text))

    required_patterns = {
        "M0 milestone": r"\bM0\b",
        "review gate": r"(?i)\breview\s*gate\b|Review gate|评审|验收",
        "checkpoint evidence": r"(?i)\bcheckpoint\b|检查点",
        "checkpoint component": r"(?i)\bcheckpoint\s+component\b|components/checkpoint\.md",
        "planning preflight": r"(?i)\bplanning\s+preflight\b|components/planning-preflight\.md|grill-with-docs",
        "rollback path": r"(?i)\brollback\b|回滚",
        "close/archive procedure": r"(?i)\b(close|archive)\b|关闭|归档",
        "validation evidence": r"(?i)\b(validation|verify|test)\b|验证|测试",
        "failure handling": r"(?i)\b(fail|failure|breakpoint|blocked)\b|失败|断点|阻塞",
        "continuation contract": r"(?i)\bcontinuation\s+contract\b|Continuation contract|继续执行的关键约束",
        "pre-approval boundary": r"(?im)^##\s+Pre-Approval\s*/\s*YOLO\b",
        "runtime hard stops": r"(?i)\bruntime\s+hard\s*stops?\b|运行时硬停止",
        "non-stops": r"(?i)\bnon[- ]?stops?\b|不应中断",
        "reusable prompt": r"(?i)\b(prompt)\b|推荐.*Prompt",
    }
    errors.extend(
        missing_required_pattern_errors(
            visible_text,
            required_patterns,
            message="missing required section signal",
        )
    )

    harness = h2_section(visible_text, r"Loop Blueprint\s*/\s*Harness(?:\s+边界)?")
    if harness is None:
        errors.append("missing Loop Blueprint / Harness section")
    else:
        execution_mode_match = re.search(
            r"(?im)^(?:Execution mode|执行模式)\s*[:：]\s*`?([^`\n]+)`?\s*$",
            harness,
        )
        if not execution_mode_match:
            errors.append("missing execution mode in Loop Blueprint / Harness section")
        else:
            execution_mode = execution_mode_match.group(1).strip().casefold()
            if execution_mode not in {
                "manual staged execution",
                "loop-shaped execution",
                "automated loop",
            }:
                errors.append(
                    "execution mode must be Manual staged execution, "
                    "Loop-shaped execution, or Automated loop"
                )
            elif execution_mode == "manual staged execution":
                opt_out = re.search(
                    r"(?is)Not applicable\s*:\s*manual staged execution(?P<reason>.*)$",
                    harness,
                )
                reason = (
                    opt_out.group("reason").strip(" \t\r\n:;,.—-") if opt_out else ""
                )
                if len(reason) < 10:
                    errors.append("manual harness opt-out requires a reason")
                if re.search(
                    r"(?i)\b(?:uses?|requires?|reads?\s+from|writes?\s+to)\s+"
                    r"(?:the\s+)?(?:[A-Za-z0-9_.-]+\s+)?connector\b|"
                    r"\bconnector-backed\b",
                    visible_text,
                ):
                    errors.append(
                        "goal declares connector use but Loop harness is Not applicable"
                    )
                if re.search(
                    r"(?i)\b(?:uses?|requires?|orchestrates?)\s+"
                    r"(?:(?:parallel|multiple)\s+)?(?:worktrees?|sub-?agents?)\b|"
                    r"\b(?:runs?|uses?|requires?)\s+(?:an?\s+)?"
                    r"(?:automated|recurring)\s+(?:loop|trigger|schedule)\b",
                    visible_text,
                ):
                    errors.append(
                        "goal declares Loop-shaped orchestration but harness is Not applicable"
                    )
            else:
                harness_fields = {
                    "Trigger": r"Trigger",
                    "Inputs": r"Inputs",
                    "Triage and orchestration": r"Triage\s+and\s+orchestration",
                    "Worktree and isolation": r"Worktree\s+and\s+isolation",
                    "Skills and context": r"Skills\s+and\s+context",
                    "Connector read/write boundaries": r"Connector\s+read/write\s+boundaries",
                    "Independent verification": r"Independent\s+verification",
                    "Runtime hard stops": r"Runtime\s+hard\s+stops",
                    "Durable learning": r"Durable\s+learning",
                }
                harness_values = named_contract_fields(harness, harness_fields)
                for label in harness_fields:
                    if label not in harness_values:
                        errors.append(
                            f"Loop-shaped goal is missing harness field: {label}"
                        )
                    elif not harness_values[label].strip(" \t\r\n-*"):
                        errors.append(
                            f"Loop-shaped goal has empty harness field: {label}"
                        )

    approval = h2_section(visible_text, r"Pre-Approval\s*/\s*YOLO(?:\s+边界)?")
    if approval is None:
        errors.append("missing Pre-Approval / YOLO section")
    else:
        approval_labels = {
            "Pre-approved YOLO local operations": r"Pre-approved\s+YOLO\s+local\s+operations",
            "Pre-approved external reads/writes": r"Pre-approved\s+external\s+reads/writes",
            "Runtime hard stops": r"Runtime\s+hard\s+stops",
            "Non-stops": r"Non-stops",
        }
        approval_fields = named_contract_fields(approval, approval_labels)
        for label in approval_labels:
            if not approval_fields.get(label):
                errors.append(f"missing Pre-Approval / YOLO field: {label}")

        local_operations = approval_fields.get(
            "Pre-approved YOLO local operations", ""
        )
        normalized_local_operations = re.sub(
            r"(?i)non[- ]destructive", "", local_operations
        )
        unsafe_local_pattern = re.compile(
            r"(?i)\b(?:delete\s+production|drop\s+(?:database|table)|destroy|"
            r"irreversible|privacy[- ]sensitive|publish|deploy\s+to|"
            r"send\b.*\bmessage|external\s+(?:write|message)|post\s+to)\b"
        )
        if (
            not re.search(r"(?i)\bnon[- ]destructive\b", local_operations)
            or not re.search(r"(?i)\blocal\b", local_operations)
            or unsafe_local_pattern.search(normalized_local_operations)
        ):
            errors.append("YOLO local operations must be non-destructive and local")

        external_approvals = approval_fields.get(
            "Pre-approved external reads/writes", ""
        )
        document_is_draft = bool(normalized_overall_statuses) and set(
            normalized_overall_statuses
        ) == {"draft"}
        if re.search(
            r"(?i)\b(?:pending approval|approval pending|TBD|to be decided|"
            r"unapproved|needs? approval|awaiting (?:user )?approval)\b",
            external_approvals,
        ) and not document_is_draft:
            errors.append("unresolved external write approval keeps the goal Draft")

        hard_stops = approval_fields.get("Runtime hard stops", "")
        for line in hard_stops.splitlines():
            for clause in re.split(
                r"(?i)[;。]|，\s*(?=但)|,\s*(?=(?:but|however)\b)|\.(?=\s|$)",
                line,
            ):
                if re.search(
                    r"(?i)\b(?:not|never|isn't|is not|do not)\b", clause
                ):
                    continue
                recoverable = re.search(
                    r"(?i)\b(?:milestone boundary|checkpoint|rebuild|refresh|reinstall|"
                    r"review gate|first\s+(?:failed\s+)?validation|"
                    r"first\s+validation\s+failure)\b",
                    clause,
                )
                if recoverable:
                    errors.append(
                        "runtime hard stop misclassifies recoverable work: "
                        + recoverable.group(0)
                    )
                    break
            else:
                continue
            break

    states = milestone_states(visible_text)
    if not states:
        errors.append("missing milestone status table")
    close_rows = [state for state in states if state.name.casefold() == "close"]
    milestone_rows = [item for item in states if item.name.casefold() != "close"]
    if states and len(close_rows) != 1:
        errors.append("milestone status table must contain exactly one Close row")
    for state in states:
        if state.status.casefold() not in {
            "ready",
            "not started",
            "in progress",
            "blocked",
            "done",
        }:
            errors.append(f"{state.name} has invalid milestone status {state.status}")
        if state.review.casefold() not in {"pending", "passed", "failed"}:
            errors.append(f"{state.name} has invalid Review status {state.review}")
        if state.checkpoint.casefold() not in {"pending", "done"}:
            errors.append(f"{state.name} has invalid Checkpoint status {state.checkpoint}")
        if state.review.casefold() == "failed" and state.status.casefold() not in {
            "in progress",
            "blocked",
        }:
            errors.append(
                f"{state.name} Review Failed requires milestone status In Progress or Blocked"
            )
        if state.status.casefold() != "done":
            if state.review.casefold() == "passed" or state.checkpoint.casefold() == "done":
                errors.append(
                    f"{state.name} Review/Checkpoint completion requires milestone status Done"
                )
            continue
        if state.review.casefold() != "passed":
            errors.append(
                f"{state.name} status Done requires Review Passed; found {state.review}"
            )
        if state.checkpoint.casefold() != "done":
            errors.append(
                f"{state.name} status Done requires Checkpoint Done; found {state.checkpoint}"
            )

    section_groups = milestone_sections(visible_text)
    for name, bodies in section_groups.items():
        if len(bodies) > 1:
            errors.append(f"duplicate milestone sections: {name.upper()}")
    section_bodies = {name: bodies[0] for name, bodies in section_groups.items()}
    table_ids = {state.name.casefold() for state in milestone_rows}
    section_ids = set(section_groups)
    if "m0" not in table_ids:
        errors.append("milestone status table must include M0")
    for name in sorted(table_ids - section_ids):
        errors.append(f"milestone table has no matching section: {name.upper()}")
    for name in sorted(section_ids - table_ids):
        errors.append(f"milestone section has no matching table row: {name.upper()}")

    section_statuses = milestone_section_statuses(section_bodies)
    for state in states:
        section_status = section_statuses.get(state.name.casefold())
        if section_status and section_status.casefold() != state.status.casefold():
            errors.append(
                f"{state.name} status disagrees between section and milestone table: "
                f"{section_status} != {state.status}"
            )
        if state.status.casefold() == "blocked":
            if state.name.casefold() == "close":
                section_body = h2_section(visible_text, r"Close Gate|关闭门") or ""
            else:
                section_body = section_bodies.get(state.name.casefold(), "")
            if not re.search(
                r"(?im)^(?:Runtime hard-stop evidence|运行时硬停止证据)\s*[:：]\s*\S",
                section_body,
            ):
                errors.append(
                    f"{state.name} Blocked requires section-local runtime hard-stop evidence"
                )

    first_incomplete: MilestoneState | None = None
    milestone_numbers = [int(state.name[1:]) for state in milestone_rows]
    duplicate_numbers = sorted(
        number for number in set(milestone_numbers) if milestone_numbers.count(number) > 1
    )
    if duplicate_numbers:
        errors.append(
            "duplicate milestone rows: "
            + ", ".join(f"M{number}" for number in duplicate_numbers)
        )
    elif milestone_numbers:
        missing_numbers = sorted(set(range(max(milestone_numbers) + 1)) - set(milestone_numbers))
        if missing_numbers:
            errors.append(
                "milestone sequence must be contiguous from M0; missing "
                + ", ".join(f"M{number}" for number in missing_numbers)
            )
        elif milestone_numbers != sorted(milestone_numbers):
            errors.append("milestone rows must be ordered from M0")
    for state in milestone_rows:
        normalized_status = state.status.casefold()
        if normalized_status == "done" and first_incomplete:
            errors.append(
                "milestone order invalid: Done milestone "
                f"{state.name} follows incomplete {first_incomplete.name}"
            )
        elif normalized_status != "done":
            if first_incomplete and normalized_status in {
                "ready",
                "in progress",
                "blocked",
            }:
                errors.append(
                    f"milestone order invalid: {state.name} {state.status} "
                    f"requires {first_incomplete.name} Done"
                )
            first_incomplete = first_incomplete or state

    current_rows = [
        state
        for state in states
        if state.status.casefold() in {"ready", "in progress", "blocked"}
    ]
    if len(current_rows) > 1:
        errors.append(
            "multiple current milestones: "
            + ", ".join(f"{state.name} {state.status}" for state in current_rows)
        )

    if close_rows and close_rows[0].status.casefold() in {
        "ready",
        "in progress",
        "blocked",
        "done",
    }:
        incomplete_milestones = [
            state.name for state in milestone_rows if state.status.casefold() != "done"
        ]
        if incomplete_milestones:
            errors.append(
                f"Close {close_rows[0].status} requires all milestones Done; incomplete: "
                + ", ".join(incomplete_milestones)
            )

    marker: str | None = None
    marker_match = re.search(
        r"(?im)^Planning preflight marker\s*[:：]\s*`?([^`\n]+)`?\s*$",
        visible_text,
    )
    if not marker_match:
        if not args.allow_draft:
            errors.append("missing planning preflight marker field")
    else:
        marker = marker_match.group(1).strip()
        marker_pattern = re.compile(
            r"^preflight:[A-Za-z0-9_.-]+:(?:skip:)?[0-9]{8}-[A-Za-z0-9_.-]+$"
        )
        if not marker_pattern.match(marker):
            errors.append(
                "planning preflight marker must be a non-placeholder id like "
                "preflight:<goal_slug>:<yyyymmdd>-<short-id> or "
                "preflight:<goal_slug>:skip:<yyyymmdd>-<short-id>"
            )

    preflight_status: str | None = None
    status_match = re.search(
        r"(?im)^Planning preflight status\s*[:：]\s*`?([^`\n]+)`?\s*$",
        visible_text,
    )
    if not status_match:
        if not args.allow_draft:
            errors.append("missing planning preflight status field")
    else:
        preflight_status = status_match.group(1).strip().lower()
        valid_statuses = {
            "done",
            "skipped by explicit user instruction",
        }
        if preflight_status not in valid_statuses:
            errors.append(
                "planning preflight status must be Done or Skipped by explicit user instruction"
            )

    if marker and preflight_status:
        marker_is_skip = ":skip:" in marker
        status_is_skip = preflight_status == "skipped by explicit user instruction"
        if marker_is_skip and not status_is_skip:
            errors.append(
                "preflight skip marker requires status Skipped by explicit user instruction"
            )
        elif status_is_skip and not marker_is_skip:
            errors.append("skipped preflight status requires a :skip: marker")

    source_match = re.search(
        r"(?im)^Preflight source\s*[:：]\s*`?([^`\n]+)`?\s*$",
        visible_text,
    )
    preflight_source = source_match.group(1).strip().casefold() if source_match else None
    if not preflight_source:
        if not args.allow_draft:
            errors.append("missing planning preflight source field")
    elif marker and preflight_status:
        if ":skip:" in marker and not preflight_source.startswith("user skip"):
            errors.append("skipped preflight requires source user skip")
        elif ":skip:" not in marker and preflight_source != "grill-with-docs":
            errors.append("completed preflight requires source grill-with-docs")

    if args.allow_draft and any((marker_match, status_match, source_match)) and not all(
        (marker_match, status_match, source_match)
    ):
        if not marker_match:
            errors.append("missing planning preflight marker field")
        if not status_match:
            errors.append("missing planning preflight status field")
        if not source_match:
            errors.append("missing planning preflight source field")

    errors.extend(
        preflight_time_assessment_errors(
            visible_text,
            raw_markdown_text=text,
        )
    )

    temporary_cache_section = h2_section(
        visible_text,
        r"Task Temporary Cache\s*/\s*Housekeeping|任务临时缓存(?:\s*/\s*Housekeeping)?",
    )
    temporary_cache_policy: str | None = None
    recorded_roots = ""
    recorded_roots_state: str | None = None
    recorded_root_paths: list[str] = []
    if temporary_cache_section is not None:
        temporary_cache_labels = {
            "Close housekeeping policy": r"Close\s+housekeeping\s+policy|关闭清理策略",
            "Housekeeping decision source": r"Housekeeping\s+decision\s+source|清理决策来源",
            "Task temporary cache root strategy": (
                r"Task\s+temporary\s+cache\s+root\s+strategy|任务临时缓存根目录策略"
            ),
            "Recorded task temporary cache roots": (
                r"Recorded\s+task\s+temporary\s+cache\s+roots|已记录的任务临时缓存根目录"
            ),
            "Housekeeping boundary": r"Housekeeping\s+boundary|清理边界",
        }
        temporary_cache_fields = named_contract_fields(
            temporary_cache_section,
            temporary_cache_labels,
        )
        for label in temporary_cache_labels:
            if not temporary_cache_fields.get(label):
                errors.append(f"missing Task Temporary Cache / Housekeeping field: {label}")

        policy_value = temporary_cache_fields.get("Close housekeeping policy", "")
        temporary_cache_policy = policy_value.strip().strip("`").strip().casefold()
        allowed_policies = {"enabled", "disabled", "not applicable"}
        if temporary_cache_policy not in allowed_policies:
            errors.append(
                "Close housekeeping policy must be Enabled, Disabled, or Not applicable"
            )

        unresolved_pattern = re.compile(
            r"(?i)\b(?:pending|TBD|to be decided|awaiting (?:user )?(?:choice|decision))\b|"
            r"待确认|未决定|待选择"
        )
        for label, value in temporary_cache_fields.items():
            if unresolved_pattern.search(value):
                errors.append(f"unresolved Task Temporary Cache / Housekeeping field: {label}")

        decision_source = temporary_cache_fields.get("Housekeeping decision source", "")
        normalized_decision_source = normalize_contractions(decision_source)
        negated_or_inferred_decision = re.search(
            r"(?i)\b(?:no|not|without)\s+(?:an?\s+)?explicit(?:ly)?\s+user\s+confirmation\b|"
            r"\b(?:no|not|never|without)\b[^.;\n]{0,100}"
            r"\bexplicit(?:ly)?\s+user\s+confirmation\b|"
            r"\b(?:never|not)\s+(?:received|obtained|recorded|got)\s+"
            r"(?:an?\s+)?explicit(?:ly)?\s+user\s+confirmation\b|"
            r"\b(?:not|never)\s+explicitly\s+confirmed\s+by\s+(?:the\s+)?user\b|"
            r"\bexplicit(?:ly)?\s+user\s+confirmation\b[^.\n;]{0,100}"
            r"\b(?:no|not|never|absent|missing|unavailable)\b|"
            r"\b(?:inferred|defaulted|derived|assumed|declined|refused|withdrawn|"
            r"revoked)\b|"
            r"未(?:获得|取得|经过)用户(?:显式|明确)?(?:确认|选择)|未经用户(?:确认|选择)",
            normalized_decision_source,
        )
        positive_decision = re.search(
            r"(?i)\bexplicit(?:ly)?\s+user\s+confirmation\b"
            r"(?:\s+(?:was|is|has\s+been|had\s+been))?\s+"
            r"(?:obtained|recorded|received|given|provided)\b|"
            r"\bconfirmed\s+explicitly\s+by\s+(?:the\s+)?user\b|"
            r"\buser\s+explicitly\s+(?:confirmed|selected|chose)\b|"
            r"用户(?:显式|明确)(?:确认|选择)",
            decision_source,
        )
        if decision_source and (negated_or_inferred_decision or not positive_decision):
            errors.append(
                "Housekeeping decision source must record non-negated explicit user confirmation"
            )

        root_strategy = temporary_cache_fields.get(
            "Task temporary cache root strategy", ""
        )
        hardcoded_shared_root = re.search(
            r"(?i)(?<![A-Za-z0-9:])(?:/[^\s,;`]+|[A-Za-z]:[\\/]|\\\\|"
            r"%[A-Z_][A-Z0-9_]*%|\$\{?[A-Z_][A-Z0-9_]*\}?)|"
            r"共享(?:系统)?临时根目录(?:本身)?",
            root_strategy,
        )
        resolver_strategy = bool(
            re.search(r"(?i)\b(?:host|platform|runtime)\b|宿主|平台|运行时", root_strategy)
            and re.search(
                r"(?i)\b(?:goal|sequence|task)[- ]owned\b|\bowner[- ]specific\b|"
                r"目标专属|序列专属|任务专属",
                root_strategy,
            )
            and re.search(
                r"(?i)\b(?:beneath|under|within|inside)\b|\bchild\s+of\b|"
                r"\bsub(?:directory|ordinate)\s+(?:of|to)\b|位于.+(?:之下|内部)|子目录|下层命名空间",
                root_strategy,
            )
            and not hardcoded_shared_root
        )
        no_root_strategy = bool(
            re.search(
                r"(?i)\b(?:not applicable|no)\b[^.\n]{0,80}"
                r"\b(?:temporary\s+cache\s+)?roots?\b[^.\n]{0,30}"
                r"\b(?:created|used|needed)\b|不适用|不(?:会|需).*(?:创建|使用).*(?:临时缓存)?根目录",
                root_strategy,
            )
        )
        if root_strategy and not (
            resolver_strategy
            or (temporary_cache_policy == "not applicable" and no_root_strategy)
        ):
            errors.append(
                "Task temporary cache root strategy must use a host platform/runtime "
                "resolver and an owner-specific namespace beneath the resolved root"
            )

        boundary = temporary_cache_fields.get("Housekeeping boundary", "")
        boundary_has_watcher = bool(re.search(r"(?i)\bwatcher:housekeeping\b", boundary))
        affirmative_boundary_watcher = boundary_has_affirmative_watcher_action(boundary)
        if temporary_cache_policy == "enabled":
            if not boundary_has_watcher or not affirmative_boundary_watcher:
                errors.append(
                    "Enabled housekeeping requires watcher:housekeeping in the boundary"
                )
            if not (
                re.search(r"(?i)\binventor(?:y|ied|ize|ized)\b|盘点", boundary)
                and re.search(
                    r"(?i)\b(?:goal|sequence|task)[- ]owned\b|\bowner[- ]specific\b|"
                    r"目标专属|序列专属|任务专属",
                    boundary,
                )
                and re.search(
                    r"(?i)\b(?:disposable|discardable)\b|(?:确认|已确认).*(?:可丢弃|可清理)",
                    boundary,
                )
            ):
                errors.append(
                    "Enabled housekeeping boundary must limit watcher:housekeeping to "
                    "inventoried owner-specific disposable candidates"
                )
        elif temporary_cache_policy == "disabled":
            if affirmative_boundary_watcher or not re.search(
                r"(?i)\b(?:preserv(?:e|ed|ing)|retain(?:ed|ing)?)\b|保留",
                boundary,
            ):
                errors.append(
                    "Disabled housekeeping boundary must retain recorded roots without cleanup"
                )
        elif temporary_cache_policy == "not applicable":
            if affirmative_boundary_watcher or not re.search(
                r"(?i)\bno\b[^.\n]{0,60}\b(?:temporary\s+cache\s+)?roots?\b"
                r"[^.\n]{0,30}\b(?:created|used|needed)\b|不适用|"
                r"不(?:会|需).*(?:创建|使用).*(?:临时缓存)?根目录",
                boundary,
            ):
                errors.append(
                    "Not applicable housekeeping boundary must record that no roots are created"
                )

        if boundary_permits_unbounded_deletion(boundary):
            errors.append(
                "Housekeeping boundary must not permit raw, unbounded, or policy-conflicting "
                "deletion"
            )

        is_sequence_parent = bool(
            re.search(
                r"(?im)^Promotion policy\s*[:：]\s*`?automatic-after-close`?\s*$",
                visible_text,
            )
            and h2_section(visible_text, r"Child Execution Register") is not None
        )
        if is_sequence_parent and boundary_expands_child_policy(boundary):
            errors.append(
                "sequence parent housekeeping boundary must not inherit, widen, or override "
                "child policy"
            )

        recorded_roots = temporary_cache_fields.get(
            "Recorded task temporary cache roots", ""
        ).strip()
        scalar_wrapper = r"`?{}(?:[.]?)`?"
        not_applicable_state = r"(?:not applicable|不适用)"
        none_created_state = (
            r"(?:(?:none|no roots?)\s+(?:were\s+)?created|"
            r"no task temporary cache roots?|(?:未创建|没有创建).*(?:临时缓存)?根目录)"
        )
        deferred_state = (
            r"(?:resolve\s+and\s+record\s+before\s+first\s+use|"
            r"(?:首次使用前|在首次使用前).*(?:解析|记录))"
        )
        if re.fullmatch(scalar_wrapper.format(not_applicable_state), recorded_roots, re.I):
            recorded_roots_state = "not-applicable"
        elif re.fullmatch(scalar_wrapper.format(none_created_state), recorded_roots, re.I):
            recorded_roots_state = "none-created"
        elif re.fullmatch(scalar_wrapper.format(deferred_state), recorded_roots, re.I):
            recorded_roots_state = "deferred"
        elif recorded_roots:
            if re.match(
                rf"(?i)^`?(?:{not_applicable_state}|{none_created_state}|{deferred_state})\b",
                recorded_roots,
            ):
                recorded_roots_state = "invalid-state"
                errors.append(
                    "recorded roots state values must not include additional text or paths"
                )
            else:
                recorded_roots_state = "concrete"

        if temporary_cache_policy == "not applicable" and recorded_roots_state != "not-applicable":
            errors.append(
                "Not applicable housekeeping requires recorded roots to be Not applicable"
            )
        elif temporary_cache_policy in {"enabled", "disabled"}:
            if recorded_roots_state == "not-applicable":
                errors.append(
                    "Enabled or Disabled housekeeping cannot use Not applicable recorded roots"
                )
            elif recorded_roots_state == "concrete":
                path_entries, invalid_entries = concrete_owner_root_entries(recorded_roots)
                unsafe_roots: list[str] = []
                unresolved_roots: list[str] = []
                invalid_paths: list[str] = []
                for raw_root in path_entries:
                    normalized_root, root_errors = normalized_absolute_owner_root(raw_root)
                    if "unresolved" in root_errors:
                        unresolved_roots.append(raw_root)
                    if normalized_root is None or "not-absolute" in root_errors:
                        invalid_paths.append(raw_root)
                        continue
                    if "dot-segment" in root_errors:
                        unresolved_roots.append(raw_root)
                    recorded_root_paths.append(normalized_root)
                    slash_root = re.sub(r"/+", "/", normalized_root.replace("\\", "/"))
                    trimmed_root = slash_root.rstrip("/") or "/"
                    basename = trimmed_root.rsplit("/", 1)[-1].casefold()
                    if "root" in root_errors or trimmed_root.casefold() in {
                        "/",
                        "/tmp",
                        "/var/tmp",
                        "/private/tmp",
                        "c:/windows/temp",
                    } or basename in {"tmp", "temp", "cache", "caches"}:
                        unsafe_roots.append(raw_root)
                if unresolved_roots:
                    errors.append("recorded task temporary cache roots must be fully resolved")
                if invalid_entries or invalid_paths or not path_entries:
                    errors.append(
                        "concrete task temporary cache roots require an owner marker and "
                        "an absolute owner-specific path"
                    )
                if unsafe_roots:
                    errors.append(
                        "recorded task temporary cache roots must not name a shared or "
                        "generic temporary/cache root: " + ", ".join(unsafe_roots)
                    )

    if not overall_statuses:
        if not args.allow_draft:
            errors.append("missing overall goal status field")
    else:
        allowed_statuses = {"draft", "ready", "in progress", "closed"}
        invalid_statuses = [
            status.strip() for status in overall_statuses if status.strip().lower() not in allowed_statuses
        ]
        if invalid_statuses:
            errors.append(
                "invalid overall goal status; expected Draft, Ready, In Progress, or Closed; found "
                + ", ".join(sorted(set(invalid_statuses)))
            )

        distinct_overall_statuses = set(normalized_overall_statuses)
        if len(distinct_overall_statuses) > 1:
            errors.append(
                "overall goal statuses disagree: "
                + ", ".join(status.strip() for status in overall_statuses)
            )

        overall_status = normalized_overall_statuses[0]
        if overall_status == "draft" and not args.allow_draft:
            errors.append(
                "overall goal status must be Ready, In Progress, or Closed; found Draft"
            )
        elif overall_status == "draft":
            non_draft_rows = [
                state.name
                for state in states
                if (
                    state.status.casefold(),
                    state.review.casefold(),
                    state.checkpoint.casefold(),
                )
                != ("not started", "pending", "pending")
            ]
            if non_draft_rows:
                errors.append(
                    "overall Draft requires every milestone Not Started/Pending/Pending; found "
                    + ", ".join(non_draft_rows)
                )
        elif overall_status == "ready":
            if not current_rows:
                errors.append("overall Ready requires exactly one Ready milestone")
            elif len(current_rows) == 1:
                current = current_rows[0]
                if current.status.casefold() != "ready":
                    errors.append(
                        "overall Ready requires current milestone Ready; found "
                        f"{current.name} {current.status}"
                    )
        elif overall_status == "in progress":
            if not current_rows:
                errors.append(
                    "overall In Progress requires exactly one In Progress or Blocked milestone"
                )
            elif len(current_rows) == 1:
                current = current_rows[0]
                if current.status.casefold() not in {"in progress", "blocked"}:
                    errors.append(
                        "overall In Progress requires current milestone In Progress or Blocked; "
                        f"found {current.name} {current.status}"
                    )

        close_complete = len(close_rows) == 1 and (
            close_rows[0].status.casefold(),
            close_rows[0].review.casefold(),
            close_rows[0].checkpoint.casefold(),
        ) == ("done", "passed", "done")
        if close_complete and overall_status != "closed":
            errors.append(
                "Close is Done/Passed/Done but overall goal status is "
                + overall_status.title()
            )

        if "closed" in normalized_overall_statuses and states:
            incomplete = [
                state.name
                for state in states
                if (
                    state.status.casefold(),
                    state.review.casefold(),
                    state.checkpoint.casefold(),
                )
                != ("done", "passed", "done")
            ]
            if incomplete:
                errors.append(
                    "Closed goal requires every milestone and Close row to be "
                    "Done/Passed/Done; incomplete: "
                    + ", ".join(incomplete)
                )
            if (
                temporary_cache_section is not None
                and temporary_cache_policy in {"enabled", "disabled"}
                and recorded_roots_state == "deferred"
            ):
                errors.append(
                    "Closed Enabled or Disabled housekeeping requires concrete recorded "
                    "roots or an explicit None created outcome"
                )
            close_evidence = h2_section(
                visible_text,
                r"Close execution evidence|Close 执行证据|关闭执行证据",
            )
            raw_close_evidence = h2_section(
                text,
                r"Close execution evidence|Close 执行证据|关闭执行证据",
            )
            if close_evidence is None:
                close_gate = h2_section(visible_text, r"Close Gate|关闭门")
                if close_gate and re.search(
                    r"(?i)\bClose execution evidence\b|Close 执行证据|关闭执行证据",
                    close_gate,
                ):
                    close_evidence = close_gate
                    raw_close_gate = h2_section(text, r"Close Gate|关闭门")
                    if raw_close_gate and re.search(
                        r"(?i)\bClose execution evidence\b|Close 执行证据|关闭执行证据",
                        raw_close_gate,
                    ):
                        raw_close_evidence = raw_close_gate
            if close_evidence is None:
                errors.append("Closed goal requires Close execution evidence")
            else:
                if not re.search(r"(?i)\b(?:validation|test)\b|验证|测试", close_evidence):
                    errors.append("Close execution evidence must record validation")
                if not re.search(r"(?i)\bcheckpoint\b|检查点", close_evidence):
                    errors.append("Close execution evidence must record checkpoint evidence")
                if temporary_cache_section is not None:
                    housekeeping_evidence = housekeeping_evidence_block(close_evidence)
                    if housekeeping_evidence is None:
                        errors.append(
                            "Closed goal with a housekeeping contract requires temporary "
                            "cache / housekeeping evidence"
                        )
                    else:
                        raw_housekeeping_evidence = (
                            housekeeping_evidence_block(raw_close_evidence or "")
                            or housekeeping_evidence
                        )
                        raw_close_safety_evidence = (
                            raw_close_evidence or raw_housekeeping_evidence
                        )
                        expected_policy = re.escape(temporary_cache_policy or "").replace(
                            r"\ ", r"\s+"
                        )
                        if expected_policy and not re.search(
                            rf"(?im)^\s*(?:[-*]\s*)?Recorded\s+policy\s*[:：=]\s*"
                            rf"`?{expected_policy}`?\s*$",
                            housekeeping_evidence,
                        ):
                            errors.append(
                                "temporary cache / housekeeping evidence must record the "
                                "recorded policy"
                            )

                        no_roots_evidence = re.search(
                            r"(?i)\b(?:none|no)\s+(?:task\s+temporary\s+cache\s+)?"
                            r"roots?\s+(?:were\s+)?created\b|"
                            r"\bno task temporary cache roots?\b|"
                            r"(?:未创建|没有创建).*(?:临时缓存)?根目录",
                            housekeeping_evidence,
                        )
                        recursive_delete_or_fallback = re.search(
                            r"(?im)\brm\b[^\n;]{0,120}"
                            r"(?:--recursive\b|-[A-Za-z]*r[A-Za-z]*\b|-Recurse\b)|"
                            r"\bRemove-Item\b[^\n]{0,200}-(?:Recurse|r)\b|"
                            r"\brmdir\b[^\n]{0,100}(?:/s|-Recurse)\b|"
                            r"\bshutil\.rmtree\s*\(|"
                            r"\bos\.RemoveAll\s*\(|"
                            r"\bfs\.(?:rm|rmdir)\s*\([^\n]{0,300}"
                            r"\brecursive\s*:\s*true\b|"
                            r"\bDirectory\]?(?:::|\.)Delete\s*\([^\n]{0,160},\s*(?:true|\$true)\s*\)|"
                            r"\b(?:raw\s+recursive|recursive\s+delete)\b|"
                            r"\b(?:used|invoked|ran)\s+(?:an?\s+)?fallback\b|"
                            r"\b(?:alternate|alternative|replacement)\s+cleanup\b|"
                            r"^\s*(?:[-*]\s*)?Fallback\s*[:：=]\s*"
                            r"(?!none\b|not\s+used\b|no\s+fallback\b)\S.*$",
                            raw_close_safety_evidence,
                        )
                        if recursive_delete_or_fallback:
                            errors.append(
                                "temporary cache / housekeeping cannot close while "
                                "watcher:housekeeping is unavailable or a raw recursive "
                                "fallback is recorded"
                            )
                        if recorded_roots_state == "none-created":
                            if not no_roots_evidence:
                                errors.append(
                                    "None created recorded roots require explicit no-roots "
                                    "Close evidence"
                                )
                        elif temporary_cache_policy == "not applicable":
                            if not no_roots_evidence:
                                errors.append(
                                    "Not applicable housekeeping requires explicit no-roots "
                                    "Close evidence"
                                )
                        elif (
                            temporary_cache_policy in {"enabled", "disabled"}
                            and recorded_roots_state == "concrete"
                        ):
                            for recorded_root in recorded_root_paths:
                                expected_root = recorded_root.replace("\\", "/")
                                evidence_for_path = housekeeping_evidence.replace("\\", "/")
                                path_flags = (
                                    re.IGNORECASE
                                    if re.match(r"(?i)^[A-Z]:/|^//", expected_root)
                                    else 0
                                )
                                exact_path_pattern = (
                                    rf"(?<![A-Za-z0-9_.~/-]){re.escape(expected_root)}"
                                    r"(?=$|[\s`'\",;)\]])"
                                )
                                if not re.search(
                                    exact_path_pattern,
                                    evidence_for_path,
                                    flags=path_flags,
                                ):
                                    errors.append(
                                        "temporary cache / housekeeping Close evidence must "
                                        "repeat every exact recorded root"
                                    )
                                    break

                            action_match = re.search(
                                r"(?im)^\s*(?:[-*]\s*)?Action\s*[:：=]\s*(?P<action>\S.*)$",
                                housekeeping_evidence,
                            )
                            action = action_match.group("action") if action_match else ""
                            if temporary_cache_policy == "enabled":
                                normalized_action = normalize_contractions(action)
                                normalized_housekeeping_evidence = normalize_contractions(
                                    raw_housekeeping_evidence
                                )
                                unavailable_or_not_run = watcher_evidence_has_negative_status(
                                    normalized_housekeeping_evidence
                                )
                                watcher_action_failed = bool(
                                    re.search(
                                        r"(?i)\bwatcher:housekeeping\b",
                                        normalized_action,
                                    )
                                    and re.search(
                                        r"(?i)(?:\b(?:ran|executed|invoked)\b"
                                        r"[^\n]{0,60}\bfailed\b|\bit\s+failed\b|"
                                        r"\breturned\s+(?:a\s+)?failure\b)",
                                        normalized_action,
                                    )
                                )
                                affirmative_watcher_action = re.search(
                                    r"(?i)(?:\bwatcher:housekeeping\b[^.;\n]{0,35}"
                                    r"\b(?:invoked|ran|run|executed|inventoried|cleaned|"
                                    r"removed|performed|completed)\b|"
                                    r"\b(?:invoked|ran|executed)\b[^.;\n]{0,35}"
                                    r"\bwatcher:housekeeping\b)",
                                    normalized_action,
                                )
                                if (
                                    unavailable_or_not_run
                                    or watcher_action_failed
                                    or recursive_delete_or_fallback
                                ):
                                    errors.append(
                                        "Enabled housekeeping cannot close while "
                                        "watcher:housekeeping is unavailable or a raw "
                                        "recursive fallback is recorded"
                                    )
                                elif not affirmative_watcher_action:
                                    errors.append(
                                        "Enabled housekeeping Close evidence must record an "
                                        "affirmative watcher:housekeeping action"
                                    )
                            if temporary_cache_policy == "disabled":
                                affirmative_retention = re.search(
                                    r"(?i)\b(?:preserv(?:e|ed|ing)|retain(?:ed|ing)?)\b|保留",
                                    action,
                                )
                                negated_retention = re.search(
                                    r"(?i)\b(?:not|never|without)\b[^.\n;]{0,50}"
                                    r"\b(?:preserv(?:e|ed|ing)|retain(?:ed|ing)?)\b|未保留",
                                    action,
                                )
                                if negated_retention:
                                    errors.append(
                                        "Disabled housekeeping Close evidence must record an "
                                        "affirmative preserved or retained action"
                                    )
                                elif not affirmative_retention:
                                    errors.append(
                                        "Disabled housekeeping Close evidence must record the "
                                        "preserved or retained action"
                                    )
                                normalized_disabled_action = normalize_contractions(action)
                                affirmative_cleanup = re.search(
                                    r"(?i)\b(?:deleted|removed|cleaned|purged)\b",
                                    normalized_disabled_action,
                                )
                                if affirmative_cleanup:
                                    cleanup_prefix = normalized_disabled_action[
                                        max(0, affirmative_cleanup.start() - 50) :
                                        affirmative_cleanup.start()
                                    ]
                                    if not re.search(
                                        r"(?i)\b(?:no|not|never|without)\b[^.;\n]{0,45}$",
                                        cleanup_prefix,
                                    ):
                                        errors.append(
                                            "Disabled housekeeping Close evidence must not "
                                            "record a cleanup or deletion action"
                                        )

                            size_value = (
                                r"\d+(?:\.\d+)?\s*(?:bytes?|[KMGTPE]?i?B)"
                            )
                            required_metrics = {
                                "removed": r"removed(?:\s+size)?|移除(?:大小|体积)?",
                                "preserved": r"preserved(?:\s+size)?|保留(?:大小|体积)?",
                                "failed": r"failed(?:\s+size)?|失败(?:大小|体积)?",
                                "residual": r"residual(?:\s+size)?|残留(?:大小|体积)?",
                            }
                            for metric, label_pattern in required_metrics.items():
                                if not re.search(
                                    rf"(?i)(?:{label_pattern})\s*[:：=]\s*{size_value}\b",
                                    housekeeping_evidence,
                                ):
                                    errors.append(
                                        "temporary cache / housekeeping Close evidence "
                                        f"must record {metric} size"
                                    )

    if errors:
        return render_errors(path, errors)

    print(f"{path}: goal readiness checks OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Output formatters for validator findings.

Two consumers, one source of truth (Issues.findings):
- format_human(issues) → multi-line string, grouped by layer + rule
  category, sorted for determinism.
- format_json(issues) → dict matching the JSON schema v1 in
  docs/json-schema.md (contract: docs/spec-v1.0.md §5), ready for
  `json.dumps(..., sort_keys=True)`.

Buffer-then-emit. Checks never print directly; everything funnels here.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict

from latex2ufdissertation.pipeline.rules import (
    EXIT_REASON_CLEAN,
    EXIT_REASON_MISSING_TOOLCHAIN,
    EXIT_REASON_MUST_FIX_PRESENT,
    EXIT_REASON_REVIEW_PRESENT,
)
from latex2ufdissertation.pipeline.types import Finding, Issues

SCHEMA_VERSION = "1.0"

# Report framing — severity meaning and scope disclaimer.  These are static
# strings so the output is deterministic.  Emitted on BOTH the clean path and
# the findings path, just after the Summary line.
_FRAMING_SEVERITY = (
    "Severity guide: must-fix = will likely cause UF Graduate School rejection; "
    "review = discretionary, verify manually."
)
_FRAMING_SCOPE = (
    "Scope: clean means no violations of the rules this tool checks "
    "(targeting the Fall-2025+ UF ufdissertation template). "
    "It does NOT guarantee Graduate School acceptance — "
    "the editorial office checks requirements beyond this tool's scope."
)
_FRAMING_NO_PDF = (
    "PDF layer did not run (--dry-run or source-only mode). "
    "UF-F2, UF-F3, and other PDF-authoritative rules were not verified. "
    "Re-run without --dry-run for full coverage."
)
_FRAMING_NO_SOURCE = (
    "Source layer did not run (PDF-only input). "
    "UF-F1, UF-F4-F14, UF-S2/S3, and other source-authoritative rules were not "
    "verified. Re-run against the project source for full coverage."
)

# Rule IDs whose per-page findings are collapsed into page-range groups in the
# human report.  JSON output is NOT affected.
_GROUPABLE_RULES: frozenset[str] = frozenset({"UF-F2", "UF-F3"})

# Maps every spec-§5 exit_reason to its exit-code state. Used by
# format_json so summary.exit_code never lies on a fatal-path payload
# (any non-clean / non-must-fix / non-missing-toolchain reason → 2).
_REASON_TO_CODE: dict[str, int] = {
    EXIT_REASON_CLEAN: 0,
    EXIT_REASON_REVIEW_PRESENT: 0,
    EXIT_REASON_MUST_FIX_PRESENT: 1,
    EXIT_REASON_MISSING_TOOLCHAIN: 3,
}

_CATEGORY_ORDER = ["F", "S", "D", "P", "J", "A"]


def _category(rule_id: str) -> str:
    # "UF-F13" → "F". Falls back to "_" for any future rule prefix that
    # doesn't match the catalog's single-letter scheme so unknown IDs
    # sort last instead of crashing.
    parts = rule_id.split("-", 1)
    if len(parts) != 2 or not parts[1]:
        return "_"
    return parts[1][0]


def _spec_sort_key(f: Finding) -> tuple[str, str, str]:
    """Sort key the spec requires: (layer, rule_id, location). Used by
    the JSON serializer so byte-identical output is contractual, not
    coincidental.
    """
    return (f.layer, f.rule_id, f.location)


def _sorted_for_json(issues: Issues) -> list[Finding]:
    return sorted(issues.findings, key=_spec_sort_key)


def exit_code(issues: Issues) -> int:
    """0 if no must-fix findings; 1 otherwise. review-only does not trip
    the code. Fatal exits (2 / 3) are decided in cli.main, not here.
    """
    return 1 if issues.must_fix_count() > 0 else 0


def _default_exit_reason(issues: Issues) -> str:
    # must-fix outranks review outranks clean. review_present keeps exit_code 0
    # (review is discretionary) but stops the verdict from claiming bare "clean"
    # while unresolved review items remain.
    if issues.must_fix_count() > 0:
        return EXIT_REASON_MUST_FIX_PRESENT
    if issues.review_count() > 0:
        return EXIT_REASON_REVIEW_PRESENT
    return EXIT_REASON_CLEAN


def _parse_page_num(location: str) -> int | None:
    """Parse a "p.N" location string to an integer page number.
    Returns None if the location does not match that pattern.
    """
    m = re.fullmatch(r"p\.(\d+)", location)
    return int(m.group(1)) if m else None


def _page_range_str(page_nums: list[int]) -> str:
    """Build a compact page-range string from a sorted list of page numbers.

    Single page → "p.12".
    Multiple pages → "pp.12-16,19" (consecutive runs collapsed to "a-b",
    single-page runs as "a", runs joined with ",").
    """
    assert page_nums, "_page_range_str called with empty list"
    if len(page_nums) == 1:
        return f"p.{page_nums[0]}"
    # Collapse consecutive runs.
    runs: list[str] = []
    start = page_nums[0]
    end = page_nums[0]
    for n in page_nums[1:]:
        if n == end + 1:
            end = n
        else:
            runs.append(f"{start}-{end}" if start != end else str(start))
            start = n
            end = n
    runs.append(f"{start}-{end}" if start != end else str(start))
    return "pp." + ",".join(runs)


def _build_framing(pdf_layer_ran: bool, source_layer_ran: bool = True) -> str:
    """Return the framing block that follows the Summary line on every report.

    Includes severity guide + scope disclaimer on all runs.
    Adds a "PDF layer did not run" note when pdf_layer_ran is False, and a
    "source layer did not run" note when source_layer_ran is False.
    """
    lines = [_FRAMING_SEVERITY, _FRAMING_SCOPE]
    if not pdf_layer_ran:
        lines.append(_FRAMING_NO_PDF)
    if not source_layer_ran:
        lines.append(_FRAMING_NO_SOURCE)
    return "\n".join(lines)


def format_human(issues: Issues) -> str:
    """Render the human-readable report. Empty findings → a short
    success message. Otherwise group by layer then rule category, with
    a per-finding line citing severity, rule ID, location, and the
    observed-vs-required pair where present.

    UF-F2/UF-F3 findings that share (rule_id, observed) are consolidated
    into a single line with a page-range location.  All other findings
    render one line each.

    A framing block (severity guide + scope disclaimer + optional
    dry-run note) appears after the Summary line on every report.
    """
    framing = _build_framing(issues.pdf_layer_ran, issues.source_layer_ran)

    must_fix = issues.must_fix_count()
    review = issues.review_count()
    if not issues.findings:
        verdict = (
            "clean"
            if issues.source_layer_ran
            else "no violations in the checked layer — source layer skipped (PDF-only input)"
        )
        return f"\nSummary: 0 must-fix, 0 review — {verdict}.\n" + framing + "\n"

    # ------------------------------------------------------------------
    # Build render units: one unit per ordinary finding, one per
    # (rule_id, observed) group for UF-F2/UF-F3.
    # A "render unit" is a dict with keys:
    #   layer, cat_rank, rule_id, page_key (int for sorting), loc_str,
    #   severity, location_display, body, fix_hint, source_url
    # ------------------------------------------------------------------
    _PAGE_KEY_SENTINEL = float("inf")

    # Separate groupable candidates from everything else.
    groupable: list[Finding] = []
    ordinary: list[Finding] = []
    for f in issues.findings:
        if f.rule_id in _GROUPABLE_RULES and _parse_page_num(f.location) is not None:
            groupable.append(f)
        else:
            ordinary.append(f)

    # Group groupable findings by (rule_id, observed).
    # Key: (rule_id, observed) → list of (page_num, finding)
    groups: dict[tuple[str, str | None], list[tuple[int, Finding]]] = defaultdict(list)
    for f in groupable:
        pn = _parse_page_num(f.location)
        assert pn is not None  # guaranteed by the filter above
        groups[(f.rule_id, f.observed)].append((pn, f))

    # A render unit is a dict with keys: layer, cat_rank, rule_id, page_key,
    # loc_str, severity, location_display, body, fix_hint, source_url.
    units: list[dict] = []

    # Ordinary findings → one unit each.
    for f in ordinary:
        cat = _category(f.rule_id)
        cat_rank = _CATEGORY_ORDER.index(cat) if cat in _CATEGORY_ORDER else len(_CATEGORY_ORDER)
        pn = _parse_page_num(f.location)
        page_key = pn if pn is not None else _PAGE_KEY_SENTINEL
        body = f.observed or ""
        if f.required:
            body = f"{body} (required: {f.required})" if body else f"required: {f.required}"
        units.append(
            {
                "layer": f.layer,
                "cat_rank": cat_rank,
                "rule_id": f.rule_id,
                "page_key": page_key,
                "loc_str": f.location,
                "severity": f.severity,
                "location_display": f" {f.location}" if f.location else "",
                "body": body,
                "fix_hint": f.fix_hint,
                "source_url": f.source_url,
            }
        )

    # Grouped findings → one unit per (rule_id, observed) key.
    for (rule_id, observed), page_findings in groups.items():
        page_findings.sort(key=lambda x: x[0])
        page_nums = [pn for pn, _ in page_findings]
        rep_finding = page_findings[0][1]  # representative finding (any; same rule metadata)
        cat = _category(rule_id)
        cat_rank = _CATEGORY_ORDER.index(cat) if cat in _CATEGORY_ORDER else len(_CATEGORY_ORDER)
        min_page = page_nums[0]
        loc_str = _page_range_str(page_nums)
        count = len(page_nums)
        count_suffix = f" ({count} pages)" if count > 1 else ""
        full_loc = f" {loc_str}{count_suffix}"
        body = observed or ""
        if rep_finding.required:
            body = (
                f"{body} (required: {rep_finding.required})"
                if body
                else f"required: {rep_finding.required}"
            )
        units.append(
            {
                "layer": rep_finding.layer,
                "cat_rank": cat_rank,
                "rule_id": rule_id,
                "page_key": min_page,
                "loc_str": loc_str,
                "severity": rep_finding.severity,
                "location_display": full_loc,
                "body": body,
                "fix_hint": rep_finding.fix_hint,
                "source_url": rep_finding.source_url,
            }
        )

    # Sort all units: (layer, cat_rank, rule_id, page_key, loc_str).
    # page_key is numeric for p.N locations (F2/F3 are the only current emitters);
    # all other rules use a sentinel (inf) so they sort by loc_str as before.
    units.sort(key=lambda u: (u["layer"], u["cat_rank"], u["rule_id"], u["page_key"], u["loc_str"]))

    lines: list[str] = []
    current_layer = None
    current_cat = None
    for u in units:
        cat = _category(u["rule_id"])
        if u["layer"] != current_layer:
            lines.append(f"\n[{u['layer']} layer]")
            current_layer = u["layer"]
            current_cat = None
        if cat != current_cat:
            lines.append(f"  ({cat}-series)")
            current_cat = cat
        finding_line = (
            f"    [{u['severity']}] {u['rule_id']}{u['location_display']} — {u['body']}"
        ).rstrip(" —")
        lines.append(finding_line)
        if u["fix_hint"]:
            lines.append(f"      fix: {u['fix_hint']}")
        lines.append(f"      see: {u['source_url']}")
    lines.append(f"\nSummary: {must_fix} must-fix, {review} review.")
    return "\n".join(lines) + "\n" + framing + "\n"


def format_json(issues: Issues) -> dict:
    """Build the JSON schema v1 payload. Stable key order is guaranteed
    by the caller passing `sort_keys=True` to json.dumps; this function
    just builds the dict.
    """
    exit_reason = (
        issues.exit_reason
        if issues.exit_reason != EXIT_REASON_CLEAN
        else _default_exit_reason(issues)
    )
    # exit_code reflects the actual process exit state. On any fatal-
    # reason payload (unreadable_input, compile_failure, etc.) findings
    # may be empty but the process exited 2 — `exit_code(issues)` alone
    # would falsely report 0. Resolve via the exit_reason mapping
    # instead, defaulting non-mapped reasons to 2 (fatal-on-input).
    code = _REASON_TO_CODE.get(exit_reason, 2)
    return {
        "schema_version": SCHEMA_VERSION,
        "input": issues.input_path,
        "detected_mode": issues.detected_mode or "unknown",
        "template_version": issues.template_version or "unknown",
        "findings": [asdict(f) for f in _sorted_for_json(issues)],
        "summary": {
            "must_fix_count": issues.must_fix_count(),
            "review_count": issues.review_count(),
            "exit_code": code,
            "exit_reason": exit_reason,
        },
    }

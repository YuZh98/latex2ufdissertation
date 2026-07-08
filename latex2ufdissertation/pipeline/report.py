"""Output formatters for validator findings.

Two consumers, one source of truth (Issues.findings):
- format_human(issues) → multi-line string, grouped by severity then rule,
  one line per finding, sorted for determinism.
- format_json(issues) → dict matching the JSON schema v1 in
  docs/json-schema.md (contract: docs/spec-v1.0.md §5), ready for
  `json.dumps(..., sort_keys=True)`.

Buffer-then-emit. Checks never print directly; everything funnels here.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from itertools import groupby

from latex2ufdissertation.pipeline.rules import (
    EXIT_REASON_CLEAN,
    EXIT_REASON_MISSING_TOOLCHAIN,
    EXIT_REASON_MUST_FIX_PRESENT,
    EXIT_REASON_REVIEW_PRESENT,
    MUST_FIX,
    REVIEW,
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

# Maps every spec-§5 exit_reason to its exit-code state. Used by
# format_json so summary.exit_code never lies on a fatal-path payload
# (any non-clean / non-must-fix / non-missing-toolchain reason → 2).
_REASON_TO_CODE: dict[str, int] = {
    EXIT_REASON_CLEAN: 0,
    EXIT_REASON_REVIEW_PRESENT: 0,
    EXIT_REASON_MUST_FIX_PRESENT: 1,
    EXIT_REASON_MISSING_TOOLCHAIN: 3,
}

# Severity sections in display order: (severity value, header label).
_SEVERITY_SECTIONS: tuple[tuple[str, str], ...] = (
    (MUST_FIX, "Must-fix"),
    (REVIEW, "Review"),
)


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


def _finding_sort_key(f: Finding) -> tuple[str, int, str]:
    """Order findings within a severity section: by rule, then location.

    A page location (``p.N``) sorts by its number; non-page (source-file)
    locations sort ahead of pages (sentinel -1) so a rule's source signal
    reads before its rendered pages. Ties break on the raw location string
    for determinism.
    """
    pn = _parse_page_num(f.location)
    return (f.rule_id, pn if pn is not None else -1, f.location)


def format_human(issues: Issues) -> str:
    """Render the human-readable report.

    Findings are grouped by severity (must-fix first, then review); within
    a section one line is emitted per finding — ``RULE  location  observed``
    — with the finding's Fix hint shown once per rule group. The section
    header count equals the finding count, so the Summary line reconciles
    with the lines shown. Empty findings → a short success message.

    A framing block (severity guide + scope disclaimer + optional dry-run /
    pdf-only note) follows the Summary line on every report.
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

    # Group by severity (must-fix, then review); within a section, one line
    # per finding, ordered by rule then location, with each rule group's Fix
    # hint(s) shown once. Section counts equal finding counts, so the Summary
    # reconciles with the lines shown.
    lines: list[str] = []
    for severity, label in _SEVERITY_SECTIONS:
        section = sorted(
            (f for f in issues.findings if f.severity == severity),
            key=_finding_sort_key,
        )
        if not section:
            continue
        lines.append(f"\n{label} ({len(section)})\n")
        for _, group_iter in groupby(section, key=lambda f: f.rule_id):
            group = list(group_iter)
            loc_width = max((len(f.location) for f in group if f.location), default=0)
            for f in group:
                loc = f.location.ljust(loc_width)
                observed = f.observed or f.required or ""
                lines.append(f"  {f.rule_id}  {loc}  {observed}".rstrip())
            # One Fix line per distinct hint in the group (usually exactly one;
            # a dual-layer rule may carry a source hint and a rendered hint).
            seen_hints: list[str] = []
            for f in group:
                if f.fix_hint and f.fix_hint not in seen_hints:
                    seen_hints.append(f.fix_hint)
            for hint in seen_hints:
                lines.append(f"    Fix: {hint}")

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

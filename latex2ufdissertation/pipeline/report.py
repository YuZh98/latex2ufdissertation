"""Output formatters for validator findings.

Two consumers, one source of truth (Issues.findings):
- format_human(issues) → multi-line string, grouped by layer + rule
  category, sorted for determinism.
- format_json(issues) → dict matching the JSON schema v1 in
  docs/spec-v1.0.md §5, ready for `json.dumps(..., sort_keys=True)`.

Buffer-then-emit. Checks never print directly; everything funnels here.
"""

from __future__ import annotations

from dataclasses import asdict

from latex2ufdissertation.pipeline.rules import (
    EXIT_REASON_CLEAN,
    EXIT_REASON_MUST_FIX_PRESENT,
)
from latex2ufdissertation.pipeline.types import Finding, Issues

SCHEMA_VERSION = "1.0"

_CATEGORY_ORDER = ["F", "S", "D", "P", "J", "A"]


def _category(rule_id: str) -> str:
    # "UF-F13" → "F". Falls back to "_" for any future rule prefix that
    # doesn't match the catalog's single-letter scheme so unknown IDs
    # sort last instead of crashing.
    parts = rule_id.split("-", 1)
    if len(parts) != 2 or not parts[1]:
        return "_"
    return parts[1][0]


def _sort_key(f: Finding) -> tuple[str, int, str, str]:
    cat = _category(f.rule_id)
    cat_rank = _CATEGORY_ORDER.index(cat) if cat in _CATEGORY_ORDER else len(_CATEGORY_ORDER)
    return (f.layer, cat_rank, f.rule_id, f.location)


def _sorted_findings(issues: Issues) -> list[Finding]:
    return sorted(issues.findings, key=_sort_key)


def exit_code(issues: Issues) -> int:
    """0 if no must-fix findings; 1 otherwise. review-only does not trip
    the code. Fatal exits (2 / 3) are decided in cli.main, not here.
    """
    return 1 if issues.must_fix_count() > 0 else 0


def _default_exit_reason(issues: Issues) -> str:
    return EXIT_REASON_MUST_FIX_PRESENT if issues.must_fix_count() > 0 else EXIT_REASON_CLEAN


def format_human(issues: Issues) -> str:
    """Render the human-readable report. Empty findings → a short
    success message. Otherwise group by layer then rule category, with
    a per-finding line citing severity, rule ID, location, and the
    observed-vs-required pair where present.
    """
    must_fix = issues.must_fix_count()
    review = issues.review_count()
    if not issues.findings:
        return f"\nSummary: 0 must-fix, 0 review — clean.\n"

    lines: list[str] = []
    current_layer = None
    current_cat = None
    for f in _sorted_findings(issues):
        cat = _category(f.rule_id)
        if f.layer != current_layer:
            lines.append(f"\n[{f.layer} layer]")
            current_layer = f.layer
            current_cat = None
        if cat != current_cat:
            lines.append(f"  ({cat}-series)")
            current_cat = cat
        loc = f" {f.location}" if f.location else ""
        body = f.observed or ""
        if f.required:
            body = f"{body} (required: {f.required})" if body else f"required: {f.required}"
        lines.append(f"    [{f.severity}] {f.rule_id}{loc} — {body}".rstrip(" —"))
        if f.fix_hint:
            lines.append(f"      fix: {f.fix_hint}")
        lines.append(f"      see: {f.source_url}")
    lines.append(f"\nSummary: {must_fix} must-fix, {review} review.")
    return "\n".join(lines) + "\n"


def format_json(issues: Issues) -> dict:
    """Build the JSON schema v1 payload. Stable key order is guaranteed
    by the caller passing `sort_keys=True` to json.dumps; this function
    just builds the dict.
    """
    exit_reason = (
        issues.exit_reason if issues.exit_reason != EXIT_REASON_CLEAN
        else _default_exit_reason(issues)
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "input": issues.input_path,
        "template_version": issues.template_version,
        "findings": [asdict(f) for f in _sorted_findings(issues)],
        "summary": {
            "must_fix_count": issues.must_fix_count(),
            "review_count": issues.review_count(),
            "exit_code": exit_code(issues),
            "exit_reason": exit_reason,
        },
    }

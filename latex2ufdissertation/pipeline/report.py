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

from dataclasses import asdict

from latex2ufdissertation.pipeline.rules import (
    EXIT_REASON_CLEAN,
    EXIT_REASON_MISSING_TOOLCHAIN,
    EXIT_REASON_MUST_FIX_PRESENT,
)
from latex2ufdissertation.pipeline.types import Finding, Issues

SCHEMA_VERSION = "1.0"

# Maps every spec-§5 exit_reason to its exit-code state. Used by
# format_json so summary.exit_code never lies on a fatal-path payload
# (any non-clean / non-must-fix / non-missing-toolchain reason → 2).
_REASON_TO_CODE: dict[str, int] = {
    EXIT_REASON_CLEAN: 0,
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


def _human_sort_key(f: Finding) -> tuple[str, int, str, str]:
    """Sort key the human report uses so category headers (F-series,
    S-series, ...) render in a sensible order. Diverges from
    `_spec_sort_key` only at the category-rank tiebreaker; both keys
    agree within a category.
    """
    cat = _category(f.rule_id)
    cat_rank = _CATEGORY_ORDER.index(cat) if cat in _CATEGORY_ORDER else len(_CATEGORY_ORDER)
    return (f.layer, cat_rank, f.rule_id, f.location)


def _sorted_for_json(issues: Issues) -> list[Finding]:
    return sorted(issues.findings, key=_spec_sort_key)


def _sorted_for_human(issues: Issues) -> list[Finding]:
    return sorted(issues.findings, key=_human_sort_key)


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
        return "\nSummary: 0 must-fix, 0 review — clean.\n"

    lines: list[str] = []
    current_layer = None
    current_cat = None
    for f in _sorted_for_human(issues):
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

"""Schema and formatting tests for report.format_human / format_json."""

from __future__ import annotations

import json
from pathlib import Path

from latex2ufdissertation.pipeline.report import (
    SCHEMA_VERSION,
    exit_code,
    format_human,
    format_json,
)
from latex2ufdissertation.pipeline.types import Issues

REPO_ROOT = Path(__file__).resolve().parent.parent


def _populated_issues() -> Issues:
    issues = Issues()
    issues.input_path = "demo/"
    issues.template_version = "Fall 2025"
    issues.add("UF-F13", location="main.tex", observed="bad class")
    issues.add("UF-D1", location="main.tex", observed="editMode left on")
    return issues


def test_format_json_top_level_keys_are_frozen_v1_shape():
    payload = format_json(_populated_issues())
    assert set(payload.keys()) == {
        "schema_version",
        "input",
        "detected_mode",
        "template_version",
        "findings",
        "summary",
    }
    assert payload["schema_version"] == SCHEMA_VERSION == "1.0"


def test_format_json_unknown_fields_emit_unknown_string():
    # Spec § 5: template_version is "the detected version, or `unknown`".
    # detected_mode follows the same rule when the input mode is unset.
    payload = format_json(Issues())
    assert payload["template_version"] == "unknown"
    assert payload["detected_mode"] == "unknown"


def test_format_json_detected_mode_reflects_value():
    issues = Issues()
    issues.detected_mode = "zip"
    issues.template_version = "Fall 2025"
    payload = format_json(issues)
    assert payload["detected_mode"] == "zip"
    assert payload["template_version"] == "Fall 2025"


def test_json_schema_doc_documents_every_emitted_key():
    # Drift gate (#12): every top-level key format_json emits must be
    # documented in docs/json-schema.md, so the code and the schema doc
    # cannot diverge silently. The reconciled fields (detected_mode and the
    # template_version "unknown" semantics) must be present.
    keys = set(format_json(Issues()).keys())
    doc = (REPO_ROOT / "docs" / "json-schema.md").read_text(encoding="utf-8")
    for key in keys:
        assert f"`{key}`" in doc, f"format_json key {key!r} undocumented in json-schema.md"
    # The reconciled semantics must be documented per-field, not just the
    # bare word "unknown" (which also appears in unrelated exit_reason prose).
    # template_version row:
    assert '`"unknown"` when undetectable' in doc
    # detected_mode row (its own enum incl. "unknown"):
    assert '`"pdf"`, or `"unknown"`' in doc


def test_format_json_summary_shape():
    payload = format_json(_populated_issues())
    summary = payload["summary"]
    assert set(summary.keys()) == {
        "must_fix_count",
        "review_count",
        "exit_code",
        "exit_reason",
    }
    assert summary["must_fix_count"] == 1
    assert summary["review_count"] == 1
    assert summary["exit_code"] == 1
    assert summary["exit_reason"] == "must_fix_present"


def test_format_json_clean_run_has_exit_reason_clean():
    issues = Issues()
    payload = format_json(issues)
    assert payload["summary"]["exit_code"] == 0
    assert payload["summary"]["exit_reason"] == "clean"


def test_format_json_per_finding_has_all_eight_fields():
    payload = format_json(_populated_issues())
    assert payload["findings"], "expected at least one finding"
    expected = {
        "severity",
        "rule_id",
        "layer",
        "location",
        "observed",
        "required",
        "fix_hint",
        "source_url",
    }
    for f in payload["findings"]:
        assert set(f.keys()) == expected


def test_format_json_is_json_serializable_with_sort_keys():
    payload = format_json(_populated_issues())
    # Must round-trip cleanly under sort_keys for deterministic output.
    s = json.dumps(payload, indent=2, sort_keys=True)
    assert json.loads(s) == payload


def test_format_human_clean_run_returns_clean_summary():
    issues = Issues()
    out = format_human(issues)
    assert "clean" in out.lower()
    assert "0 must-fix" in out


def test_format_human_groups_by_layer_and_category():
    issues = _populated_issues()
    out = format_human(issues)
    assert "[source layer]" in out
    assert "(F-series)" in out
    assert "(D-series)" in out
    assert "UF-F13" in out
    assert "UF-D1" in out


def test_human_report_groups_by_category_then_rule_id():
    # The human view interpolates category rank between layer and
    # rule_id so the F-series block appears before the D-series block
    # under the source layer. The JSON sort key is different (spec-
    # mandated lex on rule_id); see the dedicated JSON sort test.
    issues = Issues()
    issues.add("UF-D1", location="x.tex", observed="x")
    issues.add("UF-F14", location="b.tex", observed="b")
    issues.add("UF-F13", location="a.tex", observed="a")
    out = format_human(issues)
    # F13 line appears before F14 line appears before D1 line.
    assert out.index("UF-F13") < out.index("UF-F14") < out.index("UF-D1")


def test_exit_code_reflects_must_fix_only():
    issues = Issues()
    issues.add("UF-D1", observed="review-only finding")
    assert exit_code(issues) == 0
    issues.add("UF-F13", observed="must-fix finding")
    assert exit_code(issues) == 1


def test_format_json_exit_code_reflects_fatal_exit_reason():
    # On fatal-path payloads (no findings, but the process exits 2 or 3),
    # summary.exit_code must mirror the actual exit state, not a
    # findings-derived 0. Guard against the C1 regression spotted in
    # PR #7 review.
    issues = Issues()
    issues.set_exit_reason("unreadable_input")
    payload = format_json(issues)
    assert payload["summary"]["exit_code"] == 2
    assert payload["summary"]["exit_reason"] == "unreadable_input"

    issues2 = Issues()
    issues2.set_exit_reason("missing_toolchain")
    payload2 = format_json(issues2)
    assert payload2["summary"]["exit_code"] == 3

    issues3 = Issues()
    issues3.set_exit_reason("compile_failure")
    payload3 = format_json(issues3)
    assert payload3["summary"]["exit_code"] == 2


def test_findings_in_json_use_spec_sort_key_layer_rule_id_location():
    # Spec (docs/spec-v1.0.md §6) requires (layer, rule_id, location)
    # ordering verbatim. Category-rank tiebreakers belong only in the
    # human-readable view. Guard the C2 fix.
    issues = Issues()
    issues.add("UF-P1", observed="p")  # P-series — sorts before S lexicographically
    issues.add("UF-S3", observed="s")  # S-series
    issues.add("UF-F13", observed="f")  # F-series
    payload = format_json(issues)
    ids = [f["rule_id"] for f in payload["findings"]]
    # All three are source layer; pure lex order on rule_id.
    assert ids == sorted(ids), f"JSON sort order diverged from spec: {ids}"

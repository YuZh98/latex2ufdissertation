"""Schema and formatting tests for report.format_human / format_json."""

from __future__ import annotations

import json

from latex2ufdissertation.pipeline.report import (
    SCHEMA_VERSION,
    exit_code,
    format_human,
    format_json,
)
from latex2ufdissertation.pipeline.types import Issues


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
        "template_version",
        "findings",
        "summary",
    }
    assert payload["schema_version"] == SCHEMA_VERSION == "1.0"


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
    expected = {"severity", "rule_id", "layer", "location",
                "observed", "required", "fix_hint", "source_url"}
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


def test_findings_sorted_by_layer_then_category_then_id_then_location():
    issues = Issues()
    issues.add("UF-D1", location="x.tex", observed="x")
    issues.add("UF-F14", location="b.tex", observed="b")
    issues.add("UF-F13", location="a.tex", observed="a")
    payload = format_json(issues)
    ids = [f["rule_id"] for f in payload["findings"]]
    # All three are source-layer; F-series sorts before D-series; within F:
    # F13 before F14 lexicographically.
    assert ids == ["UF-F13", "UF-F14", "UF-D1"]


def test_exit_code_reflects_must_fix_only():
    issues = Issues()
    issues.add("UF-D1", observed="review-only finding")
    assert exit_code(issues) == 0
    issues.add("UF-F13", observed="must-fix finding")
    assert exit_code(issues) == 1

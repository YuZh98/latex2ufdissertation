"""Schema and formatting tests for report.format_human / format_json."""

from __future__ import annotations

import json
from pathlib import Path

from latex2ufdissertation.pipeline.report import (
    _FRAMING_NO_PDF,
    _FRAMING_SCOPE,
    _FRAMING_SEVERITY,
    A2_ADVISORY,
    SCHEMA_VERSION,
    exit_code,
    format_human,
    format_json,
)
from latex2ufdissertation.pipeline.types import (
    Finding,
    Issues,
)

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


# --- A2 standing advisory tests (FIX #4: gated on pdf_layer_ran) ---


def test_a2_advisory_appears_when_pdf_layer_ran_clean():
    # A2 must appear when pdf_layer_ran=True, even on the clean path.
    issues = Issues()
    issues.pdf_layer_ran = True
    out = format_human(issues)
    assert A2_ADVISORY in out


def test_a2_advisory_appears_when_pdf_layer_ran_with_findings():
    # A2 must appear when pdf_layer_ran=True and there are findings.
    issues = _populated_issues()
    issues.pdf_layer_ran = True
    out = format_human(issues)
    assert A2_ADVISORY in out


def test_a2_advisory_absent_when_pdf_layer_not_ran_clean():
    # A2 must NOT appear when pdf_layer_ran=False (default, dry-run/source-only).
    issues = Issues()
    # pdf_layer_ran defaults to False
    out = format_human(issues)
    assert "Advisory (not a finding)" not in out


def test_a2_advisory_absent_when_pdf_layer_not_ran_with_findings():
    # A2 must NOT appear when pdf_layer_ran=False, even with findings.
    issues = _populated_issues()
    # pdf_layer_ran defaults to False
    out = format_human(issues)
    assert "Advisory (not a finding)" not in out


def test_a2_advisory_absent_from_json_output():
    # A2 is human-only; the JSON schema is frozen. The advisory text must
    # not appear anywhere in the serialised JSON payload.
    issues = Issues()
    issues.pdf_layer_ran = True
    json_str = json.dumps(format_json(issues), sort_keys=True)
    assert A2_ADVISORY not in json_str

    issues2 = _populated_issues()
    issues2.pdf_layer_ran = True
    json_str2 = json.dumps(format_json(issues2), sort_keys=True)
    assert A2_ADVISORY not in json_str2


def test_a2_advisory_does_not_affect_counts_or_exit_code():
    # Emitting A2 is additive only; it must not change must_fix_count,
    # review_count, or exit_code on either a clean or a findings-bearing run.
    clean = Issues()
    clean.pdf_layer_ran = True
    assert clean.must_fix_count() == 0
    assert clean.review_count() == 0
    assert exit_code(clean) == 0
    # Presence of the advisory text in human output does not change state.
    format_human(clean)
    assert clean.must_fix_count() == 0
    assert clean.review_count() == 0
    assert exit_code(clean) == 0

    populated = _populated_issues()
    populated.pdf_layer_ran = True
    before_must = populated.must_fix_count()
    before_review = populated.review_count()
    before_exit = exit_code(populated)
    format_human(populated)
    assert populated.must_fix_count() == before_must
    assert populated.review_count() == before_review
    assert exit_code(populated) == before_exit


# --- FIX #4: pdf_layer_ran flag set by run_pdf_checks ---


def test_pdf_layer_ran_false_by_default():
    issues = Issues()
    assert issues.pdf_layer_ran is False


def test_pdf_layer_ran_set_by_run_pdf_checks(tmp_path):
    """run_pdf_checks must set pdf_layer_ran=True at entry, before any
    later check runs.  Monkeypatching _extract_pages to raise verifies
    the flag is set even when a subsequent step fails.
    """
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks
    from latex2ufdissertation.pipeline.types import UnreadableInput

    dummy_pdf = tmp_path / "x.pdf"
    dummy_pdf.write_bytes(b"")

    issues = Issues()
    with patch(
        "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
        side_effect=UnreadableInput("mocked"),
    ):
        try:
            run_pdf_checks(dummy_pdf, issues)
        except UnreadableInput:
            pass

    assert issues.pdf_layer_ran is True


# --- FIX #FRAME: report framing (severity meaning + scope honesty) ---


def test_framing_severity_present_in_clean_run():
    issues = Issues()
    out = format_human(issues)
    assert _FRAMING_SEVERITY in out


def test_framing_scope_present_in_clean_run():
    issues = Issues()
    out = format_human(issues)
    assert _FRAMING_SCOPE in out


def test_framing_severity_present_with_findings():
    issues = _populated_issues()
    out = format_human(issues)
    assert _FRAMING_SEVERITY in out


def test_framing_scope_present_with_findings():
    issues = _populated_issues()
    out = format_human(issues)
    assert _FRAMING_SCOPE in out


def test_framing_no_pdf_note_present_when_pdf_layer_not_ran():
    issues = Issues()
    # pdf_layer_ran=False by default → dry-run note must appear
    out = format_human(issues)
    assert _FRAMING_NO_PDF in out


def test_framing_no_pdf_note_absent_when_pdf_layer_ran():
    issues = Issues()
    issues.pdf_layer_ran = True
    out = format_human(issues)
    assert _FRAMING_NO_PDF not in out


def test_framing_no_pdf_note_absent_when_pdf_layer_ran_with_findings():
    issues = _populated_issues()
    issues.pdf_layer_ran = True
    out = format_human(issues)
    assert _FRAMING_NO_PDF not in out


# --- FIX #2: UF-F2 / UF-F3 consolidation in human report ---


def _make_f2_finding(location: str, observed: str = "LMRoman12-Regular") -> Finding:
    """Build a synthetic UF-F2 Finding for testing consolidation."""
    from latex2ufdissertation.pipeline.rules import MUST_FIX, PDF, RULES

    rule = RULES["UF-F2"]
    return Finding(
        severity=MUST_FIX,
        rule_id="UF-F2",
        layer=PDF,
        location=location,
        observed=observed,
        required="Times New Roman or Arial body font",
        fix_hint=rule.fix_hint,
        source_url=rule.source_url,
    )


def _make_f3_finding(location: str, observed: str = "20.0pt body text") -> Finding:
    """Build a synthetic UF-F3 Finding for testing consolidation."""
    from latex2ufdissertation.pipeline.rules import MUST_FIX, PDF, RULES

    rule = RULES["UF-F3"]
    return Finding(
        severity=MUST_FIX,
        rule_id="UF-F3",
        layer=PDF,
        location=location,
        observed=observed,
        required="12-point body text",
        fix_hint=rule.fix_hint,
        source_url=rule.source_url,
    )


def _count_finding_lines(out: str, rule_id: str) -> int:
    """Count rendered finding lines for a given rule_id (lines starting with
    '    [' that contain the rule_id). Excludes framing/advisory text."""
    return sum(1 for line in out.splitlines() if line.startswith("    [") and rule_id in line)


def test_f2_multiple_pages_same_observed_consolidated():
    """N>1 UF-F2 findings with the same observed value → one line with 'pp.'
    and '(N pages)'.
    """
    issues = Issues()
    for page in [12, 13, 14, 15, 16, 19, 20, 21, 22, 23, 24, 25, 26]:
        issues.findings.append(_make_f2_finding(f"p.{page}"))
    out = format_human(issues)
    # Exactly one grouped finding line (not 13 separate lines)
    assert _count_finding_lines(out, "UF-F2") == 1
    assert "pp." in out
    assert "(13 pages)" in out
    assert "LMRoman12-Regular" in out


def test_f2_single_page_no_count_suffix():
    """A single-page UF-F2 renders 'p.12' with NO '(1 pages)' suffix."""
    issues = Issues()
    issues.findings.append(_make_f2_finding("p.12"))
    out = format_human(issues)
    assert "p.12" in out
    assert "(1 pages)" not in out
    # Should be one finding line only
    assert _count_finding_lines(out, "UF-F2") == 1


def test_f2_two_different_observed_fonts_two_lines():
    """Two different observed fonts → two separate grouped lines."""
    issues = Issues()
    for page in [1, 2, 3]:
        issues.findings.append(_make_f2_finding(f"p.{page}", observed="LMRoman12-Regular"))
    for page in [4, 5, 6]:
        issues.findings.append(_make_f2_finding(f"p.{page}", observed="ComicSansMS"))
    out = format_human(issues)
    assert _count_finding_lines(out, "UF-F2") == 2
    assert "LMRoman12-Regular" in out
    assert "ComicSansMS" in out


def test_f3_consolidation_same_treatment():
    """UF-F3 findings with same observed collapse the same way as UF-F2."""
    issues = Issues()
    for page in [3, 4, 5]:
        issues.findings.append(_make_f3_finding(f"p.{page}"))
    out = format_human(issues)
    assert _count_finding_lines(out, "UF-F3") == 1
    assert "pp." in out
    assert "(3 pages)" in out


def test_f2_json_still_one_finding_per_page():
    """format_json must still emit one finding per page (consolidation is
    human-only; JSON schema is frozen).
    """
    issues = Issues()
    for page in [1, 2, 3, 4, 5]:
        issues.findings.append(_make_f2_finding(f"p.{page}"))
    payload = format_json(issues)
    f2_findings = [f for f in payload["findings"] if f["rule_id"] == "UF-F2"]
    assert len(f2_findings) == 5, f"Expected 5 per-page F2 findings in JSON, got {len(f2_findings)}"


def test_f2_page_range_consecutive_runs():
    """Pages 12-16 and 19-26 collapse to 'pp.12-16,19-26'."""
    issues = Issues()
    for page in [12, 13, 14, 15, 16, 19, 20, 21, 22, 23, 24, 25, 26]:
        issues.findings.append(_make_f2_finding(f"p.{page}"))
    out = format_human(issues)
    assert "pp.12-16,19-26" in out


def test_f2_non_pn_location_renders_individually():
    """A UF-F2 finding whose location does NOT match 'p.N' falls back to
    individual rendering (no consolidation).
    """
    issues = Issues()
    # Two F2 findings with non-"p.N" location — must render as two lines.
    for loc in ["section:intro", "appendix"]:
        issues.findings.append(_make_f2_finding(loc))
    out = format_human(issues)
    # Two individual UF-F2 finding lines (no consolidation because no "p.N" locations)
    assert _count_finding_lines(out, "UF-F2") == 2
    assert "pp." not in out

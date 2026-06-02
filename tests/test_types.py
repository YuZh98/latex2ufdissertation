from latex2ufdissertation.pipeline.rules import BOTH, MUST_FIX, PDF, REVIEW, SOURCE
from latex2ufdissertation.pipeline.types import (
    ConverterError,
    Finding,
    Issues,
    MissingToolchain,
    UnreadableInput,
)


def test_issues_starts_empty():
    issues = Issues()
    assert issues.findings == []
    assert issues.must_fix_count() == 0
    assert issues.review_count() == 0
    assert issues.template_version is None
    assert issues.exit_reason == "clean"


def test_issues_add_appends_finding_and_writes_stderr(capsys):
    issues = Issues()
    issues.add(
        "UF-F13",
        location="main.tex",
        observed="\\documentclass{article}",
        required="\\documentclass{ufdissertation}",
    )
    assert len(issues.findings) == 1
    f = issues.findings[0]
    assert isinstance(f, Finding)
    assert f.rule_id == "UF-F13"
    assert f.severity == MUST_FIX
    assert f.layer == SOURCE
    assert f.location == "main.tex"
    assert f.source_url.startswith("https://github.com/")
    captured = capsys.readouterr()
    # Progress / diagnostic output goes to stderr; stdout is reserved
    # for the --json payload contract.
    assert captured.out == ""
    assert "UF-F13" in captured.err
    assert "must-fix" in captured.err


def test_emit_progress_false_suppresses_diagnostic_line(capsys):
    # Under --json the cli sets emit_progress=False; add() must not print the
    # live per-finding diagnostic (the final report carries it instead).
    issues = Issues(emit_progress=False)
    issues.add("UF-F13", observed="bad class")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""  # no live diagnostic line
    assert len(issues.findings) == 1  # finding still recorded


def test_emit_progress_default_true_still_prints(capsys):
    # Default (normal CLI run) keeps the live diagnostic stream.
    issues = Issues()
    issues.add("UF-F13", observed="bad class")
    assert "UF-F13" in capsys.readouterr().err


def test_issues_counts_split_by_severity():
    issues = Issues()
    issues.add("UF-F13", observed="bad class")
    issues.add("UF-D1", observed="editMode left on")
    assert issues.must_fix_count() == 1
    assert issues.review_count() == 1


def test_per_finding_fix_hint_overrides_rule_default():
    issues = Issues()
    issues.add("UF-F13", fix_hint="custom hint")
    assert issues.findings[0].fix_hint == "custom hint"


def test_default_fix_hint_falls_back_to_rule_registry():
    issues = Issues()
    issues.add("UF-F13")
    # Rule UF-F13 has a non-null fix_hint in the registry; verify it
    # propagates when the caller does not override.
    assert issues.findings[0].fix_hint is not None
    assert "ufdissertation" in issues.findings[0].fix_hint


def test_unknown_rule_id_raises_keyerror():
    issues = Issues()
    try:
        issues.add("UF-XX999")
    except KeyError:
        return
    raise AssertionError("expected KeyError on unknown rule_id")


def test_set_exit_reason_validates_against_enum():
    issues = Issues()
    issues.set_exit_reason("missing_toolchain")
    assert issues.exit_reason == "missing_toolchain"
    try:
        issues.set_exit_reason("bogus_reason")
    except ValueError:
        return
    raise AssertionError("expected ValueError on unknown exit_reason")


def test_converter_error_hierarchy():
    assert issubclass(ConverterError, Exception)
    assert issubclass(UnreadableInput, ConverterError)
    assert issubclass(MissingToolchain, ConverterError)
    # Each subclass carries its own exit_reason for the JSON summary.
    assert UnreadableInput().exit_reason == "unreadable_input"
    assert MissingToolchain().exit_reason == "missing_toolchain"


def test_severity_constants_are_distinct():
    assert MUST_FIX != REVIEW


# --- Override tests (severity/layer per-call overrides) ---


def test_add_severity_layer_override_changes_finding():
    """add() with severity/layer overrides uses the supplied values, not the registry's."""
    # UF-F2 registry: severity=must-fix, layer=both — override to review/source
    issues = Issues()
    issues.add("UF-F2", severity=REVIEW, layer=SOURCE)
    f = issues.findings[0]
    assert f.severity == REVIEW
    assert f.layer == SOURCE


def test_add_no_override_uses_registry_values():
    """add() without overrides preserves the exact registry severity and layer."""
    issues = Issues()
    issues.add("UF-F2")
    f = issues.findings[0]
    assert f.severity == MUST_FIX
    assert f.layer == BOTH


def test_add_override_does_not_affect_fix_hint_or_source_url():
    """severity/layer overrides must not disturb fix_hint or source_url resolution."""
    issues = Issues()
    issues.add("UF-F2", severity=REVIEW, layer=PDF)
    f = issues.findings[0]
    # fix_hint falls back to registry value (UF-F2 has one)
    assert f.fix_hint is not None
    assert "Times New Roman" in f.fix_hint or "font" in f.fix_hint.lower()
    # source_url comes from the registry unchanged
    assert f.source_url.startswith("https://github.com/")


def test_add_severity_override_appears_in_stderr(capsys):
    """The stderr diagnostic line must print the *effective* severity, not always the registry's."""
    issues = Issues()
    issues.add("UF-F2", severity=REVIEW, layer=SOURCE)
    captured = capsys.readouterr()
    assert "review" in captured.err
    # The registry value (must-fix) must NOT appear in its place
    assert "must-fix" not in captured.err

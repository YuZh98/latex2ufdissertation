from pathlib import Path

import pytest

from latex2ufdissertation.pipeline.checks import run_checks
from latex2ufdissertation.pipeline.rules import MUST_FIX, REVIEW
from latex2ufdissertation.pipeline.types import Issues


def _project(tmp_path: Path, master: str, extra: dict[str, str] | None = None) -> Path:
    (tmp_path / "master.tex").write_text(master, encoding="utf-8")
    for name, body in (extra or {}).items():
        (tmp_path / name).write_text(body, encoding="utf-8")
    return tmp_path / "master.tex"


_VALID = r"""\documentclass{ufdissertation}
\title{X}
\author{Y}
\degreeType{Doctor of Philosophy}
\thesisType{Dissertation}
\degreeYear{2026}
\degreeMonth{May}
\major{Computer Science}
\chair{Advisor}
\setAcknowledgementsFile{ack}
\setAbstractFile{abs}
\setReferenceFile{refs}{agsm}
\setBiographicalFile{bio}
\begin{document}\end{document}
"""

_VALID_FILES = {
    "ack.tex": "",
    "abs.tex": "",
    "refs.bib": "",
    "bio.tex": "",
}


def _rule_ids(issues: Issues) -> set[str]:
    return {f.rule_id for f in issues.findings}


def test_valid_project_no_findings(tmp_path):
    master = _project(tmp_path, _VALID, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert issues.findings == []
    assert issues.must_fix_count() == 0
    assert issues.review_count() == 0


def test_wrong_documentclass_fires_uf_f13(tmp_path):
    src = r"\documentclass{article}" + "\n" + _VALID.split("\n", 1)[1]
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F13" in _rule_ids(issues)
    f = next(f for f in issues.findings if f.rule_id == "UF-F13")
    assert f.severity == MUST_FIX
    assert "article" in (f.observed or "")


@pytest.mark.parametrize(
    "cmd,label",
    [
        (r"\title{X}", r"\title"),
        (r"\author{Y}", r"\author"),
        (r"\degreeType{Doctor of Philosophy}", r"\degreeType"),
        (r"\thesisType{Dissertation}", r"\thesisType"),
        (r"\degreeYear{2026}", r"\degreeYear"),
        (r"\degreeMonth{May}", r"\degreeMonth"),
        (r"\major{Computer Science}", r"\major"),
        (r"\chair{Advisor}", r"\chair"),
    ],
)
def test_missing_required_command_fires_uf_f14(tmp_path, cmd, label):
    src = _VALID.replace(cmd, "")
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f14_findings = [f for f in issues.findings if f.rule_id == "UF-F14"]
    assert f14_findings, "expected at least one UF-F14 finding"
    assert any(label in (f.observed or "") for f in f14_findings)
    assert all(f.severity == MUST_FIX for f in f14_findings)


@pytest.mark.parametrize(
    "set_cmd,file_name,cmd_label",
    [
        (r"\setAcknowledgementsFile{ack}", "ack.tex", r"\setAcknowledgementsFile"),
        (r"\setAbstractFile{abs}", "abs.tex", r"\setAbstractFile"),
        (r"\setReferenceFile{refs}{agsm}", "refs.bib", r"\setReferenceFile"),
        (r"\setBiographicalFile{bio}", "bio.tex", r"\setBiographicalFile"),
    ],
)
def test_missing_setfile_fires_uf_f8(tmp_path, set_cmd, file_name, cmd_label):
    src = _VALID.replace(set_cmd, "")
    files = dict(_VALID_FILES)
    files.pop(file_name, None)
    master = _project(tmp_path, src, files)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f8_findings = [f for f in issues.findings if f.rule_id == "UF-F8"]
    assert f8_findings, "expected at least one UF-F8 finding"
    assert any(cmd_label in (f.observed or "") for f in f8_findings)
    assert all(f.severity == MUST_FIX for f in f8_findings)


@pytest.mark.parametrize(
    "file_name,cmd_label",
    [
        ("ack.tex", r"\setAcknowledgementsFile"),
        ("abs.tex", r"\setAbstractFile"),
        ("refs.bib", r"\setReferenceFile"),
        ("bio.tex", r"\setBiographicalFile"),
    ],
)
def test_missing_setfile_target_fires_uf_p1(tmp_path, file_name, cmd_label):
    files = {k: v for k, v in _VALID_FILES.items() if k != file_name}
    master = _project(tmp_path, _VALID, files)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    p1_findings = [f for f in issues.findings if f.rule_id == "UF-P1"]
    assert p1_findings, "expected at least one UF-P1 finding"
    assert any(cmd_label in (f.observed or "") for f in p1_findings)
    assert all(f.severity == MUST_FIX for f in p1_findings)


def test_editmode_fires_uf_d1_review(tmp_path):
    src = _VALID.replace(
        r"\documentclass{ufdissertation}",
        r"\documentclass[editMode]{ufdissertation}",
    )
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-D1" in _rule_ids(issues)
    d1 = next(f for f in issues.findings if f.rule_id == "UF-D1")
    assert d1.severity == REVIEW


def test_pdflatex_hint_fires_uf_d2_must_fix(tmp_path):
    src = "% !TEX program = pdflatex\n" + _VALID
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-D2" in _rule_ids(issues)
    d2 = next(f for f in issues.findings if f.rule_id == "UF-D2")
    # Per the spec rebrand: D2 is must-fix (was warn in v0.1).
    assert d2.severity == MUST_FIX


def test_chair_with_optional_cochair_bracket_satisfies_uf_f14(tmp_path):
    # UF template documents \chair[Co-chair]{Chair} as the optional-cochair
    # form. The detector must accept that as satisfying the F14 requirement.
    src = _VALID.replace(r"\chair{Advisor}", r"\chair[Co-chair Example]{Chair Example}")
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F14" not in _rule_ids(issues)


@pytest.mark.parametrize("month", ["May", "August", "December", " May ", "August "])
def test_valid_degree_month_does_not_fire_uf_f14(tmp_path, month):
    # Catalog: \degreeMonth must be May / August / December per C2:41.
    # Whitespace padding around the value (e.g. `\degreeMonth{ May }`) is
    # tolerated — LaTeX compiles it identically, and stripping is the
    # principled comparison given how authors might format the macro.
    src = _VALID.replace(r"\degreeMonth{May}", f"\\degreeMonth{{{month}}}")
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F14" not in _rule_ids(issues)


@pytest.mark.parametrize(
    "override",
    [
        r"\setlength{\parindent}{0pt}",
        r"\setlength{\parindent}{0in}",
        r"\setlength{\parindent}{0em}",
        r"\setlength{\parindent}{0}",
        r"\setlength\parindent{0pt}",
        r"\parindent=0pt",
        r"\parindent=0in",
        r"\parindent = 0pt",
    ],
)
def test_parindent_zero_override_fires_uf_f7(tmp_path, override):
    # Catalog § UF-F7: \parindent set to zero (any unit) overrides the
    # template's \parindent=1cm (cls:1010). All these forms must fire.
    src = _VALID.replace(
        r"\begin{document}", override + "\n" + r"\begin{document}"
    )
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f7 = [f for f in issues.findings if f.rule_id == "UF-F7"]
    assert len(f7) == 1
    assert f7[0].severity == MUST_FIX


@pytest.mark.parametrize(
    "nonzero",
    [
        r"\setlength{\parindent}{1cm}",
        r"\setlength{\parindent}{0.5em}",  # nonzero with leading 0 in decimal
        r"\parindent=2em",
        r"\parindent=15pt",
    ],
)
def test_parindent_nonzero_does_not_fire_uf_f7(tmp_path, nonzero):
    # Nonzero values are allowed even when reinforcing the template.
    # \setlength{\parindent}{0.5em} starts with "0" but is decimal-nonzero —
    # detector must not naively fire on the leading 0.
    src = _VALID.replace(
        r"\begin{document}", nonzero + "\n" + r"\begin{document}"
    )
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F7" not in _rule_ids(issues)


def test_parindent_zero_in_comment_does_not_fire_uf_f7(tmp_path):
    src = _VALID.replace(
        r"\begin{document}",
        r"% \setlength{\parindent}{0pt} commented" + "\n" + r"\begin{document}",
    )
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F7" not in _rule_ids(issues)


@pytest.mark.parametrize(
    "args",
    [
        ("14pt", "16pt"),
        ("10pt", "12pt"),
        ("18pt", "22pt"),
    ],
)
def test_fontsize_selectfont_fires_uf_f3(tmp_path, args):
    body, baseline = args
    override = f"\\fontsize{{{body}}}{{{baseline}}}\\selectfont"
    src = _VALID.replace(r"\begin{document}", r"\begin{document}" + "\n" + override)
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f3 = [f for f in issues.findings if f.rule_id == "UF-F3"]
    assert len(f3) == 1
    assert override in (f3[0].observed or "")
    assert f3[0].severity == MUST_FIX


@pytest.mark.parametrize(
    "relative_size",
    [r"\small", r"\large", r"\Large", r"\tiny", r"\Huge"],
)
def test_relative_size_commands_do_not_fire_uf_f3_v01(tmp_path, relative_size):
    # Catalog scope: relative-size commands (\small, \large, etc.) ARE listed
    # as F3 overrides, but body-vs-caption/heading context distinction is
    # genuinely hard. v0.1 detector deliberately skips them; this test
    # pins the deferral so a future widening doesn't slip in unnoticed.
    src = _VALID.replace(r"\begin{document}", r"\begin{document}" + "\n" + relative_size)
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F3" not in _rule_ids(issues)


def test_fontsize_in_comment_does_not_fire_uf_f3(tmp_path):
    src = _VALID.replace(
        r"\begin{document}",
        r"\begin{document}" + "\n" + r"% \fontsize{14pt}{16pt}\selectfont as comment",
    )
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F3" not in _rule_ids(issues)


@pytest.mark.parametrize("override", [r"\justifying", r"\justify"])
def test_text_alignment_override_fires_uf_f5(tmp_path, override):
    # Catalog § UF-F5: \justifying and \justify override the template's
    # \raggedright (cls:171). Detector must catch both forms.
    src = _VALID.replace(r"\begin{document}", r"\begin{document}" + "\n" + override)
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f5 = [f for f in issues.findings if f.rule_id == "UF-F5"]
    assert len(f5) == 1
    assert override in (f5[0].observed or "")
    assert f5[0].severity == MUST_FIX


@pytest.mark.parametrize(
    "allowlist",
    [
        r"\sloppy",
        r"\sloppypar",
        r"\raggedright",  # reinforcing template's default is fine
    ],
)
def test_text_alignment_allowlist_does_not_fire_uf_f5(tmp_path, allowlist):
    # Catalog § UF-F5 allowlist: \sloppy / \sloppypar are line-breaking
    # helpers, not alignment overrides. \raggedright is the template's
    # own command; reinforcing it is harmless.
    src = _VALID.replace(r"\begin{document}", r"\begin{document}" + "\n" + allowlist)
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F5" not in _rule_ids(issues)


def test_sloppy_on_same_line_as_documentclass_does_not_fire_uf_f5(tmp_path):
    # Catalog § UF-F5 explicitly calls out the
    # `\documentclass[editMode]{ufdissertation}\sloppy` form (the bundled
    # UF example uses it). The allowlist must apply regardless of
    # position — same line as \documentclass included.
    src = _VALID.replace(
        r"\documentclass{ufdissertation}",
        r"\documentclass[editMode]{ufdissertation}\sloppy",
    )
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F5" not in _rule_ids(issues)


def test_justify_in_comment_does_not_fire_uf_f5(tmp_path):
    # Comment-stripping should hide \justify-in-comments from the
    # detector. A user writing "% TODO: should we \justify here?"
    # must not trip the rule.
    src = _VALID.replace(
        r"\begin{document}",
        r"\begin{document}" + "\n" + r"% TODO: should we \justify here?",
    )
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F5" not in _rule_ids(issues)


@pytest.mark.parametrize("month", ["February", "June", "Spring", "01", "may"])
def test_invalid_degree_month_value_fires_uf_f14(tmp_path, month):
    # Anything outside the enum (case-sensitive — "may" is invalid; UF
    # writes the month with title-case capitalization) trips F14.
    src = _VALID.replace(r"\degreeMonth{May}", f"\\degreeMonth{{{month}}}")
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f14 = [f for f in issues.findings if f.rule_id == "UF-F14"]
    assert any(month in (f.observed or "") for f in f14), (
        f"expected an F14 finding citing {month!r}; got: {[f.observed for f in f14]}"
    )
    assert all(f.severity == MUST_FIX for f in f14)


def test_fontsize_override_does_not_shadow_documentclass_for_d3(tmp_path):
    # Regression: F3's re.finditer loop used to assign to `m`, shadowing the
    # outer documentclass match `m` that D3 reads later. With both present,
    # D3 would silently fail to fire on overrideTitles. This test pins the
    # fix (loop var renamed to f3m).
    src = _VALID.replace(
        r"\documentclass{ufdissertation}",
        r"\documentclass[overrideTitles]{ufdissertation}",
    ).replace(
        r"\begin{document}",
        r"\begin{document}" + "\n" + r"\fontsize{14pt}{16pt}\selectfont",
    )
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    rule_ids = _rule_ids(issues)
    assert "UF-F3" in rule_ids
    assert "UF-D3" in rule_ids


def test_override_options_fire_uf_d3_review(tmp_path):
    # Both options present → one finding per option (each is independently
    # a candidate for removal at submission).
    src = _VALID.replace(
        r"\documentclass{ufdissertation}",
        r"\documentclass[overrideTitles,overrideChapters]{ufdissertation}",
    )
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    d3_findings = [f for f in issues.findings if f.rule_id == "UF-D3"]
    assert len(d3_findings) == 2
    assert {"overrideTitles", "overrideChapters"} == {
        f.observed.split(" ", 1)[0] for f in d3_findings if f.observed
    }
    assert all(f.severity == REVIEW for f in d3_findings)


def test_no_override_options_does_not_fire_uf_d3(tmp_path):
    # Negative case: a clean preamble must not trip D3 (guards against a
    # regex that matches anything containing the substring).
    master = _project(tmp_path, _VALID, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-D3" not in _rule_ids(issues)

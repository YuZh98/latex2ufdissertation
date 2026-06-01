from pathlib import Path

import pytest

from latex2ufdissertation.pipeline.checks import _setfile_arg, run_checks
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
\begin{document}\chapter{Introduction}\chapter{Main Body}\chapter{Closing Summary}\end{document}
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


@pytest.mark.parametrize(
    "src,expected",
    [
        (r"\setAbstractFile{abs}", "abs"),
        (r"\setAbstractFile[tex]{abs}", "abs"),
        (r"\setAbstractFile[txt]{abs}", "abs"),
        (r"\setAbstractFile [txt] {abs}", "abs"),
    ],
)
def test_setfile_arg_handles_optional_ext_bracket(src, expected):
    # \set*File macros accept an optional [ext] argument (cls:540-596),
    # e.g. \setAbstractFile[txt]{abs}. The name argument must parse the
    # same with or without the bracket; otherwise UF-F8 fires a false
    # "not set" finding on the legal bracket form.
    assert _setfile_arg(src, r"\setAbstractFile") == expected


def test_setfile_bracket_form_no_uf_f8_false_positive(tmp_path):
    # End-to-end guard: the optional [ext] bracket form flows through
    # run_checks without a spurious UF-F8 "not set" finding (and the
    # companion abs.tex exists, so no UF-P1 either).
    src = _VALID.replace(r"\setAbstractFile{abs}", r"\setAbstractFile[tex]{abs}")
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    abstract_findings = [
        f
        for f in issues.findings
        if f.rule_id in {"UF-F8", "UF-P1"} and "setAbstractFile" in (f.observed or "")
    ]
    assert not abstract_findings, [f.observed for f in abstract_findings]


@pytest.mark.parametrize(
    "macro,stem",
    [
        (r"\setCopyrightFile", "copyr"),
        (r"\setDedicationFile", "ded"),
        (r"\setAbbreviationsFile", "abbr"),
        (r"\setAppendixFile", "app"),
    ],
)
def test_optional_setfile_present_missing_companion_fires_uf_p1(tmp_path, macro, stem):
    # Optional \set*File macros (cls:540-596) are not required, but if the
    # user opts in by setting one, its companion file must exist (UF-P1).
    decl = f"{macro}{{{stem}}}"
    src = _VALID.replace(r"\begin{document}", decl + "\n" + r"\begin{document}")
    master = _project(tmp_path, src, _VALID_FILES)  # companion intentionally absent
    issues = Issues()
    run_checks(master, tmp_path, issues)
    p1 = [f for f in issues.findings if f.rule_id == "UF-P1" and macro in (f.observed or "")]
    assert p1, f"expected UF-P1 for {decl} with missing companion"
    assert all(f.severity == MUST_FIX for f in p1)


def test_absent_optional_setfile_does_not_fire_uf_f8(tmp_path):
    # Optional \set*File macros absent from source must NOT fire UF-F8
    # "not set"; only the four required macros do.
    master = _project(tmp_path, _VALID, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f8 = [f for f in issues.findings if f.rule_id == "UF-F8"]
    assert f8 == [], [f.observed for f in f8]


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
    src = _VALID.replace(r"\begin{document}", override + "\n" + r"\begin{document}")
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
    src = _VALID.replace(r"\begin{document}", nonzero + "\n" + r"\begin{document}")
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F7" not in _rule_ids(issues)


_VALID_BODY = r"\chapter{Introduction}\chapter{Main Body}\chapter{Closing Summary}"


def _with_body(body: str) -> str:
    """Replace the 3-chapter default body of _VALID with the given body."""
    return _VALID.replace(_VALID_BODY, body)


@pytest.mark.parametrize("count", [0, 1, 2])
def test_fewer_than_3_chapters_fires_uf_f10(tmp_path, count):
    # Catalog § UF-F10: minimum 3 chapters required (S1 + S3).
    chapters = "".join(f"\\chapter{{Chapter {i + 1}}}" for i in range(count))
    master = _project(tmp_path, _with_body(chapters), _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f10 = [f for f in issues.findings if f.rule_id == "UF-F10"]
    assert len(f10) == 1
    assert str(count) in (f10[0].observed or "")
    assert f10[0].severity == MUST_FIX


def test_3_chapters_in_main_does_not_fire_uf_f10(tmp_path):
    # _VALID baseline already has 3 chapters; F10 must not fire.
    master = _project(tmp_path, _VALID, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F10" not in _rule_ids(issues)


def test_chapters_counted_across_includes_for_uf_f10(tmp_path):
    # Three \include calls each pointing at a chapter file with one \chapter.
    # Detector must walk one level of \include / \input to count chapters.
    files = dict(_VALID_FILES)
    for i in range(1, 4):
        files[f"ch{i}.tex"] = f"\\chapter{{Chapter {i}}}\n"
    body = "".join(f"\\include{{ch{i}}}" for i in range(1, 4))
    master = _project(tmp_path, _with_body(body), files)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F10" not in _rule_ids(issues)


def test_chapters_in_comments_do_not_count_for_uf_f10(tmp_path):
    # Commented-out \chapter lines must not count toward the requirement.
    body = "% \\chapter{Commented one}\n% \\chapter{Commented two}\n\\chapter{Real one}"
    master = _project(tmp_path, _with_body(body), _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f10 = [f for f in issues.findings if f.rule_id == "UF-F10"]
    assert len(f10) == 1
    assert "1 chapter" in (f10[0].observed or "")


@pytest.mark.parametrize(
    "duplicate_lines,cmd_label",
    [
        (r"\setAbstractFile{abs2}", r"\setAbstractFile"),
        ("\\tableofcontents\n\\tableofcontents", r"\tableofcontents"),
        (r"\setReferenceFile{refs2}{plain}", r"\setReferenceFile"),
        (r"\bibliography{x}\bibliography{y}", r"\bibliography"),
    ],
)
def test_duplicate_singleton_fires_uf_f9(tmp_path, duplicate_lines, cmd_label):
    # Catalog § UF-F9: only one abstract, table of contents, and reference list.
    # Each duplication form emits exactly one F9 finding citing the duplicated command.
    src = _VALID.replace(r"\begin{document}", duplicate_lines + "\n" + r"\begin{document}")
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f9 = [f for f in issues.findings if f.rule_id == "UF-F9"]
    assert any(cmd_label in (f.observed or "") for f in f9), (
        f"expected F9 finding citing {cmd_label}; got: {[f.observed for f in f9]}"
    )
    assert all(f.severity == MUST_FIX for f in f9)


@pytest.mark.parametrize(
    "manual_chapter",
    [
        r"\chapter{ABSTRACT}",
        r"\chapter{REFERENCES}",
    ],
)
def test_manual_template_chapter_fires_uf_f9(tmp_path, manual_chapter):
    # Catalog § UF-F9: manual \chapter{ABSTRACT} / \chapter{REFERENCES} outside
    # template would duplicate sections the template auto-generates.
    body = "\\chapter{Intro}" + manual_chapter + "\\chapter{Body}\\chapter{Summary}"
    src = _VALID.replace(_VALID_BODY, body)
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f9 = [f for f in issues.findings if f.rule_id == "UF-F9"]
    assert f9, f"expected F9 finding for {manual_chapter}"
    assert any(manual_chapter in (f.observed or "") for f in f9)
    assert all(f.severity == MUST_FIX for f in f9)


def test_singleton_baseline_does_not_fire_uf_f9(tmp_path):
    # _VALID has one of each singleton macro; F9 must not fire.
    master = _project(tmp_path, _VALID, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F9" not in _rule_ids(issues)


@pytest.mark.parametrize(
    "section_cmd",
    [r"\chapter", r"\section", r"\subsection", r"\subsubsection", r"\paragraph"],
)
def test_titleformat_redefine_fires_uf_f11(tmp_path, section_cmd):
    # Catalog § UF-F11: \titleformat redefining any of the 5 tiers fires.
    override = f"\\titleformat{{{section_cmd}}}{{\\Large\\bfseries}}{{}}{{0pt}}{{}}"
    src = _VALID.replace(r"\begin{document}", override + "\n" + r"\begin{document}")
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f11 = [f for f in issues.findings if f.rule_id == "UF-F11"]
    assert len(f11) == 1
    assert section_cmd in (f11[0].observed or "")
    assert f11[0].severity == MUST_FIX


@pytest.mark.parametrize(
    "section_cmd",
    [r"\chapter", r"\section", r"\subsection"],
)
def test_titleformat_starred_form_also_fires_uf_f11(tmp_path, section_cmd):
    # titlesec's starred \titleformat* is the one-shot variant for a single
    # tier — functionally equivalent override. Pin both forms.
    override = f"\\titleformat*{{{section_cmd}}}{{\\Large\\bfseries}}"
    src = _VALID.replace(r"\begin{document}", override + "\n" + r"\begin{document}")
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f11 = [f for f in issues.findings if f.rule_id == "UF-F11"]
    assert len(f11) == 1
    assert section_cmd in (f11[0].observed or "")


def test_paragraph_usage_fires_uf_f11(tmp_path):
    # Catalog § UF-F11: \paragraph usage discouraged per C4.
    body = "\\chapter{Intro}\\paragraph{Heading}\\chapter{Body}\\chapter{Summary}"
    src = _VALID.replace(_VALID_BODY, body)
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f11 = [f for f in issues.findings if f.rule_id == "UF-F11"]
    assert f11
    assert any("paragraph" in (f.observed or "") for f in f11)


def test_section_subsection_subsubsection_dont_fire_uf_f11(tmp_path):
    # Catalog note: \section / \subsection / \subsubsection are the happy path.
    body = (
        "\\chapter{Intro}\\section{S}\\subsection{Sub}\\subsubsection{Subsub}"
        "\\chapter{Body}\\chapter{Summary}"
    )
    src = _VALID.replace(_VALID_BODY, body)
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F11" not in _rule_ids(issues)


def test_abstract_under_350_words_does_not_fire_uf_f15(tmp_path):
    files = dict(_VALID_FILES)
    files["abs.tex"] = " ".join(["word"] * 350) + "\n"
    master = _project(tmp_path, _VALID, files)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F15" not in _rule_ids(issues)


def test_abstract_over_350_words_fires_uf_f15(tmp_path):
    files = dict(_VALID_FILES)
    files["abs.tex"] = " ".join(["word"] * 351) + "\n"
    master = _project(tmp_path, _VALID, files)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f15 = [f for f in issues.findings if f.rule_id == "UF-F15"]
    assert len(f15) == 1
    assert "351" in (f15[0].observed or "")
    assert f15[0].severity == MUST_FIX


def test_abstract_word_count_strips_latex_commands_for_uf_f15(tmp_path):
    # \textbf{word} contributes 1 word ("word"), \\ doesn't. \LaTeX is a command,
    # also doesn't contribute. Detector must not over-count LaTeX commands.
    files = dict(_VALID_FILES)
    files["abs.tex"] = " ".join(["\\textbf{word}"] * 350) + "\n"
    master = _project(tmp_path, _VALID, files)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F15" not in _rule_ids(issues)


def test_abstract_missing_file_does_not_fire_uf_f15(tmp_path):
    # If abs.tex doesn't exist, UF-P1 handles that. F15 should silently skip.
    files = dict(_VALID_FILES)
    del files["abs.tex"]
    master = _project(tmp_path, _VALID, files)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F15" not in _rule_ids(issues)


def test_broken_label_reference_fires_uf_s3(tmp_path):
    body = (
        "\\chapter{Intro}\\label{chap:intro}"
        "See Chapter~\\ref{chap:nonexistent}."
        "\\chapter{Body}\\chapter{Summary}"
    )
    src = _VALID.replace(_VALID_BODY, body)
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    s3 = [f for f in issues.findings if f.rule_id == "UF-S3"]
    assert len(s3) == 1
    assert "chap:nonexistent" in (s3[0].observed or "")
    assert s3[0].severity == MUST_FIX


def test_resolved_label_reference_does_not_fire_uf_s3(tmp_path):
    body = (
        "\\chapter{Intro}\\label{chap:intro}"
        "See Chapter~\\ref{chap:intro}."
        "\\chapter{Body}\\chapter{Summary}"
    )
    src = _VALID.replace(_VALID_BODY, body)
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-S3" not in _rule_ids(issues)


def test_broken_cite_fires_uf_s3(tmp_path):
    body = "\\chapter{Intro}\\cite{missingKey} not in bib.\\chapter{Body}\\chapter{Summary}"
    src = _VALID.replace(_VALID_BODY, body)
    files = dict(_VALID_FILES)
    files["refs.bib"] = "@book{realKey, title={Real}}\n"
    master = _project(tmp_path, src, files)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    s3 = [f for f in issues.findings if f.rule_id == "UF-S3"]
    assert any("missingKey" in (f.observed or "") for f in s3)


def test_resolved_cite_does_not_fire_uf_s3(tmp_path):
    body = "\\chapter{Intro}\\cite{realKey} in bib.\\chapter{Body}\\chapter{Summary}"
    src = _VALID.replace(_VALID_BODY, body)
    files = dict(_VALID_FILES)
    files["refs.bib"] = "@book{realKey, title={Real}}\n"
    master = _project(tmp_path, src, files)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-S3" not in _rule_ids(issues)


def test_multi_cite_keys_in_one_call_resolve_independently_for_uf_s3(tmp_path):
    body = "\\chapter{Intro}\\cite{realKey,missingKey}\\chapter{Body}\\chapter{Summary}"
    src = _VALID.replace(_VALID_BODY, body)
    files = dict(_VALID_FILES)
    files["refs.bib"] = "@book{realKey, title={Real}}\n"
    master = _project(tmp_path, src, files)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    s3 = [f for f in issues.findings if f.rule_id == "UF-S3"]
    observed_all = " ".join(f.observed or "" for f in s3)
    assert "missingKey" in observed_all
    assert "realKey" not in observed_all


@pytest.mark.parametrize(
    "override",
    [
        r"\usepackage[margin=0.5in]{geometry}",
        r"\usepackage[left=2cm]{geometry}",
        r"\geometry{margin=0.5in}",
        r"\newgeometry{margin=0.5in}",
        r"\setlength{\textwidth}{7in}",
        r"\setlength{\textheight}{10in}",
        r"\hoffset=-1in",
        r"\voffset=-0.5in",
    ],
)
def test_margin_override_fires_uf_f1(tmp_path, override):
    src = _VALID.replace(r"\begin{document}", override + "\n" + r"\begin{document}")
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f1 = [f for f in issues.findings if f.rule_id == "UF-F1"]
    assert f1
    assert f1[0].severity == MUST_FIX


@pytest.mark.parametrize(
    "override",
    [
        r"\setmainfont{Comic Sans MS}",
        r"\usepackage{mathpazo}",
        r"\usepackage{mathptmx}",
        r"\usepackage{libertine}",
        r"\fontfamily{ppl}\selectfont",
    ],
)
def test_font_override_fires_uf_f2(tmp_path, override):
    src = _VALID.replace(r"\begin{document}", override + "\n" + r"\begin{document}")
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f2 = [f for f in issues.findings if f.rule_id == "UF-F2"]
    assert f2
    # Source-layer F2 is advisory (review); PDF layer is the authoritative must-fix.
    assert f2[0].severity == REVIEW


@pytest.mark.parametrize(
    "override",
    [
        r"\singlespacing",
        r"\onehalfspacing",
        r"\setstretch{1.2}",
        r"\renewcommand{\baselinestretch}{1.5}",
    ],
)
def test_linespacing_override_fires_uf_f4(tmp_path, override):
    body = "\\chapter{Intro}" + override + "\\chapter{Body}\\chapter{Summary}"
    src = _VALID.replace(_VALID_BODY, body)
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f4 = [f for f in issues.findings if f.rule_id == "UF-F4"]
    assert f4
    assert f4[0].severity == MUST_FIX


@pytest.mark.parametrize(
    "override",
    [
        r"\pagenumbering{roman}",
        r"\pagenumbering{Roman}",
        r"\pagenumbering{alph}",
        r"\pagenumbering{Alph}",
        r"\renewcommand{\thepage}{X-\arabic{page}}",
    ],
)
def test_pagenumbering_override_fires_uf_f6(tmp_path, override):
    body = "\\chapter{Intro}" + override + "\\chapter{Body}\\chapter{Summary}"
    src = _VALID.replace(_VALID_BODY, body)
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f6 = [f for f in issues.findings if f.rule_id == "UF-F6"]
    assert f6
    assert f6[0].severity == MUST_FIX


def test_multiple_f1_patterns_collapse_to_one_finding(tmp_path):
    # F1 detector emits at most 1 finding regardless of how many margin-
    # override patterns are present (same root cause). Pin the collapse.
    override = r"\geometry{margin=0.5in}" + "\n" + r"\hoffset=-1in"
    src = _VALID.replace(r"\begin{document}", override + "\n" + r"\begin{document}")
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f1 = [f for f in issues.findings if f.rule_id == "UF-F1"]
    assert len(f1) == 1


def test_multiple_f2_packages_emit_separate_findings(tmp_path):
    # F2 detector emits one finding per matched pattern (each package is
    # independently actionable). Pin the divergence from F1's collapse.
    override = r"\usepackage{mathpazo}" + "\n" + r"\usepackage{libertine}"
    src = _VALID.replace(r"\begin{document}", override + "\n" + r"\begin{document}")
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f2 = [f for f in issues.findings if f.rule_id == "UF-F2"]
    assert len(f2) == 2


def test_arabic_pagenumbering_does_not_fire_uf_f6(tmp_path):
    # \pagenumbering{arabic} matches the template's default; silent.
    body = "\\chapter{Intro}\\pagenumbering{arabic}\\chapter{Body}\\chapter{Summary}"
    src = _VALID.replace(_VALID_BODY, body)
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F6" not in _rule_ids(issues)


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


# ---------------------------------------------------------------------------
# Bug-fix regression tests
# ---------------------------------------------------------------------------


def test_f3_fontsize_in_verbatim_no_finding(tmp_path):
    # \fontsize inside \begin{verbatim} must not fire UF-F3.
    src = _VALID.replace(
        r"\begin{document}",
        "\\begin{document}\n\\begin{verbatim}\n\\fontsize{10}{12}\\selectfont\n\\end{verbatim}",
    )
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F3" not in _rule_ids(issues)


def test_s3_label_in_transitive_input_no_finding(tmp_path):
    # main → chapter1.tex → ch1body.tex where \label lives; \ref in main must resolve.
    master_src = (
        "\\documentclass{ufdissertation}\n"
        "\\title{X}\n\\author{Y}\n\\degreeType{Doctor of Philosophy}\n"
        "\\thesisType{Dissertation}\n\\degreeYear{2026}\n\\degreeMonth{May}\n"
        "\\major{Computer Science}\n\\chair{Advisor}\n"
        "\\setAcknowledgementsFile{ack}\n\\setAbstractFile{abs}\n"
        "\\setReferenceFile{refs}{agsm}\n\\setBiographicalFile{bio}\n"
        "\\begin{document}\n"
        "\\input{chapter1}\n"
        "\\ref{sec:deep}\n"
        "\\chapter{Main Body}\n\\chapter{Closing Summary}\n"
        "\\end{document}\n"
    )
    extra = dict(_VALID_FILES)
    extra["chapter1.tex"] = "\\chapter{Introduction}\n\\input{ch1body}\n"
    extra["ch1body.tex"] = "\\label{sec:deep}\nSome text.\n"
    master = _project(tmp_path, master_src, extra)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-S3" not in _rule_ids(issues)


def test_s3_citep_broken_key_fires(tmp_path):
    src = _VALID.replace(
        "\\chapter{Introduction}",
        "\\chapter{Introduction}\n\\citep{missing-key}",
    )
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    s3 = [f for f in issues.findings if f.rule_id == "UF-S3"]
    assert s3, "expected UF-S3 for \\citep{missing-key}"
    assert any("missing-key" in (f.observed or "") for f in s3)


def test_s3_string_entry_not_valid_cite_key_fires(tmp_path):
    # @string defines an abbreviation name, not a citable entry; \cite{JMLR} should fire.
    extra = dict(_VALID_FILES)
    extra["refs.bib"] = '@string{JMLR = "Journal of Machine Learning Research"}\n'
    src = _VALID.replace(
        "\\chapter{Introduction}",
        "\\chapter{Introduction}\n\\cite{JMLR}",
    )
    master = _project(tmp_path, src, extra)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    s3 = [f for f in issues.findings if f.rule_id == "UF-S3"]
    assert s3, "expected UF-S3 for \\cite{JMLR} with JMLR defined only as @string"
    assert any("JMLR" in (f.observed or "") for f in s3)


def test_f10_starred_chapter_counts(tmp_path):
    # \chapter*{...} must count toward the 3-chapter minimum.
    src = (
        "\\documentclass{ufdissertation}\n"
        "\\title{X}\n\\author{Y}\n\\degreeType{Doctor of Philosophy}\n"
        "\\thesisType{Dissertation}\n\\degreeYear{2026}\n\\degreeMonth{May}\n"
        "\\major{Computer Science}\n\\chair{Advisor}\n"
        "\\setAcknowledgementsFile{ack}\n\\setAbstractFile{abs}\n"
        "\\setReferenceFile{refs}{agsm}\n\\setBiographicalFile{bio}\n"
        "\\begin{document}\n"
        "\\chapter*{Introduction}\n\\chapter*{Main Body}\n\\chapter*{Closing Summary}\n"
        "\\end{document}\n"
    )
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F10" not in _rule_ids(issues)


def test_f2_multi_package_fires(tmp_path):
    # \usepackage{amsmath,mathpazo} must detect mathpazo even though it is not the sole argument.
    src = _VALID.replace(
        "\\begin{document}",
        "\\usepackage{amsmath,mathpazo}\n\\begin{document}",
    )
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f2 = [f for f in issues.findings if f.rule_id == "UF-F2"]
    assert f2, "expected UF-F2 for \\usepackage{amsmath,mathpazo}"
    assert any("mathpazo" in (f.observed or "") for f in f2)


def test_f7_observed_uses_actual_match_setlength(tmp_path):
    # observed must reflect the unit in source, not a hardcoded '0pt'.
    src = _VALID.replace(
        "\\begin{document}",
        "\\setlength{\\parindent}{0em}\n\\begin{document}",
    )
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f7 = [f for f in issues.findings if f.rule_id == "UF-F7"]
    assert f7, "expected UF-F7 for zero parindent"
    assert any("0em" in (f.observed or "") for f in f7)


def test_f7_observed_uses_actual_match_parindent_eq(tmp_path):
    # The assignment form \parindent=0em must also report the actual unit.
    src = _VALID.replace(
        "\\begin{document}",
        "\\parindent=0em\n\\begin{document}",
    )
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f7 = [f for f in issues.findings if f.rule_id == "UF-F7"]
    assert f7, "expected UF-F7 for zero parindent"
    assert any("0em" in (f.observed or "") for f in f7)


def test_f10_verbatim_chapter_in_included_file_not_counted(tmp_path):
    # \chapter inside verbatim in an included file must not count toward the chapter minimum.
    master_src = (
        "\\documentclass{ufdissertation}\n"
        "\\title{X}\n\\author{Y}\n\\degreeType{Doctor of Philosophy}\n"
        "\\thesisType{Dissertation}\n\\degreeYear{2026}\n\\degreeMonth{May}\n"
        "\\major{Computer Science}\n\\chair{Advisor}\n"
        "\\setAcknowledgementsFile{ack}\n\\setAbstractFile{abs}\n"
        "\\setReferenceFile{refs}{agsm}\n\\setBiographicalFile{bio}\n"
        "\\begin{document}\n"
        "\\chapter{Introduction}\n"
        "\\input{body}\n"
        "\\end{document}\n"
    )
    extra = dict(_VALID_FILES)
    # body.tex has one real chapter + one verbatim-wrapped chapter; only 1 should count.
    extra["body.tex"] = (
        "\\chapter{Closing Summary}\n\\begin{verbatim}\n\\chapter{Fake Chapter}\n\\end{verbatim}\n"
    )
    master = _project(tmp_path, master_src, extra)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    # 2 real chapters (Introduction + Closing Summary) → UF-F10 must fire (< 3).
    assert "UF-F10" in _rule_ids(issues)


def test_s3_bib_key_with_space_after_brace_resolves(tmp_path):
    # @article{ key, (space after brace) is valid BibTeX; cite must not fire UF-S3.
    extra = dict(_VALID_FILES)
    extra["refs.bib"] = "@article{ smith2023,\n  title = {Test},\n}\n"
    src = _VALID.replace(
        "\\chapter{Introduction}",
        "\\chapter{Introduction}\n\\cite{smith2023}",
    )
    master = _project(tmp_path, src, extra)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    s3 = [f for f in issues.findings if f.rule_id == "UF-S3"]
    assert not s3, f"unexpected UF-S3 for valid bib key with space after brace: {s3}"


def test_f3_fontsize_in_lstlisting_no_finding(tmp_path):
    # \fontsize inside \begin{lstlisting} must not fire UF-F3.
    src = _VALID.replace(
        r"\begin{document}",
        "\\begin{document}\n\\begin{lstlisting}\n\\fontsize{10}{12}\\selectfont\n\\end{lstlisting}",
    )
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F3" not in _rule_ids(issues)


def test_f15_verbatim_in_abstract_not_counted(tmp_path):
    # Words inside \begin{verbatim} in the abstract file must not count toward the 350-word limit.
    extra = dict(_VALID_FILES)
    # Abstract with 5 real words + a verbatim block of 350 words; total should stay <= 350.
    verbatim_words = " ".join(["word"] * 350)
    extra["abs.tex"] = (
        f"Real abstract content here.\n\\begin{{verbatim}}\n{verbatim_words}\n\\end{{verbatim}}\n"
    )
    master = _project(tmp_path, _VALID, extra)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert "UF-F15" not in _rule_ids(issues)


def test_f2_same_package_both_forms_emits_once(tmp_path):
    # Same forbidden package in both \usepackage{pkg} and \usepackage{pkg,other} must
    # emit exactly one UF-F2 finding.
    src = _VALID.replace(
        "\\begin{document}",
        "\\usepackage{mathpazo}\n\\usepackage{mathpazo,amsmath}\n\\begin{document}",
    )
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    f2 = [f for f in issues.findings if f.rule_id == "UF-F2" and "mathpazo" in (f.observed or "")]
    assert len(f2) == 1, f"expected exactly 1 UF-F2 for mathpazo, got {len(f2)}"

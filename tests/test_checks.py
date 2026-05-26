from pathlib import Path

import pytest

from pipeline.checks import run_checks
from pipeline.types import Issues


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


def test_valid_project_no_errors(tmp_path):
    master = _project(tmp_path, _VALID, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert issues.errors == []
    assert issues.warnings == []


def test_e1_wrong_class(tmp_path):
    src = r"\documentclass{article}" + "\n" + _VALID.split("\n", 1)[1]
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert any("wrong document class" in e for e in issues.errors)


@pytest.mark.parametrize(
    "cmd,msg_fragment",
    [
        (r"\title{X}", r"\title"),
        (r"\author{Y}", r"\author"),
        (r"\degreeType{Doctor of Philosophy}", r"\degreeType"),
        (r"\thesisType{Dissertation}", r"\thesisType"),
    ],
)
def test_missing_required_command(tmp_path, cmd, msg_fragment):
    src = _VALID.replace(cmd, "")
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert any(msg_fragment in e for e in issues.errors), f"no error mentioning {msg_fragment}"


@pytest.mark.parametrize(
    "set_cmd,file_name,msg_fragment",
    [
        (r"\setAcknowledgementsFile{ack}", "ack.tex", "Acknowledgements"),
        (r"\setAbstractFile{abs}", "abs.tex", "Abstract"),
        (r"\setReferenceFile{refs}{agsm}", "refs.bib", "Reference"),
        (r"\setBiographicalFile{bio}", "bio.tex", "Biographical"),
    ],
)
def test_missing_setfile_command(tmp_path, set_cmd, file_name, msg_fragment):
    src = _VALID.replace(set_cmd, "")
    files = dict(_VALID_FILES)
    files.pop(file_name, None)
    master = _project(tmp_path, src, files)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert any(msg_fragment in e for e in issues.errors)


@pytest.mark.parametrize(
    "file_name,msg_fragment",
    [
        ("ack.tex", "Acknowledgements"),
        ("abs.tex", "Abstract"),
        ("refs.bib", "Reference"),
        ("bio.tex", "Biographical"),
    ],
)
def test_missing_setfile_target_file(tmp_path, file_name, msg_fragment):
    files = {k: v for k, v in _VALID_FILES.items() if k != file_name}
    master = _project(tmp_path, _VALID, files)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert any(msg_fragment in e for e in issues.errors)


def test_w1_editmode_warn(tmp_path):
    src = _VALID.replace(
        r"\documentclass{ufdissertation}",
        r"\documentclass[editMode]{ufdissertation}",
    )
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert any("editMode" in w for w in issues.warnings)


def test_w2_pdflatex_magic_comment(tmp_path):
    src = "% !TEX program = pdflatex\n" + _VALID
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert any("LuaLaTeX" in w for w in issues.warnings)

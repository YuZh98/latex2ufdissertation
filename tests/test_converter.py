import json
import subprocess
import sys

_MIN_VALID = r"""\documentclass{ufdissertation}
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


def _run(*args, cwd=None):
    return subprocess.run(
        [sys.executable, "-m", "latex2ufdissertation.cli", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _make_valid_project(tmp_path):
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "master.tex").write_text(_MIN_VALID, encoding="utf-8")
    # Required companions carry minimal non-empty content: an empty required
    # companion now (correctly) raises the UF-P1 empty-content review advisory.
    for f in ("ack.tex", "abs.tex", "bio.tex"):
        (proj / f).write_text("Placeholder content.\n", encoding="utf-8")
    (proj / "refs.bib").write_text("@misc{placeholder, title={Placeholder}}\n", encoding="utf-8")
    return proj


def test_version():
    from importlib.metadata import version

    r = _run("--version")
    assert r.returncode == 0
    assert version("latex2ufdissertation") in r.stdout


def test_missing_input_returns_2(tmp_path):
    r = _run(str(tmp_path / "nope"))
    assert r.returncode == 2


def test_validate_valid_fixture(tmp_path):
    proj = _make_valid_project(tmp_path)
    r = _run(str(proj))
    assert r.returncode == 0, r.stderr + r.stdout


def test_validate_errors_exit_1(tmp_path):
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "master.tex").write_text(r"\documentclass{article}", encoding="utf-8")
    r = _run(str(proj))
    assert r.returncode == 1


def test_json_output_summary(tmp_path):
    proj = _make_valid_project(tmp_path)
    r = _run(str(proj), "--json")
    # stdout is JSON-only per the v1 contract; parse the whole thing.
    payload = json.loads(r.stdout)
    assert payload["schema_version"] == "1.0"
    assert payload["findings"] == []
    assert payload["summary"]["must_fix_count"] == 0
    assert payload["summary"]["review_count"] == 0
    assert payload["summary"]["exit_code"] == 0
    assert payload["summary"]["exit_reason"] == "clean"


def test_init_creates_target(tmp_path):
    target = tmp_path / "new-thesis"
    # Force bundled fallback so the test doesn't depend on network.
    r = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; from unittest.mock import patch; "
                "import latex2ufdissertation.pipeline.init as I; "
                "from latex2ufdissertation.cli import main; "
                "patcher = patch.object(I, '_fetch_remote', "
                "side_effect=ConnectionError('offline')); "
                "patcher.start(); "
                f"sys.exit(main(['--init', {str(target)!r}]))"
            ),
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert (target / "exampleMasterFile.tex").exists()

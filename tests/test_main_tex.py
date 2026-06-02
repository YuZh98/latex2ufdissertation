import pytest

from latex2ufdissertation.pipeline.main_tex import detect_main_tex, first_documentclass
from latex2ufdissertation.pipeline.types import ConverterError


@pytest.mark.parametrize(
    "text,expected",
    [
        (r"\documentclass{ufdissertation}", "ufdissertation"),
        (r"\documentclass[oneside,12pt]{ufdissertation}", "ufdissertation"),
        (r"\documentclass[oneside]{ufdissertation}", "ufdissertation"),
        (r"\documentclass{ ufdissertation }", "ufdissertation"),  # inner whitespace
        ("  \\documentclass{ufdissertation}", "ufdissertation"),  # leading indent
        (r"\documentclass{article}", "article"),
        ("% \\documentclass{ufdissertation}\n\\section{x}", None),  # commented out
        ("\\section{intro}\nsome ufdissertation prose", None),  # no documentclass
        ("foo\n\\documentclass{ufdissertation}", "ufdissertation"),  # not first line
    ],
)
def test_first_documentclass(text, expected):
    # Single source of truth shared by master auto-detection (_score) and the
    # bare-.tex input gate in cli.main — they must never drift on class detection.
    assert first_documentclass(text) == expected


def _write(d, name, content):
    p = d / name
    p.write_text(content, encoding="utf-8")
    return p


def test_detect_single_master(tmp_path):
    _write(
        tmp_path,
        "master.tex",
        r"\documentclass{ufdissertation}" + "\n\\setAbstractFile{a}",
    )
    _write(tmp_path, "chapter1.tex", "content")
    assert detect_main_tex(tmp_path) == tmp_path / "master.tex"


def test_detect_prefers_setfile_count(tmp_path):
    _write(tmp_path, "draft.tex", r"\documentclass{ufdissertation}")
    _write(
        tmp_path,
        "real.tex",
        r"\documentclass{ufdissertation}"
        + "\n"
        + r"\setAbstractFile{a}"
        + "\n"
        + r"\setBiographicalFile{b}",
    )
    assert detect_main_tex(tmp_path) == tmp_path / "real.tex"


def test_detect_with_explicit_hint(tmp_path):
    _write(tmp_path, "a.tex", r"\documentclass{ufdissertation}")
    _write(tmp_path, "b.tex", r"\documentclass{ufdissertation}")
    assert detect_main_tex(tmp_path, hint="b.tex") == tmp_path / "b.tex"


def test_detect_explicit_hint_missing_raises(tmp_path):
    with pytest.raises(ConverterError):
        detect_main_tex(tmp_path, hint="nope.tex")


def test_detect_no_master_raises(tmp_path):
    _write(tmp_path, "only.tex", r"\input{other}")  # no \documentclass at all
    with pytest.raises(ConverterError):
        detect_main_tex(tmp_path)


def test_detect_prefers_ufd_over_other_class(tmp_path):
    _write(tmp_path, "article.tex", r"\documentclass{article}")
    _write(tmp_path, "ufd.tex", r"\documentclass{ufdissertation}")
    assert detect_main_tex(tmp_path) == tmp_path / "ufd.tex"


def test_detect_returns_non_ufd_master_when_only_choice(tmp_path):
    # If no ufdissertation master exists, still return the best candidate
    # so checks.py can fire E1 (wrong document class).
    p = _write(tmp_path, "article.tex", r"\documentclass{article}")
    assert detect_main_tex(tmp_path) == p


def test_detect_ignores_documentclass_in_verb_blocks(tmp_path):
    """A documentation file that starts with \\documentclass{article} but
    mentions \\documentclass[editMode]{ufdissertation} inside \\verb|...|
    must not outrank the real master."""
    _write(
        tmp_path,
        "master.tex",
        r"\documentclass[editMode]{ufdissertation}" + "\n" + r"\setAbstractFile{a}",
    )
    _write(
        tmp_path,
        "docs.tex",
        r"\documentclass{article}"
        + "\n"
        + r"Example: \verb|\documentclass[editMode]{ufdissertation}|"
        + "\n"
        + r"with \setAbstractFile{x} \setAcknowledgementsFile{y} "
        r"\setReferenceFile{z}{agsm} \setBiographicalFile{w}",
    )
    assert detect_main_tex(tmp_path) == tmp_path / "master.tex"


def test_detect_skips_commented_documentclass(tmp_path):
    _write(tmp_path, "real.tex", r"\documentclass{ufdissertation}")
    _write(tmp_path, "fake.tex", "% \\documentclass{ufdissertation}")
    assert detect_main_tex(tmp_path) == tmp_path / "real.tex"


# ---------------------------------------------------------------------------
# Robustness: path-escape, non-file hints, and dash-prefix names
# ---------------------------------------------------------------------------


def test_detect_hint_outside_root_raises(tmp_path):
    """A hint that resolves outside root must raise ConverterError, not ValueError."""
    from latex2ufdissertation.pipeline.types import ConverterError

    _write(tmp_path, "real.tex", r"\documentclass{ufdissertation}")
    with pytest.raises(ConverterError, match="outside"):
        detect_main_tex(tmp_path, hint="/etc/passwd")


def test_detect_hint_not_a_file_raises(tmp_path):
    """A hint pointing at a directory must raise ConverterError."""
    from latex2ufdissertation.pipeline.types import ConverterError

    sub = tmp_path / "subdir"
    sub.mkdir()
    with pytest.raises(ConverterError):
        detect_main_tex(tmp_path, hint="subdir")


def test_detect_hint_nonexistent_raises(tmp_path):
    """A hint that does not exist must raise ConverterError."""
    from latex2ufdissertation.pipeline.types import ConverterError

    _write(tmp_path, "real.tex", r"\documentclass{ufdissertation}")
    with pytest.raises(ConverterError):
        detect_main_tex(tmp_path, hint="ghost.tex")


def test_detect_hint_dash_prefix_raises(tmp_path):
    """A master whose filename starts with '-' must be rejected as a subprocess-injection risk."""
    from latex2ufdissertation.pipeline.types import ConverterError

    _write(tmp_path, "-x.tex", r"\documentclass{ufdissertation}")
    with pytest.raises(ConverterError, match=r"-"):
        detect_main_tex(tmp_path, hint="-x.tex")


def test_detect_autodiscovered_dash_prefix_skipped(tmp_path):
    """Auto-discovery must skip (not return) any .tex file whose name starts with '-'."""
    from latex2ufdissertation.pipeline.types import ConverterError

    _write(tmp_path, "-x.tex", r"\documentclass{ufdissertation}")
    # Only the dash-prefixed file exists; no safe master → ConverterError
    with pytest.raises(ConverterError):
        detect_main_tex(tmp_path)

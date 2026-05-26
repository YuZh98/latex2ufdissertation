import pytest

from pipeline.main_tex import detect_main_tex
from pipeline.types import ConverterError


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
    _write(tmp_path, "only.tex", r"\documentclass{article}")
    with pytest.raises(ConverterError):
        detect_main_tex(tmp_path)


def test_detect_skips_commented_documentclass(tmp_path):
    _write(tmp_path, "real.tex", r"\documentclass{ufdissertation}")
    _write(tmp_path, "fake.tex", "% \\documentclass{ufdissertation}")
    assert detect_main_tex(tmp_path) == tmp_path / "real.tex"

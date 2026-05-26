from unittest.mock import patch

from latex2ufdissertation.pipeline.build import format_errors, lualatex_available


def test_format_errors_extracts_bang_blocks():
    log = """
Some preamble noise
! Undefined control sequence.
l.42 \\nosuchcmd
                  next line of context
! Missing $ inserted.
l.99 $1+1
        end
"""
    formatted = format_errors(log)
    assert "! Undefined control sequence." in formatted
    assert "l.42" in formatted
    assert "! Missing $ inserted." in formatted


def test_format_errors_caps_at_5_blocks():
    log = "\n".join([f"! Error {i}.\nl.{i} bad" for i in range(10)])
    formatted = format_errors(log)
    blocks = formatted.count("! Error ")
    assert blocks == 5


def test_format_errors_empty():
    assert format_errors("") == ""
    assert format_errors("no errors here") == ""


def test_lualatex_available_when_installed():
    with patch(
        "latex2ufdissertation.pipeline.build.shutil.which", return_value="/usr/bin/lualatex"
    ):
        assert lualatex_available()


def test_lualatex_unavailable_when_missing():
    with patch("latex2ufdissertation.pipeline.build.shutil.which", return_value=None):
        assert not lualatex_available()

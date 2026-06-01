import subprocess
from unittest.mock import patch

from latex2ufdissertation.pipeline.build import compile_pdf, format_errors, lualatex_available


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


def test_compile_pdf_runs_in_master_dir_with_detached_stdin(tmp_path):
    """Regression: a master in a subdirectory must compile in its own directory.

    Previously compile ran with ``cwd=<project root>`` and a bare ``main.tex``,
    so a master at ``root/input/main.tex`` failed with "can't find main.tex" and
    could prompt for input on a TTY. Compilation must run in ``main_tex.parent``
    with ``stdin`` detached.
    """
    sub = tmp_path / "input"
    sub.mkdir()
    master = sub / "main.tex"
    master.write_text("\\documentclass{ufdissertation}\n")
    output = tmp_path / "out.pdf"

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        (sub / "main.pdf").write_bytes(b"%PDF-1.5\n")  # emulate lualatex output

        class _Result:
            stdout = b""
            stderr = b""

        return _Result()

    with (
        patch("latex2ufdissertation.pipeline.build.lualatex_available", return_value=True),
        patch("latex2ufdissertation.pipeline.build.biber_available", return_value=False),
        patch("latex2ufdissertation.pipeline.build.subprocess.run", side_effect=fake_run),
    ):
        result = compile_pdf(master, output, open_pdf=False)

    assert result == output
    assert output.exists()
    lualatex_call = next(c for c in calls if c[0][0] == "lualatex")
    assert lualatex_call[1]["cwd"] == sub
    assert lualatex_call[1]["stdin"] is subprocess.DEVNULL
    assert lualatex_call[0][-1] == "main.tex"

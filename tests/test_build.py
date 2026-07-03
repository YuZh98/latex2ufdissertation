import subprocess
from unittest.mock import patch

import pytest

from latex2ufdissertation.pipeline.build import compile_pdf, format_errors, lualatex_available
from latex2ufdissertation.pipeline.types import ConverterError


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
            returncode = 0
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


# ---------------------------------------------------------------------------
# Security: flag-injection (item 4)
# ---------------------------------------------------------------------------


def test_compile_pdf_rejects_flag_injection_filename(tmp_path):
    """A master .tex filename starting with '-' must raise ConverterError before
    any subprocess is launched — prevents flag injection into lualatex/biber."""
    evil = tmp_path / "-x.tex"
    evil.write_text("\\documentclass{ufdissertation}\n")
    output = tmp_path / "out.pdf"

    with (
        patch("latex2ufdissertation.pipeline.build.lualatex_available", return_value=True),
        patch("latex2ufdissertation.pipeline.build.subprocess.run") as mock_run,
    ):
        with pytest.raises(ConverterError, match="unsafe master filename"):
            compile_pdf(evil, output, open_pdf=False)
        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# Security: lualatex hardening flags and env (item 5)
# ---------------------------------------------------------------------------


def test_compile_pdf_lualatex_hardening_flags_and_env(tmp_path):
    """-no-shell-escape must be in argv, and env must restrict shell/file ops."""
    sub = tmp_path / "src"
    sub.mkdir()
    master = sub / "main.tex"
    master.write_text("\\documentclass{ufdissertation}\n")
    output = tmp_path / "out.pdf"

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        (sub / "main.pdf").write_bytes(b"%PDF-1.5\n")

        class _Result:
            returncode = 0
            stdout = b""
            stderr = b""

        return _Result()

    with (
        patch("latex2ufdissertation.pipeline.build.lualatex_available", return_value=True),
        patch("latex2ufdissertation.pipeline.build.biber_available", return_value=False),
        patch("latex2ufdissertation.pipeline.build.subprocess.run", side_effect=fake_run),
    ):
        compile_pdf(master, output, open_pdf=False)

    lualatex_call = next(c for c in calls if c[0][0] == "lualatex")
    cmd = lualatex_call[0]
    env = lualatex_call[1]["env"]

    assert "-no-shell-escape" in cmd
    assert cmd[-1] == "main.tex"  # filename stays last
    assert env["shell_escape"] == "f"
    assert env["openin_any"] == "p"
    assert env["openout_any"] == "p"


# ---------------------------------------------------------------------------
# Security: biber TimeoutExpired (item 6)
# ---------------------------------------------------------------------------


def test_compile_pdf_biber_timeout_raises_converter_error(tmp_path):
    """biber TimeoutExpired must be caught and re-raised as ConverterError."""
    sub = tmp_path / "src"
    sub.mkdir()
    master = sub / "main.tex"
    master.write_text("\\documentclass{ufdissertation}\n")
    output = tmp_path / "out.pdf"

    bcf = sub / "main.bcf"
    bcf.write_text("")  # trigger biber branch

    call_count = [0]

    def fake_run(cmd, **kwargs):
        call_count[0] += 1
        if cmd[0] == "biber":
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=600)

        class _Result:
            returncode = 0
            stdout = b""
            stderr = b""

        return _Result()

    with (
        patch("latex2ufdissertation.pipeline.build.lualatex_available", return_value=True),
        patch("latex2ufdissertation.pipeline.build.biber_available", return_value=True),
        patch("latex2ufdissertation.pipeline.build.subprocess.run", side_effect=fake_run),
    ):
        with pytest.raises(ConverterError, match="biber timed out"):
            compile_pdf(master, output, open_pdf=False)


# ---------------------------------------------------------------------------
# Silent-failure surfacing: non-zero subprocess exits must warn to stderr
# ---------------------------------------------------------------------------


def _fake_result(returncode: int):
    class _Result:
        stdout = b""
        stderr = b""

    _Result.returncode = returncode
    return _Result()


def test_compile_pdf_warns_on_lualatex_nonzero_returncode(tmp_path, capsys):
    """A non-zero lualatex exit must surface a stderr warning (a stale pass-1
    PDF from a prior run could otherwise be silently accepted as success)."""
    sub = tmp_path / "src"
    sub.mkdir()
    master = sub / "main.tex"
    master.write_text("\\documentclass{ufdissertation}\n")
    output = tmp_path / "out.pdf"

    def fake_run(cmd, **kwargs):
        (sub / "main.pdf").write_bytes(b"%PDF-1.5\n")
        return _fake_result(1)

    with (
        patch("latex2ufdissertation.pipeline.build.lualatex_available", return_value=True),
        patch("latex2ufdissertation.pipeline.build.biber_available", return_value=False),
        patch("latex2ufdissertation.pipeline.build.subprocess.run", side_effect=fake_run),
    ):
        result = compile_pdf(master, output, open_pdf=False)

    # Non-fatal: the 3-pass loop still completes and the PDF is produced.
    assert result == output
    err = capsys.readouterr().err
    assert "lualatex" in err
    assert "1" in err


def test_compile_pdf_warns_on_biber_nonzero_returncode(tmp_path, capsys):
    """A non-zero biber exit must surface a stderr warning (otherwise the PDF
    ships with unresolved [?]/[0] citation placeholders and no signal)."""
    sub = tmp_path / "src"
    sub.mkdir()
    master = sub / "main.tex"
    master.write_text("\\documentclass{ufdissertation}\n")
    output = tmp_path / "out.pdf"
    (sub / "main.bcf").write_text("")  # trigger biber branch

    def fake_run(cmd, **kwargs):
        (sub / "main.pdf").write_bytes(b"%PDF-1.5\n")
        return _fake_result(2 if cmd[0] == "biber" else 0)

    with (
        patch("latex2ufdissertation.pipeline.build.lualatex_available", return_value=True),
        patch("latex2ufdissertation.pipeline.build.biber_available", return_value=True),
        patch("latex2ufdissertation.pipeline.build.subprocess.run", side_effect=fake_run),
    ):
        result = compile_pdf(master, output, open_pdf=False)

    assert result == output
    err = capsys.readouterr().err
    assert "biber" in err

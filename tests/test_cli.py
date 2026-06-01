"""Smoke tests for the CLI argument-parsing layer."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from latex2ufdissertation.cli import (
    DEMO_GITHUB_URL,
    _build_parser,
    _find_bundled_pdf,
    _print_demo_location,
    main,
)


def test_parser_accepts_demo_flag() -> None:
    args = _build_parser().parse_args(["--demo"])
    assert args.demo is True
    assert args.input is None


def test_print_demo_location_returns_zero(capsys: pytest.CaptureFixture[str]) -> None:
    rc = _print_demo_location()
    assert rc == 0
    out = capsys.readouterr().out
    assert DEMO_GITHUB_URL in out
    assert "demo dissertation" in out.lower()


def test_main_demo_flag_short_circuits(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["--demo"])
    assert rc == 0
    assert DEMO_GITHUB_URL in capsys.readouterr().out


def test_main_without_input_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main([])
    assert rc == 2
    assert "INPUT required" in capsys.readouterr().err


def test_version_flag_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0


def test_main_json_directory_input_reports_detected_mode_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # End-to-end wiring: cli.main must classify a directory input and thread
    # detected_mode into the JSON payload.
    (tmp_path / "main.tex").write_text(
        r"\documentclass{ufdissertation}" + "\n\\begin{document}\n\\end{document}\n",
        encoding="utf-8",
    )
    rc = main(["--json", "--dry-run", str(tmp_path)])
    payload = json.loads(capsys.readouterr().out)
    assert payload["detected_mode"] == "dir"
    assert payload["input"] == str(tmp_path)
    assert rc in (0, 1)  # findings may or may not fire; mode is the assertion


def test_main_json_pdf_input_reports_pdf_mode_and_unreadable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A malformed PDF stub (missing /Root) is routed through the PDF layer
    # (v1.0 pdf-input mode). pdfminer raises PDFSyntaxError which the PDF
    # layer converts to UnreadableInput → exit 2 / unreadable_input.
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    rc = main(["--json", str(pdf)])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert payload["detected_mode"] == "pdf"
    assert payload["summary"]["exit_reason"] == "unreadable_input"


def test_issues_add_goes_to_stderr_not_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # README + spec promise --json stdout stays a single JSON document.
    # Progress / diagnostic messages MUST land on stderr so downstream
    # `json.loads(stdout)` does not break.
    from latex2ufdissertation.pipeline.types import Issues

    issues = Issues()
    issues.add("UF-F13", observed="bad class")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "UF-F13" in captured.err


# ---------------------------------------------------------------------------
# Bug 1: --main path escape
# ---------------------------------------------------------------------------


def test_main_outside_root_exits_2_no_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--main pointing outside root must exit 2 with a clean message, no ValueError."""
    (tmp_path / "main.tex").write_text(r"\documentclass{ufdissertation}", encoding="utf-8")
    rc = main(["--dry-run", "--main", "/etc/passwd", str(tmp_path)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "Error:" in err
    # The raw ValueError message must NOT appear
    assert "relative_to" not in err
    assert "ValueError" not in err


def test_main_outside_root_json_is_valid(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--json --main <outside root> must emit valid JSON to stdout."""
    (tmp_path / "main.tex").write_text(r"\documentclass{ufdissertation}", encoding="utf-8")
    rc = main(["--json", "--dry-run", "--main", "/etc/passwd", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    payload = json.loads(out)  # must not raise
    assert payload["summary"]["exit_reason"] == "unreadable_input"


def test_main_nonexistent_file_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--main pointing at a non-existent file must exit 2 cleanly."""
    (tmp_path / "main.tex").write_text(r"\documentclass{ufdissertation}", encoding="utf-8")
    rc = main(["--dry-run", "--main", "ghost.tex", str(tmp_path)])
    assert rc == 2
    assert "Error:" in capsys.readouterr().err


def test_main_hint_not_a_file_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--main pointing at a directory must exit 2 cleanly."""
    sub = tmp_path / "subdir"
    sub.mkdir()
    rc = main(["--dry-run", "--main", "subdir", str(tmp_path)])
    assert rc == 2
    assert "Error:" in capsys.readouterr().err


def test_main_dash_prefix_hint_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--main with a dash-prefix name must be rejected.

    argparse treats '-x.tex' as an unknown flag and itself raises SystemExit(2)
    before detect_main_tex is reached, which is an acceptable rejection at the
    CLI boundary.  The detect_main_tex-level check guards the programmatic API.
    """
    (tmp_path / "-x.tex").write_text(r"\documentclass{ufdissertation}", encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        main(["--dry-run", "--main", "-x.tex", str(tmp_path)])
    assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# Bug 2: --init into unwritable directory
# ---------------------------------------------------------------------------


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses chmod restrictions")
def test_init_unwritable_dir_exits_2_no_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--init into a read-only parent must exit 2, clean message, no PermissionError traceback."""
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o555)
    try:
        target = str(locked / "newproject")
        rc = main(["--init", target])
        assert rc == 2
        err = capsys.readouterr().err
        assert "Error:" in err
        assert "Traceback" not in err
        assert "PermissionError" not in err
    finally:
        locked.chmod(0o755)


# ---------------------------------------------------------------------------
# Bug 3: --json contract on all error paths
# ---------------------------------------------------------------------------


def test_json_contract_resolve_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A missing input with --json must emit valid JSON to stdout."""
    rc = main(["--json", "--dry-run", str(tmp_path / "nonexistent.zip")])
    assert rc == 2
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert "summary" in payload


def test_json_contract_detect_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A dir with no .tex master + --json must emit valid JSON to stdout."""
    (tmp_path / "empty.txt").write_text("hello", encoding="utf-8")
    rc = main(["--json", "--dry-run", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert "summary" in payload


_THESIS_MAIN = (
    r"\documentclass{ufdissertation}"
    + "\n"
    + r"\thesisType{Thesis}"
    + "\n\\begin{document}\n\\end{document}\n"
)


def test_thesis_input_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A \\thesisType{Thesis} project must exit 2 (master's theses out of scope)."""
    (tmp_path / "main.tex").write_text(_THESIS_MAIN, encoding="utf-8")
    rc = main(["--dry-run", str(tmp_path)])
    assert rc == 2


def test_thesis_input_json_is_valid_and_reports_reason(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The thesis-refusal path with --json must emit valid JSON with
    exit_reason == thesis_input."""
    (tmp_path / "main.tex").write_text(_THESIS_MAIN, encoding="utf-8")
    rc = main(["--json", "--dry-run", str(tmp_path)])
    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["exit_reason"] == "thesis_input"


def test_json_contract_missing_toolchain(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When lualatex is missing + --json must emit valid JSON to stdout."""
    (tmp_path / "main.tex").write_text(r"\documentclass{ufdissertation}", encoding="utf-8")
    monkeypatch.setattr("latex2ufdissertation.cli.lualatex_available", lambda: False)
    rc = main(["--json", str(tmp_path)])
    assert rc == 3
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["summary"]["exit_reason"] == "missing_toolchain"


def test_json_contract_compile_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A compile failure under --json must emit valid JSON with exit_reason compile_failure."""
    from latex2ufdissertation.pipeline.types import ConverterError

    (tmp_path / "main.tex").write_text(r"\documentclass{ufdissertation}", encoding="utf-8")
    monkeypatch.setattr("latex2ufdissertation.cli.lualatex_available", lambda: True)
    monkeypatch.setattr(
        "latex2ufdissertation.cli.compile_pdf",
        lambda *a, **k: (_ for _ in ()).throw(ConverterError("boom")),
    )
    rc = main(["--json", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["summary"]["exit_reason"] == "compile_failure"


def test_json_init_scope_out(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--init + --json emits nothing to stdout (no validation state exists yet).

    The --json single-document contract is scoped to the validation/conversion
    flow. Scaffolding (--init) has no exit_reason and deliberately emits no JSON.
    """
    # Force --init to fail immediately with PermissionError (skip if root).
    if os.geteuid() == 0:
        pytest.skip("root bypasses chmod restrictions")
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o555)
    try:
        rc = main(["--json", "--init", str(locked / "newproject")])
        assert rc == 2
        assert capsys.readouterr().out == ""
    finally:
        locked.chmod(0o755)


# ---------------------------------------------------------------------------
# Bug 4: _find_bundled_pdf searches master's parent dir
# ---------------------------------------------------------------------------


def test_find_bundled_pdf_in_master_parent_dir(tmp_path: Path) -> None:
    """A PDF next to a subdir master must be found."""
    src = tmp_path / "src"
    src.mkdir()
    master = src / "main.tex"
    master.write_text(r"\documentclass{ufdissertation}", encoding="utf-8")
    pdf = src / "main.pdf"
    pdf.write_bytes(b"%PDF-1.7")
    found = _find_bundled_pdf(tmp_path, master)
    assert found == pdf


def test_find_bundled_pdf_root_fallback(tmp_path: Path) -> None:
    """When no PDF is in master's dir, fall back to root."""
    src = tmp_path / "src"
    src.mkdir()
    master = src / "thesis.tex"
    master.write_text(r"\documentclass{ufdissertation}", encoding="utf-8")
    pdf = tmp_path / "main.pdf"
    pdf.write_bytes(b"%PDF-1.7")
    found = _find_bundled_pdf(tmp_path, master)
    assert found == pdf


def test_find_bundled_pdf_master_dir_priority(tmp_path: Path) -> None:
    """PDF in master's dir takes priority over one with the same name in root."""
    src = tmp_path / "src"
    src.mkdir()
    master = src / "main.tex"
    master.write_text(r"\documentclass{ufdissertation}", encoding="utf-8")
    root_pdf = tmp_path / "main.pdf"
    root_pdf.write_bytes(b"%PDF-1.7 root")
    master_pdf = src / "main.pdf"
    master_pdf.write_bytes(b"%PDF-1.7 master")
    found = _find_bundled_pdf(tmp_path, master)
    assert found == master_pdf


def test_find_bundled_pdf_returns_none_when_absent(tmp_path: Path) -> None:
    """Returns None when no PDF exists anywhere."""
    src = tmp_path / "src"
    src.mkdir()
    master = src / "thesis.tex"
    master.write_text(r"\documentclass{ufdissertation}", encoding="utf-8")
    assert _find_bundled_pdf(tmp_path, master) is None


# ---------------------------------------------------------------------------
# Bug 5: --version matches pyproject.toml
# ---------------------------------------------------------------------------


def test_version_matches_importlib_metadata() -> None:
    """__version__ must equal the version in importlib.metadata (i.e. pyproject.toml)."""
    from importlib.metadata import version

    from latex2ufdissertation import __version__

    assert __version__ == version("latex2ufdissertation")

"""Smoke tests for the CLI argument-parsing layer."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

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


# ---------------------------------------------------------------------------
# Gate 4: git-input mode end-to-end (clone mocked, full pipeline exercised)
# ---------------------------------------------------------------------------

_DEMO_DIR = Path(__file__).resolve().parent.parent / "examples" / "demo_dissertation"
_DEMO_AVAILABLE_FOR_GIT = pytest.mark.skipif(
    not _DEMO_DIR.is_dir(), reason="demo_dissertation directory not present"
)


@_DEMO_AVAILABLE_FOR_GIT
def test_git_input_mode_end_to_end(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Gate 4 — git input: full pipeline with a mocked clone.

    resolve._clone_git calls subprocess.run with
      ["git", "clone", "--depth", "1", url, dest].
    We intercept that call, copy the demo project into dest (which mkdtemp
    already created), and return a zero CompletedProcess.  Everything after
    the clone — detect_main_tex, run_checks, emit_report — runs for real.

    Assertions:
    - detected_mode == "git" in the JSON payload.
    - Exit code 0 (demo satisfies all source-layer must-fix rules; --dry-run
      skips compilation and PDF checks).
    - The temp clone directory is cleaned up by the time main() returns.
    """
    git_url = "https://github.com/someuser/somerepo.git"
    recorded_dirs: list[str] = []
    real_mkdtemp = tempfile.mkdtemp

    def spy_mkdtemp(**kwargs: object) -> str:
        d = real_mkdtemp(**kwargs)
        recorded_dirs.append(d)
        return d

    def fake_clone(
        cmd: list[str], *args: object, **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        dest = Path(cmd[-1])
        shutil.copytree(str(_DEMO_DIR), str(dest), dirs_exist_ok=True)
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    with (
        patch(
            "latex2ufdissertation.pipeline.resolve.subprocess.run",
            side_effect=fake_clone,
        ),
        patch(
            "latex2ufdissertation.pipeline.resolve.tempfile.mkdtemp",
            side_effect=spy_mkdtemp,
        ),
    ):
        rc = main(["--json", "--dry-run", git_url])

    payload = json.loads(capsys.readouterr().out)

    # detected_mode must be "git" — set from input_mode(url) before the clone.
    assert payload["detected_mode"] == "git", (
        f"expected detected_mode='git', got {payload['detected_mode']!r}"
    )

    # Exit 0: demo satisfies every source-layer must-fix rule under --dry-run.
    assert rc == 0, (
        f"expected exit 0 for clean demo via git input, got {rc}; findings: {payload['findings']}"
    )

    # Temp clone dir must be cleaned up (finally: cleanup() in cli.main).
    for d in recorded_dirs:
        assert not Path(d).exists(), f"git clone temp dir was not cleaned up: {d}"


# ---------------------------------------------------------------------------
# A1: Corrupt/non-zip .zip input through CLI → exit 2 + valid JSON
# ---------------------------------------------------------------------------


def test_corrupt_zip_cli_exits_2_with_valid_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A corrupt (non-zip) .zip file passed to the CLI must exit 2 and emit
    a single valid JSON document on stdout when --json is used.

    Regression: resolve() raises UnreadableInput on BadZipFile; cli.main()
    must catch it, set exit_reason=unreadable_input, and emit valid JSON.
    Distinct from the existing 'nonexistent.zip' test which hits the
    FileNotFoundError branch — this exercises the BadZipFile branch.
    """
    corrupt = tmp_path / "corrupt.zip"
    corrupt.write_bytes(b"this is not a zip file at all")
    rc = main(["--json", str(corrupt)])
    assert rc == 2
    out = capsys.readouterr().out
    payload = json.loads(out)  # must not raise — exactly one JSON document
    assert payload["summary"]["exit_reason"] == "unreadable_input"


def test_corrupt_zip_cli_no_traceback_on_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A corrupt .zip must produce a friendly error on stderr, no raw traceback."""
    corrupt = tmp_path / "corrupt.zip"
    corrupt.write_bytes(b"garbage")
    main([str(corrupt)])
    err = capsys.readouterr().err
    assert "Error:" in err
    assert "Traceback" not in err
    assert "BadZipFile" not in err


# ---------------------------------------------------------------------------
# A4: Non-PDF binary file with .pdf suffix → exit 2 + valid JSON, no traceback
# ---------------------------------------------------------------------------


def test_binary_non_pdf_file_exits_2_with_valid_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A file with a .pdf extension that contains binary garbage (no PDF header)
    must exit 2 and emit valid JSON with exit_reason=unreadable_input under --json.

    Distinct from the existing %PDF-1.7 stub test: that file has a PDF header
    and fails at /Root parsing; this file has no PDF structure at all.
    """
    fake_pdf = tmp_path / "garbage.pdf"
    fake_pdf.write_bytes(b"\x00\x01\x02\x03 binary garbage not a pdf")
    rc = main(["--json", str(fake_pdf)])
    assert rc == 2
    out = capsys.readouterr().out
    payload = json.loads(out)  # must not raise
    assert payload["summary"]["exit_reason"] == "unreadable_input"


def test_binary_non_pdf_file_no_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A non-PDF binary .pdf input must produce a friendly error on stderr, no traceback."""
    fake_pdf = tmp_path / "garbage.pdf"
    fake_pdf.write_bytes(b"\x00\x01\x02\x03 binary garbage not a pdf")
    main([str(fake_pdf)])
    err = capsys.readouterr().err
    assert "Error:" in err
    assert "Traceback" not in err


# ---------------------------------------------------------------------------
# A6: Parametrized --json property test: every validation-flow error path
#     must emit exactly one parseable JSON document on stdout
# ---------------------------------------------------------------------------


def _make_corrupt_zip(tmp_path: Path) -> Path:
    p = tmp_path / "a1_corrupt.zip"
    p.write_bytes(b"not a zip")
    return p


def _make_no_master_dir(tmp_path: Path) -> Path:
    d = tmp_path / "a6_empty_dir"
    d.mkdir()
    (d / "README.txt").write_text("no tex here", encoding="utf-8")
    return d


def _make_garbage_pdf(tmp_path: Path) -> Path:
    p = tmp_path / "a6_garbage.pdf"
    p.write_bytes(b"\x00\x01 not a pdf")
    return p


def _make_thesis_dir(tmp_path: Path) -> Path:
    d = tmp_path / "a6_thesis_dir"
    d.mkdir()
    (d / "main.tex").write_text(
        r"\documentclass{ufdissertation}" + "\n" + r"\thesisType{Thesis}" + "\n",
        encoding="utf-8",
    )
    return d


def _make_missing_toolchain_dir(tmp_path: Path) -> Path:
    d = tmp_path / "a6_missing_toolchain"
    d.mkdir()
    (d / "main.tex").write_text(r"\documentclass{ufdissertation}", encoding="utf-8")
    return d


def _make_compile_failure_dir(tmp_path: Path) -> Path:
    d = tmp_path / "a6_compile_fail"
    d.mkdir()
    (d / "main.tex").write_text(r"\documentclass{ufdissertation}", encoding="utf-8")
    return d


@pytest.mark.parametrize(
    "label,make_input,extra_args,mock_lualatex,mock_compile",
    [
        # Resolve-layer error: corrupt zip → UnreadableInput
        ("corrupt_zip", _make_corrupt_zip, [], False, False),
        # Detect-layer error: directory with no .tex master
        ("no_tex_master", _make_no_master_dir, ["--dry-run"], False, False),
        # Thesis input path
        ("thesis_input", _make_thesis_dir, ["--dry-run"], False, False),
        # --main outside root
        ("main_outside_root", None, ["--dry-run", "--main", "/etc/passwd"], False, False),
        # Missing toolchain
        ("missing_toolchain", _make_missing_toolchain_dir, [], True, False),
        # Compile failure
        ("compile_failure", _make_compile_failure_dir, [], False, True),
    ],
)
def test_json_stdout_is_single_parseable_document_on_all_error_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    label: str,
    make_input,
    extra_args: list[str],
    mock_lualatex: bool,
    mock_compile: bool,
) -> None:
    """--json MUST emit exactly one parseable JSON document on stdout for every
    validation-flow error path. json.loads raises on trailing data or empty
    output, so a single successful parse is the correctness gate.

    Note: --init and bare (no input) paths deliberately emit empty stdout
    (scoped outside the validation flow) and are excluded from this suite.
    """
    from latex2ufdissertation.pipeline.types import ConverterError

    # Build the input path (or reuse tmp_path for --main-outside-root case).
    if make_input is None:
        # --main outside root: we need a valid dir so resolve() succeeds
        d = tmp_path / "a6_main_escape"
        d.mkdir()
        (d / "main.tex").write_text(r"\documentclass{ufdissertation}", encoding="utf-8")
        input_path = str(d)
    else:
        input_path = str(make_input(tmp_path))

    if mock_lualatex:
        monkeypatch.setattr("latex2ufdissertation.cli.lualatex_available", lambda: False)
    if mock_compile:
        monkeypatch.setattr("latex2ufdissertation.cli.lualatex_available", lambda: True)
        monkeypatch.setattr(
            "latex2ufdissertation.cli.compile_pdf",
            lambda *a, **k: (_ for _ in ()).throw(ConverterError("boom")),
        )

    argv = ["--json", input_path] + extra_args
    rc = main(argv)

    out = capsys.readouterr().out
    try:
        payload = json.loads(out)
    except json.JSONDecodeError as exc:
        pytest.fail(f"[{label}] --json stdout is not valid JSON: {exc!r}\nstdout was: {out!r}")

    assert isinstance(payload, dict), f"[{label}] JSON payload must be a dict, got {type(payload)}"
    assert "summary" in payload, f"[{label}] JSON payload must contain 'summary' key"
    assert rc in (2, 3), f"[{label}] expected error exit code (2 or 3), got {rc}"


# ---------------------------------------------------------------------------
# Mutant killers — GROUP 3 (cli.py exit codes + --json contracts)
# ---------------------------------------------------------------------------


def test_init_success_exits_exactly_0(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """G3a: --init SUCCESS must return exit code exactly 0.

    Kills mutant: `return 0` -> `return 1` in the --init success branch.
    We mock init_project to avoid the 30s network fetch.
    """
    with patch("latex2ufdissertation.cli.init_project", return_value=None):
        rc = main(["--init", str(tmp_path / "newproject")])
    assert rc == 0, f"--init success must exit 0, got {rc}"


def test_init_converter_error_exits_exactly_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """G3b: --init on ConverterError must return exit code exactly 2.

    init_project raises ConverterError when the target is non-empty.
    Kills mutant: `return 2` -> `return 3` in the ConverterError branch.
    """
    non_empty = tmp_path / "existing"
    non_empty.mkdir()
    (non_empty / "something.tex").write_text("content", encoding="utf-8")

    # init_project raises ConverterError on a non-empty target; no mock needed.
    rc = main(["--init", str(non_empty)])
    assert rc == 2, f"--init ConverterError must exit 2, got {rc}"
    err = capsys.readouterr().err
    assert "Error:" in err


def test_corrupt_zip_exits_exactly_2_with_valid_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """G3c: resolve() UnreadableInput must return exit code EXACTLY 2 + valid JSON.

    Strengthens test_corrupt_zip_cli_exits_2_with_valid_json by explicitly
    asserting exit_code == 2 (not 3), killing mutant ID328: `return 2` -> `return 3`.
    """
    corrupt = tmp_path / "g3c_corrupt.zip"
    corrupt.write_bytes(b"this is not a zip file at all")
    rc = main(["--json", str(corrupt)])
    assert rc == 2, f"corrupt zip must exit EXACTLY 2, not {rc} (mutant ID328: return 2->3)"
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["summary"]["exit_reason"] == "unreadable_input"


def test_pdf_mode_missing_toolchain_exits_exactly_3_with_valid_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """G3d: PDF-mode MissingToolchain must exit exactly 3 + valid --json payload.

    Kills mutant ID318: `return 3` -> `return 4` in the pdf-mode MissingToolchain
    branch (cli.py ~line 219).
    Also kills _emit_json(None) mutant ID317: if _emit_json received None, it
    would crash before printing, so json.loads would fail.
    """
    from latex2ufdissertation.pipeline.types import MissingToolchain

    fake_pdf = tmp_path / "paper.pdf"
    fake_pdf.write_bytes(b"%PDF-1.7\n")

    with patch(
        "latex2ufdissertation.pipeline.pdf_checks.run_pdf_checks",
        side_effect=MissingToolchain("pdfminer.six not installed"),
    ):
        rc = main(["--json", str(fake_pdf)])

    assert rc == 3, f"PDF-mode MissingToolchain must exit EXACTLY 3, not {rc} (mutant ID318)"
    out = capsys.readouterr().out
    payload = json.loads(out)  # fails if _emit_json(None) was called
    assert isinstance(payload, dict), "JSON payload must be a dict"
    assert "summary" in payload
    assert payload["summary"]["exit_reason"] == "missing_toolchain"


def test_build_phase_missing_toolchain_exits_exactly_3_with_valid_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """G3e (MissingToolchain): run_pdf_checks raises MissingToolchain during
    the build phase (after bundled PDF is found) → must exit exactly 3 + valid JSON.

    Kills mutant ID348: `return 3` -> `return 4` (or similar) in lines ~295-299.
    Kills mutant ID347: _emit_json(None) would crash before print.
    """
    from latex2ufdissertation.pipeline.types import MissingToolchain

    # Place a bundled PDF so _find_bundled_pdf returns it; skips lualatex/compile.
    project = tmp_path / "g3e_proj"
    project.mkdir()
    (project / "main.tex").write_text(r"\documentclass{ufdissertation}", encoding="utf-8")
    (project / "main.pdf").write_bytes(b"%PDF-1.7\n")

    with patch(
        "latex2ufdissertation.pipeline.pdf_checks.run_pdf_checks",
        side_effect=MissingToolchain("pdfminer.six not installed"),
    ):
        rc = main(["--json", str(project)])

    assert rc == 3, f"build-phase MissingToolchain must exit EXACTLY 3, not {rc} (mutant ID348)"
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert isinstance(payload, dict)
    assert "summary" in payload
    assert payload["summary"]["exit_reason"] == "missing_toolchain"


def test_build_phase_unreadable_input_exits_exactly_2_with_valid_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """G3e (UnreadableInput): run_pdf_checks raises UnreadableInput during
    the build phase → must exit exactly 2 + valid JSON.

    Kills mutant ID351: `return 2` -> `return 3` in lines ~301-305.
    Kills mutant ID350: _emit_json(None) crash.
    """
    from latex2ufdissertation.pipeline.types import UnreadableInput

    project = tmp_path / "g3e_proj2"
    project.mkdir()
    (project / "main.tex").write_text(r"\documentclass{ufdissertation}", encoding="utf-8")
    (project / "main.pdf").write_bytes(b"%PDF-1.7\n")

    with patch(
        "latex2ufdissertation.pipeline.pdf_checks.run_pdf_checks",
        side_effect=UnreadableInput("cannot parse PDF"),
    ):
        rc = main(["--json", str(project)])

    assert rc == 2, f"build-phase UnreadableInput must exit EXACTLY 2, not {rc} (mutant ID351)"
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert isinstance(payload, dict)
    assert "summary" in payload
    assert payload["summary"]["exit_reason"] == "unreadable_input"


# ---------------------------------------------------------------------------
# FIX #5: --help input string mentions .tex and .pdf
# ---------------------------------------------------------------------------


def test_help_input_arg_mentions_tex_and_pdf() -> None:
    """FIX #5: parser help for the positional 'input' arg must list .tex and .pdf."""
    parser = _build_parser()
    # Find the 'input' action and check its help string.
    for action in parser._actions:
        if action.dest == "input":
            assert ".tex" in (action.help or ""), (
                f"help for 'input' must mention '.tex'; got: {action.help!r}"
            )
            assert ".pdf" in (action.help or ""), (
                f"help for 'input' must mention '.pdf'; got: {action.help!r}"
            )
            return
    pytest.fail("'input' positional argument not found in parser")


# ---------------------------------------------------------------------------
# FIX #3: bundled-PDF message shows resolved path + stale-source caveat
# ---------------------------------------------------------------------------


def test_bundled_pdf_message_shows_resolved_path_and_caveat(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FIX #3: when a bundled PDF is found, stderr must include its resolved path
    and the stale-source caveat substring 'may not reflect'/'force recompile'.
    """
    project = tmp_path / "proj"
    project.mkdir()
    (project / "main.tex").write_text(r"\documentclass{ufdissertation}", encoding="utf-8")
    pdf = project / "main.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")

    with patch(
        "latex2ufdissertation.pipeline.pdf_checks.run_pdf_checks",
        return_value=None,
    ):
        rc = main(["--dry-run", str(project)])

    # --dry-run skips the bundled-PDF path; re-run without --dry-run.
    with patch(
        "latex2ufdissertation.pipeline.pdf_checks.run_pdf_checks",
        return_value=None,
    ):
        rc = main([str(project)])

    err = capsys.readouterr().err
    resolved = str(pdf.resolve())
    assert resolved in err, f"stderr should contain the resolved PDF path {resolved!r}; got:\n{err}"
    assert "may not reflect" in err or "force recompile" in err, (
        f"stderr should contain the stale-source caveat; got:\n{err}"
    )
    assert rc in (0, 1, 2)


# ---------------------------------------------------------------------------
# FIX #11: --dry-run + .pdf input → warning emitted, PDF checks still run
# ---------------------------------------------------------------------------


def test_dry_run_with_pdf_input_warns_and_continues(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FIX #11: --dry-run with a .pdf input must emit the no-effect warning
    on stderr AND still run PDF checks (exit 2 when PDF is garbage).
    """
    garbage_pdf = tmp_path / "paper.pdf"
    garbage_pdf.write_bytes(b"%PDF-1.7\n")  # minimal PDF header, no /Root → fails parse

    rc = main(["--dry-run", str(garbage_pdf)])
    err = capsys.readouterr().err

    assert "Warning" in err and "--dry-run" in err and ".pdf input" in err, (
        f"warning line not found in stderr; got:\n{err}"
    )
    # PDF checks still ran (garbage PDF → exit 2, unreadable_input).
    assert rc == 2


def test_dry_run_with_pdf_json_warning_present(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FIX #11: --json --dry-run with .pdf input emits warning on stderr
    and still a valid JSON payload on stdout.
    """
    garbage_pdf = tmp_path / "paper2.pdf"
    garbage_pdf.write_bytes(b"%PDF-1.7\n")

    rc = main(["--dry-run", "--json", str(garbage_pdf)])
    captured = capsys.readouterr()
    err = captured.err

    assert "Warning" in err, f"warning not in stderr; got:\n{err}"
    # JSON payload must still be valid.
    payload = json.loads(captured.out)
    assert "summary" in payload
    assert rc == 2


# ---------------------------------------------------------------------------
# FIX #1: accept a .tex file as input
# ---------------------------------------------------------------------------

_MASTER_TEX = r"\documentclass{ufdissertation}" + "\n\\begin{document}\n\\end{document}\n"
_CHAPTER_TEX = r"\section{Introduction}" + "\nSome text.\n"


def test_tex_master_input_validates_and_detects_mode_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FIX #1a: passing a valid UF dissertation master .tex directly must
    validate (rc in 0/1), set detected_mode='dir' in JSON, and show the .tex
    filename in the 'validating' stderr line.
    """
    tex = tmp_path / "main.tex"
    tex.write_text(_MASTER_TEX, encoding="utf-8")

    rc = main(["--json", "--dry-run", str(tex)])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc in (0, 1), f"expected exit 0 or 1 for valid master .tex, got {rc}"
    assert payload["detected_mode"] == "dir", (
        f"expected detected_mode='dir' for .tex input, got {payload['detected_mode']!r}"
    )
    assert "validating" in captured.err and "main.tex" in captured.err, (
        f"expected 'validating main.tex' in stderr; got:\n{captured.err}"
    )


def test_tex_master_with_documentclass_options_is_accepted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FIX #1: a master whose \\documentclass carries an [options] bracket
    (e.g. \\documentclass[oneside]{ufdissertation}) must be accepted, not
    rejected as 'not a UF dissertation master'. Pins the canonical-regex
    detection against a literal-substring regression.
    """
    tex = tmp_path / "main.tex"
    tex.write_text(
        _MASTER_TEX.replace(
            r"\documentclass{ufdissertation}",
            r"\documentclass[oneside,12pt]{ufdissertation}",
        ),
        encoding="utf-8",
    )

    rc = main(["--json", "--dry-run", str(tex)])
    payload = json.loads(capsys.readouterr().out)

    assert rc in (0, 1), f"options-bracket master must be accepted, got rc={rc}"
    assert payload["detected_mode"] == "dir"


def test_tex_chapter_input_exits_2_with_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FIX #1b: a .tex file without \\documentclass{ufdissertation} must exit 2
    with the 'not a UF dissertation master' targeted message.
    """
    tex = tmp_path / "chapter1.tex"
    tex.write_text(_CHAPTER_TEX, encoding="utf-8")

    rc = main([str(tex)])
    err = capsys.readouterr().err

    assert rc == 2
    assert "not a UF dissertation master" in err, (
        f"expected targeted error message in stderr; got:\n{err}"
    )
    assert r"\documentclass{ufdissertation}" in err or "documentclass" in err


def test_tex_chapter_input_json_exit_reason(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FIX #1b (--json): chapter .tex must emit valid JSON with exit_reason=unreadable_input."""
    tex = tmp_path / "chapter2.tex"
    tex.write_text(_CHAPTER_TEX, encoding="utf-8")

    rc = main(["--json", str(tex)])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 2
    assert payload["summary"]["exit_reason"] == "unreadable_input"


def test_tex_input_json_detects_dir_mode(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FIX #1c: master .tex input with --json must report detected_mode='dir'."""
    tex = tmp_path / "dissertation.tex"
    tex.write_text(_MASTER_TEX, encoding="utf-8")

    rc = main(["--json", "--dry-run", str(tex)])
    payload = json.loads(capsys.readouterr().out)

    assert payload["detected_mode"] == "dir"
    assert rc in (0, 1)


def test_nonexistent_tex_falls_through_to_resolve_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FIX #1: a non-existent .tex path must NOT be intercepted by the .tex branch
    (p.is_file() is False); it falls through to resolve() → UnreadableInput → exit 2.
    """
    fake = tmp_path / "ghost.tex"
    # Do NOT create the file.
    rc = main([str(fake)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "Error:" in err


def _minimal_master_with_findings(tmp_path: Path) -> Path:
    # A bare ufdissertation master with no \set*File macros → required-section
    # must-fix findings fire on --dry-run (source layer).
    (tmp_path / "main.tex").write_text(
        r"\documentclass{ufdissertation}" + "\n\\begin{document}\n\\end{document}\n",
        encoding="utf-8",
    )
    return tmp_path


def test_json_mode_suppresses_live_diagnostic_lines(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Q1 follow-up: under --json the live per-finding diagnostic stream (2-space
    "  [severity] RULE" lines from Issues.add) is suppressed so it does not
    duplicate the consolidated report on stderr; JSON stdout stays valid and the
    final report still prints."""
    proj = _minimal_master_with_findings(tmp_path)
    rc = main(["--json", "--dry-run", str(proj)])
    cap = capsys.readouterr()
    json.loads(cap.out)  # stdout still a valid single JSON document
    assert rc == 1  # missing required sections → must-fix findings
    # No live 2-space-indented diagnostic lines ("\n  [..."); the report's own
    # finding lines are 4-space-indented and still present.
    assert "\n  [" not in cap.err
    assert "[must-fix]" in cap.err


def test_non_json_mode_still_emits_live_diagnostic_lines(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without --json the live per-finding stream is retained (2-space lines)."""
    proj = _minimal_master_with_findings(tmp_path)
    main(["--dry-run", str(proj)])
    assert "\n  [" in capsys.readouterr().err

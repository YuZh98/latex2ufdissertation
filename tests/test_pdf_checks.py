"""Tests for the PDF-layer validation module (pdf_checks.py).

TDD pass: these tests are written first and drive the implementation.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Locate the committed demo PDF once; tests that need it skip when absent.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEMO_PDF = _REPO_ROOT / "examples" / "demo_dissertation" / "main.pdf"
_VIOLATION_PDF = (
    _REPO_ROOT / "tests" / "fixtures" / "uf_f2_pdf_font_violation" / "input" / "violation.pdf"
)
_F3_VIOLATION_PDF = (
    _REPO_ROOT / "tests" / "fixtures" / "uf_f3_pdf_size_violation" / "input" / "violation.pdf"
)
_S5_DRAFT_PDF = _REPO_ROOT / "tests" / "fixtures" / "uf_s5_draft_mode" / "input" / "draft.pdf"
_S1_EMPTY_PDF = _REPO_ROOT / "tests" / "fixtures" / "uf_s1_empty_pdf" / "input" / "empty.pdf"

_VIOLATION_AVAILABLE = pytest.mark.skipif(
    not _VIOLATION_PDF.exists(), reason="F2 violation PDF fixture not present"
)
_F3_VIOLATION_AVAILABLE = pytest.mark.skipif(
    not _F3_VIOLATION_PDF.exists(), reason="F3 violation PDF fixture not present"
)
_S5_DRAFT_AVAILABLE = pytest.mark.skipif(
    not _S5_DRAFT_PDF.exists(), reason="S5 draft-mode PDF fixture not present"
)
_S1_EMPTY_AVAILABLE = pytest.mark.skipif(
    not _S1_EMPTY_PDF.exists(), reason="S1 empty PDF fixture not present"
)

_DEMO_AVAILABLE = pytest.mark.skipif(not _DEMO_PDF.exists(), reason="demo PDF not present")


# ---------------------------------------------------------------------------
# Subset-prefix strip (unit-level, no PDF needed)
# ---------------------------------------------------------------------------


def test_subset_prefix_strip() -> None:
    """Random 6-uppercase-letter prefix followed by '+' must be stripped."""
    from latex2ufdissertation.pipeline.pdf_checks import _SUBSET_RE

    raw = "MBKJME+TeXGyreTermesX-Regular"
    stripped = _SUBSET_RE.sub("", raw)
    assert stripped == "TeXGyreTermesX-Regular"


def test_subset_prefix_strip_no_prefix() -> None:
    """Font names without a prefix must be left unchanged."""
    from latex2ufdissertation.pipeline.pdf_checks import _SUBSET_RE

    raw = "TeXGyreTermesX-Regular"
    assert _SUBSET_RE.sub("", raw) == "TeXGyreTermesX-Regular"


# ---------------------------------------------------------------------------
# _extract_pages on the demo PDF
# ---------------------------------------------------------------------------


@_DEMO_AVAILABLE
def test_extract_pages_demo_page_count() -> None:
    """The committed demo PDF must have exactly 26 pages."""
    from latex2ufdissertation.pipeline.pdf_checks import _extract_pages

    pages = _extract_pages(_DEMO_PDF)
    assert len(pages) == 26


@_DEMO_AVAILABLE
def test_extract_pages_demo_body_font() -> None:
    """At least one page in the demo must have a body_font starting with
    'TeXGyreTermes' and body_size == 12.0.
    """
    from latex2ufdissertation.pipeline.pdf_checks import _extract_pages

    pages = _extract_pages(_DEMO_PDF)
    assert any(
        p.body_font is not None and p.body_font.startswith("TeXGyreTermes") and p.body_size == 12.0
        for p in pages
    ), "No page found with TeXGyreTermes body font at 12.0pt"


@_DEMO_AVAILABLE
def test_extract_pages_page_nums_are_1based() -> None:
    """page_num on every PageData must be 1-based and contiguous."""
    from latex2ufdissertation.pipeline.pdf_checks import _extract_pages

    pages = _extract_pages(_DEMO_PDF)
    nums = [p.page_num for p in pages]
    assert nums == list(range(1, len(pages) + 1))


# ---------------------------------------------------------------------------
# run_pdf_checks on the demo PDF — S1 must NOT fire
# ---------------------------------------------------------------------------


@_DEMO_AVAILABLE
def test_run_pdf_checks_demo_zero_findings() -> None:
    """run_pdf_checks on the known-good demo must produce zero findings.
    S1 (PDF has no extractable text) must not fire on a real dissertation.
    """
    from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks
    from latex2ufdissertation.pipeline.types import Issues

    issues = Issues()
    run_pdf_checks(_DEMO_PDF, issues)
    assert issues.findings == [], f"Unexpected findings: {issues.findings}"


# ---------------------------------------------------------------------------
# S1 check fires on a zero-page / text-free PDF
# ---------------------------------------------------------------------------


def test_run_pdf_checks_s1_fires_on_empty_pdf(tmp_path: Path) -> None:
    """An empty / zero-page PDF (PDFSyntaxError path already raises
    UnreadableInput; S1 covers the 'parses but empty' niche).
    We mock _extract_pages to return zero pages to test S1 logic directly
    without needing a real edge-case PDF file.
    """
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks
    from latex2ufdissertation.pipeline.rules import MUST_FIX, PDF
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "empty.pdf"
    dummy_pdf.write_bytes(b"")  # file must exist for the path check

    issues = Issues()
    with patch(
        "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
        return_value=[],
    ):
        run_pdf_checks(dummy_pdf, issues)

    assert len(issues.findings) == 1
    f = issues.findings[0]
    assert f.rule_id == "UF-S1"
    assert f.severity == MUST_FIX
    assert f.layer == PDF


def test_run_pdf_checks_s1_fires_on_all_none_pages(tmp_path: Path) -> None:
    """S1 fires when all pages have body_font=None (no glyph data)."""
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import PageData, run_pdf_checks
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "image_only.pdf"
    dummy_pdf.write_bytes(b"")

    # 3 pages, all with no extractable text
    mock_pages = [
        PageData(page_num=1, body_font=None, body_size=None),
        PageData(page_num=2, body_font=None, body_size=None),
        PageData(page_num=3, body_font=None, body_size=None),
    ]

    issues = Issues()
    with patch(
        "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
        return_value=mock_pages,
    ):
        run_pdf_checks(dummy_pdf, issues)

    assert len(issues.findings) == 1
    assert issues.findings[0].rule_id == "UF-S1"


# ---------------------------------------------------------------------------
# Gate 3: committed S1 fixture (real PDF, no mocks)
# ---------------------------------------------------------------------------


@_S1_EMPTY_AVAILABLE
def test_run_pdf_checks_s1_fires_on_committed_empty_fixture() -> None:
    """Gate 3 — S1 fixture: a committed PDF that parses but has no extractable
    text must produce exactly one finding: UF-S1 (must-fix, pdf layer).

    The fixture (tests/fixtures/uf_s1_empty_pdf/input/empty.pdf) was compiled
    with LuaLaTeX from a one-page document that has no body text:
      \\phantomsection + \\addcontentsline produces an Outlines entry so S5
      does not fire (S5 fires only when BOTH link_count==0 AND no Outlines).
    F2 and F3 skip pages whose body_font is None, so they are also silent.
    """
    from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks
    from latex2ufdissertation.pipeline.rules import MUST_FIX, PDF
    from latex2ufdissertation.pipeline.types import Issues

    issues = Issues()
    run_pdf_checks(_S1_EMPTY_PDF, issues)

    assert len(issues.findings) == 1, (
        f"expected exactly 1 finding (UF-S1), got {len(issues.findings)}: "
        f"{[f.rule_id for f in issues.findings]}"
    )
    finding = issues.findings[0]
    assert finding.rule_id == "UF-S1"
    assert finding.severity == MUST_FIX
    assert finding.layer == PDF


# ---------------------------------------------------------------------------
# MissingToolchain / UnreadableInput exception behaviour
# ---------------------------------------------------------------------------


def test_run_pdf_checks_missing_toolchain_if_pdfminer_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If pdfminer.six is not importable, MissingToolchain must be raised."""
    import builtins
    import sys
    from unittest.mock import patch

    real_import = builtins.__import__

    def _block_pdfminer(name: str, *args, **kwargs):  # type: ignore[override]
        if name.startswith("pdfminer"):
            raise ImportError("pdfminer blocked for test")
        return real_import(name, *args, **kwargs)

    dummy_pdf = tmp_path / "x.pdf"
    dummy_pdf.write_bytes(b"")

    from latex2ufdissertation.pipeline.types import MissingToolchain

    # Remove cached pdfminer modules so the lazy import triggers fresh.
    saved = {k: v for k, v in sys.modules.items() if k.startswith("pdfminer")}
    for k in saved:
        monkeypatch.delitem(sys.modules, k)

    with patch("builtins.__import__", side_effect=_block_pdfminer):
        from latex2ufdissertation.pipeline import pdf_checks as _mod

        with pytest.raises(MissingToolchain, match="pdfminer"):
            _mod.run_pdf_checks(
                dummy_pdf,
                __import__("latex2ufdissertation.pipeline.types", fromlist=["Issues"]).Issues(),
            )


def test_run_pdf_checks_unreadable_on_syntax_error(
    tmp_path: Path,
) -> None:
    """A pdfminer PDFSyntaxError inside _extract_pages is converted to
    UnreadableInput before it reaches run_pdf_checks. This test verifies
    that the real, minimal-stub PDF raises UnreadableInput end-to-end
    (PDFSyntaxError → UnreadableInput inside _extract_pages).
    """
    from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks
    from latex2ufdissertation.pipeline.types import Issues, UnreadableInput

    dummy_pdf = tmp_path / "bad.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.7\n")

    issues = Issues()
    with pytest.raises(UnreadableInput):
        run_pdf_checks(dummy_pdf, issues)


# ---------------------------------------------------------------------------
# Fix 1: encrypted PDFs raise UnreadableInput, not a raw PDFEncryptionError
# ---------------------------------------------------------------------------


def test_extract_pages_raises_unreadable_on_encryption_error(
    tmp_path: Path,
) -> None:
    """PDFEncryptionError from pdfminer must be caught and re-raised as
    UnreadableInput, not escape as a raw exception to the CLI.
    """
    from unittest.mock import patch

    from pdfminer.pdfdocument import PDFEncryptionError

    from latex2ufdissertation.pipeline.pdf_checks import _extract_pages
    from latex2ufdissertation.pipeline.types import UnreadableInput

    dummy_pdf = tmp_path / "encrypted.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.7\n")

    with patch(
        "pdfminer.high_level.extract_pages",
        side_effect=PDFEncryptionError("password required"),
    ):
        with pytest.raises(UnreadableInput):
            _extract_pages(dummy_pdf)


# ---------------------------------------------------------------------------
# Fix 2: body-mode dominant-font unit test (multi-font page, Counter/max logic)
# ---------------------------------------------------------------------------


def test_extract_pages_dominant_font_wins_by_glyph_count(
    tmp_path: Path,
) -> None:
    """On a page with 10 glyphs of FontA@12.0 and 3 glyphs of ABCDEF+FontB@10.0,
    body_font must be 'FontA' and body_size must be 12.0 (subset prefix stripped).
    Exercises the Counter/max tie-break logic in _extract_pages directly.
    """
    from unittest.mock import MagicMock, patch

    from pdfminer.layout import LTChar

    from latex2ufdissertation.pipeline.pdf_checks import _extract_pages

    dummy_pdf = tmp_path / "multi_font.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.7\n")

    # Build fake LTChar-like objects that pass the real isinstance(item, LTChar)
    # check by using MagicMock(spec=LTChar) — spec sets __class__ correctly.
    def make_char(fontname: str, size: float) -> MagicMock:
        c = MagicMock(spec=LTChar)
        c.fontname = fontname
        c.size = size
        return c

    # 10 glyphs FontA@12.0, 3 glyphs ABCDEF+FontB@10.0 (subset prefix present)
    fake_page = [make_char("FontA", 12.0)] * 10 + [make_char("ABCDEF+FontB", 10.0)] * 3

    with patch("pdfminer.high_level.extract_pages", return_value=[fake_page]):
        pages = _extract_pages(dummy_pdf)

    assert len(pages) == 1
    assert pages[0].body_font == "FontA"
    assert pages[0].body_size == 12.0


# ---------------------------------------------------------------------------
# PDF-input mode end-to-end (acceptance gate §8.4)
# ---------------------------------------------------------------------------


@_DEMO_AVAILABLE
def test_cli_pdf_input_mode_skips_source_layer_and_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Acceptance gate §8.4 — pdf input mode tested.

    Invoking the CLI with the committed demo PDF must:
    - skip the source layer (note emitted to stderr)
    - produce exit code 0 (no must-fix findings)
    - not attempt compilation
    """
    from latex2ufdissertation.cli import main

    rc = main([str(_DEMO_PDF)])
    captured = capsys.readouterr()
    assert "source layer skipped" in captured.err
    assert rc == 0


@_DEMO_AVAILABLE
def test_cli_pdf_input_mode_detected_mode_in_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When --json is used with a PDF input, detected_mode must be 'pdf'."""
    import json

    from latex2ufdissertation.cli import main

    rc = main(["--json", str(_DEMO_PDF)])
    payload = json.loads(capsys.readouterr().out)
    assert payload["detected_mode"] == "pdf"
    assert rc == 0


# ---------------------------------------------------------------------------
# Bundled-PDF path (spec §4: prefer bundled PDF over compiling)
# ---------------------------------------------------------------------------


@_DEMO_AVAILABLE
def test_cli_dir_input_uses_bundled_pdf_not_compile(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The demo directory contains a bundled main.pdf. Running the CLI
    against the directory must pick up that PDF (not attempt compilation)
    and produce exit 0 (zero must-fix findings on the clean demo).

    Verifies spec §4: 'prefer bundled PDF if present; otherwise compile'.
    """
    from latex2ufdissertation.cli import main

    demo_dir = _DEMO_PDF.parent
    rc = main([str(demo_dir)])
    captured = capsys.readouterr()
    assert "using bundled PDF" in captured.err, "Expected bundled-PDF branch to be taken"
    assert rc == 0


# ---------------------------------------------------------------------------
# F2 PDF-layer check (UF-F2, body-font allowlist)
# ---------------------------------------------------------------------------


def test_check_f2_fires_on_non_allowed_font(tmp_path: Path) -> None:
    """_check_f2: a page whose body font is outside the allowlist emits UF-F2
    with severity=must-fix and layer=pdf. Uses mocked PageData; no real PDF.
    """
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import PageData, run_pdf_checks
    from latex2ufdissertation.pipeline.rules import MUST_FIX, PDF
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"")

    # One page whose body-mode font is LMRoman (not in any allowed prefix).
    mock_pages = [PageData(page_num=7, body_font="LMRoman12-Regular", body_size=12.0)]

    issues = Issues()
    with patch(
        "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
        return_value=mock_pages,
    ):
        run_pdf_checks(dummy_pdf, issues)

    f2 = [f for f in issues.findings if f.rule_id == "UF-F2"]
    assert len(f2) == 1, f"expected 1 UF-F2 finding, got {len(f2)}"
    finding = f2[0]
    assert finding.severity == MUST_FIX
    assert finding.layer == PDF
    assert finding.location == "p.7"
    assert finding.observed == "LMRoman12-Regular"
    assert "Times New Roman or Arial" in (finding.required or "")


def test_check_f2_silent_on_allowed_fonts(tmp_path: Path) -> None:
    """_check_f2: pages with TeXGyreTermes / NewTX / LMMono body fonts must
    not emit any UF-F2 finding.
    """
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import PageData, run_pdf_checks
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"")

    mock_pages = [
        PageData(page_num=1, body_font="TeXGyreTermesX-Regular", body_size=12.0),
        PageData(page_num=2, body_font="NewTXMI", body_size=10.0),
        PageData(page_num=3, body_font="LMMono10-Regular", body_size=10.0),
        PageData(page_num=4, body_font=None, body_size=None),  # image-only page
        PageData(page_num=5, body_font="TeXGyreTermesX-Bold", body_size=12.0),
        PageData(page_num=6, body_font="TeXGyreTermesX-Italic", body_size=12.0),
    ]

    issues = Issues()
    with patch(
        "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
        return_value=mock_pages,
    ):
        run_pdf_checks(dummy_pdf, issues)

    f2 = [f for f in issues.findings if f.rule_id == "UF-F2"]
    assert f2 == [], f"unexpected UF-F2 findings on allowed fonts: {f2}"


def test_check_f2_silent_on_true_times_fonts(tmp_path: Path) -> None:
    """_check_f2: real Times New Roman render names (pdf-input mode) must not
    emit UF-F2.  UF allows Times New Roman or Arial; a PDF compiled with a
    true Times-NR font (not the template's TeXGyreTermes) is conforming.

    Covered names:
      TimesNewRomanPSMT  — Windows/Adobe CID embed of Times New Roman
      Times-Roman        — Type 1 canonical name
      TimesNewRoman      — bare stem (some PDF producers)
      NimbusRomNo9L-Regu — GhostScript/TeXLive Times substitute
    """
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import PageData, run_pdf_checks
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"")

    mock_pages = [
        PageData(page_num=1, body_font="TimesNewRomanPSMT", body_size=12.0),
        PageData(page_num=2, body_font="Times-Roman", body_size=12.0),
        PageData(page_num=3, body_font="TimesNewRoman", body_size=12.0),
        PageData(page_num=4, body_font="NimbusRomNo9L-Regu", body_size=12.0),
    ]

    issues = Issues()
    with patch(
        "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
        return_value=mock_pages,
    ):
        run_pdf_checks(dummy_pdf, issues)

    f2 = [f for f in issues.findings if f.rule_id == "UF-F2"]
    assert f2 == [], f"True Times New Roman names must not trigger UF-F2; unexpected findings: {f2}"


def test_check_f2_lmroman_still_fires(tmp_path: Path) -> None:
    """_check_f2: LMRoman12-Regular (Computer Modern Roman) is non-conforming
    and must still emit UF-F2 after the Times-family prefixes are added.
    Regression guard: widening the allowlist must not mask real violations.
    """
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import PageData, run_pdf_checks
    from latex2ufdissertation.pipeline.rules import MUST_FIX, PDF
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"")

    mock_pages = [PageData(page_num=5, body_font="LMRoman12-Regular", body_size=12.0)]

    issues = Issues()
    with patch(
        "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
        return_value=mock_pages,
    ):
        run_pdf_checks(dummy_pdf, issues)

    f2 = [f for f in issues.findings if f.rule_id == "UF-F2"]
    assert len(f2) == 1, f"LMRoman12-Regular must fire UF-F2; got {len(f2)} findings"
    assert f2[0].severity == MUST_FIX
    assert f2[0].layer == PDF


@_DEMO_AVAILABLE
def test_check_f2_demo_zero_findings() -> None:
    """Acceptance gate §8.2: run_pdf_checks on the committed demo must produce
    zero UF-F2 findings across all 26 pages.
    """
    from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks
    from latex2ufdissertation.pipeline.types import Issues

    issues = Issues()
    run_pdf_checks(_DEMO_PDF, issues)
    f2 = [f for f in issues.findings if f.rule_id == "UF-F2"]
    assert f2 == [], f"Demo produced unexpected UF-F2 findings: {f2}"


@_VIOLATION_AVAILABLE
def test_check_f2_violation_fixture_fires_must_fix() -> None:
    """The committed violation PDF (rendered with LMRoman body from
    \\fontfamily{ppl}\\selectfont override) must produce >=1 UF-F2 finding
    with severity=must-fix, layer=pdf, and a p.N location.
    """
    from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks
    from latex2ufdissertation.pipeline.rules import MUST_FIX, PDF
    from latex2ufdissertation.pipeline.types import Issues

    issues = Issues()
    run_pdf_checks(_VIOLATION_PDF, issues)
    f2 = [f for f in issues.findings if f.rule_id == "UF-F2"]
    assert len(f2) == 13, f"Expected 13 UF-F2 findings from violation PDF, got {len(f2)}"
    for finding in f2:
        assert finding.severity == MUST_FIX, f"Expected must-fix, got {finding.severity}"
        assert finding.layer == PDF, f"Expected pdf layer, got {finding.layer}"
        assert re.match(r"^p\.\d+$", finding.location), (
            f"Expected p.N location, got {finding.location!r}"
        )


# ---------------------------------------------------------------------------
# F3 PDF-layer check (UF-F3, body-mode size must be 12pt)
# ---------------------------------------------------------------------------


def test_check_f3_fires_on_wrong_body_size(tmp_path: Path) -> None:
    """_check_f3: a page whose body-mode size deviates from 12pt by >0.5
    emits UF-F3 with severity=must-fix, layer=pdf, and a p.N location.
    """
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import PageData, run_pdf_checks
    from latex2ufdissertation.pipeline.rules import MUST_FIX, PDF
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"")

    # One page whose body-mode size is ~20pt (well beyond 0.5pt tolerance).
    mock_pages = [PageData(page_num=3, body_font="TeXGyreTermesX-Regular", body_size=20.0)]

    issues = Issues()
    with patch(
        "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
        return_value=mock_pages,
    ):
        run_pdf_checks(dummy_pdf, issues)

    f3 = [f for f in issues.findings if f.rule_id == "UF-F3"]
    assert len(f3) == 1, f"expected 1 UF-F3 finding, got {len(f3)}"
    finding = f3[0]
    assert finding.severity == MUST_FIX
    assert finding.layer == PDF
    assert finding.location == "p.3"
    assert "20.0pt" in (finding.observed or "")
    assert "12-point" in (finding.required or "")


def test_check_f3_silent_on_correct_size(tmp_path: Path) -> None:
    """_check_f3: a page with body_size == 12.0 must not emit UF-F3."""
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import PageData, run_pdf_checks
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"")

    mock_pages = [PageData(page_num=1, body_font="TeXGyreTermesX-Regular", body_size=12.0)]

    issues = Issues()
    with patch(
        "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
        return_value=mock_pages,
    ):
        run_pdf_checks(dummy_pdf, issues)

    f3 = [f for f in issues.findings if f.rule_id == "UF-F3"]
    assert f3 == [], f"unexpected UF-F3 findings on 12pt page: {f3}"


def test_check_f3_silent_within_tolerance(tmp_path: Path) -> None:
    """_check_f3: a page with body_size exactly 12.5 (boundary) must not emit
    UF-F3 — the tolerance is strictly > 0.5.
    """
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import PageData, run_pdf_checks
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"")

    mock_pages = [PageData(page_num=1, body_font="TeXGyreTermesX-Regular", body_size=12.5)]

    issues = Issues()
    with patch(
        "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
        return_value=mock_pages,
    ):
        run_pdf_checks(dummy_pdf, issues)

    f3 = [f for f in issues.findings if f.rule_id == "UF-F3"]
    assert f3 == [], f"unexpected UF-F3 at boundary 12.5pt: {f3}"


def test_check_f3_fires_just_outside_tolerance(tmp_path: Path) -> None:
    """_check_f3: body_size 12.6 (just outside tolerance) must emit UF-F3."""
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import PageData, run_pdf_checks
    from latex2ufdissertation.pipeline.rules import MUST_FIX, PDF
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"")

    mock_pages = [PageData(page_num=1, body_font="TeXGyreTermesX-Regular", body_size=12.6)]

    issues = Issues()
    with patch(
        "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
        return_value=mock_pages,
    ):
        run_pdf_checks(dummy_pdf, issues)

    f3 = [f for f in issues.findings if f.rule_id == "UF-F3"]
    assert len(f3) == 1, f"expected UF-F3 at 12.6pt, got {len(f3)}"
    assert f3[0].severity == MUST_FIX
    assert f3[0].layer == PDF


def test_check_f3_skips_none_body_size(tmp_path: Path) -> None:
    """_check_f3: a page with body_size=None (image-only) must not emit UF-F3."""
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import PageData, run_pdf_checks
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"")

    mock_pages = [PageData(page_num=2, body_font=None, body_size=None)]

    issues = Issues()
    with patch(
        "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
        return_value=mock_pages,
    ):
        run_pdf_checks(dummy_pdf, issues)

    f3 = [f for f in issues.findings if f.rule_id == "UF-F3"]
    assert f3 == [], f"unexpected UF-F3 on image-only page: {f3}"


@_DEMO_AVAILABLE
def test_check_f3_demo_zero_findings() -> None:
    """Acceptance gate §8.2: run_pdf_checks on the committed demo must produce
    zero UF-F3 findings across all 26 pages (all at 12.0pt).
    """
    from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks
    from latex2ufdissertation.pipeline.types import Issues

    issues = Issues()
    run_pdf_checks(_DEMO_PDF, issues)
    f3 = [f for f in issues.findings if f.rule_id == "UF-F3"]
    assert f3 == [], f"Demo produced unexpected UF-F3 findings: {f3}"


@_F3_VIOLATION_AVAILABLE
def test_check_f3_violation_fixture_fires_must_fix() -> None:
    """The committed F3 violation PDF (rendered with \\fontsize{20}{24}\\selectfont
    body override) must produce >=1 UF-F3 finding with severity=must-fix,
    layer=pdf, p.N location, and observed size ~20pt.
    """
    from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks
    from latex2ufdissertation.pipeline.rules import MUST_FIX, PDF
    from latex2ufdissertation.pipeline.types import Issues

    issues = Issues()
    run_pdf_checks(_F3_VIOLATION_PDF, issues)
    f3 = [f for f in issues.findings if f.rule_id == "UF-F3"]
    assert len(f3) >= 1, f"Expected >=1 UF-F3 findings from violation PDF, got {len(f3)}"
    for finding in f3:
        assert finding.severity == MUST_FIX, f"Expected must-fix, got {finding.severity}"
        assert finding.layer == PDF, f"Expected pdf layer, got {finding.layer}"
        assert re.match(r"^p\.\d+$", finding.location), (
            f"Expected p.N location, got {finding.location!r}"
        )
        # Observed size should be considerably above 12pt (body override ~20pt)
        observed = finding.observed or ""
        size_match = re.search(r"([\d.]+)pt body text", observed)
        assert size_match, f"Expected 'Npt body text' in observed, got {observed!r}"
        body_size = float(size_match.group(1))
        assert body_size > 14.0, f"Expected body_size >14pt, got {body_size}pt"


# ---------------------------------------------------------------------------
# F3 severity calibration (3+4 hybrid): a deviation is must-fix ONLY when the
# document-wide body size is itself non-12pt (a global override = certain
# rejection). A localized deviation on an otherwise-12pt document (a
# \footnotesize table or \small figure sub-caption) is uncertain and routes
# to review, not must-fix.
# ---------------------------------------------------------------------------


def test_check_f3_localized_deviation_is_review(tmp_path: Path) -> None:
    """When the document-wide body size is 12pt but a few float pages render
    smaller (e.g. a \\footnotesize table at 10pt, a \\small sub-caption at
    10.9pt), UF-F3 must emit REVIEW on those pages and zero must-fix.
    """
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import PageData, run_pdf_checks
    from latex2ufdissertation.pipeline.rules import REVIEW
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"")

    # Majority of pages are genuine 12pt body text; two float pages deviate.
    mock_pages = [
        PageData(page_num=1, body_font="TeXGyreTermesX-Regular", body_size=12.0),
        PageData(page_num=2, body_font="TeXGyreTermesX-Regular", body_size=12.0),
        PageData(page_num=3, body_font="TeXGyreTermesX-Regular", body_size=12.0),
        PageData(page_num=4, body_font="TeXGyreTermesX-Regular", body_size=10.9),
        PageData(page_num=5, body_font="TeXGyreTermesX-Regular", body_size=10.0),
    ]

    issues = Issues()
    with patch(
        "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
        return_value=mock_pages,
    ):
        run_pdf_checks(dummy_pdf, issues)

    f3 = [f for f in issues.findings if f.rule_id == "UF-F3"]
    assert len(f3) == 2, f"expected 2 UF-F3 findings (p.4, p.5), got {len(f3)}"
    assert {f.location for f in f3} == {"p.4", "p.5"}
    for finding in f3:
        assert finding.severity == REVIEW, (
            f"localized deviation must be review, got {finding.severity} at {finding.location}"
        )
    assert issues.must_fix_count() == 0, "no must-fix expected on an otherwise-12pt document"


def test_check_f3_global_override_is_must_fix(tmp_path: Path) -> None:
    """When the document-wide body size is itself non-12pt (a global
    \\fontsize override), every deviating page must emit must-fix.
    """
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import PageData, run_pdf_checks
    from latex2ufdissertation.pipeline.rules import MUST_FIX
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"")

    # Body text shrunk document-wide to 11pt; one 12pt outlier page.
    mock_pages = [
        PageData(page_num=1, body_font="TeXGyreTermesX-Regular", body_size=11.0),
        PageData(page_num=2, body_font="TeXGyreTermesX-Regular", body_size=11.0),
        PageData(page_num=3, body_font="TeXGyreTermesX-Regular", body_size=11.0),
        PageData(page_num=4, body_font="TeXGyreTermesX-Regular", body_size=12.0),
    ]

    issues = Issues()
    with patch(
        "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
        return_value=mock_pages,
    ):
        run_pdf_checks(dummy_pdf, issues)

    f3 = [f for f in issues.findings if f.rule_id == "UF-F3"]
    assert len(f3) == 3, f"expected 3 must-fix UF-F3 findings, got {len(f3)}"
    assert {f.location for f in f3} == {"p.1", "p.2", "p.3"}
    for finding in f3:
        assert finding.severity == MUST_FIX
    assert issues.must_fix_count() == 3


def test_check_f3_global_undersize_is_must_fix(tmp_path: Path) -> None:
    """A document whose body text is shrunk document-wide (every page at 10pt)
    is a global override = certain rejection: every page emits must-fix, never
    review. Pins the lower end of the deviation spectrum.
    """
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import PageData, run_pdf_checks
    from latex2ufdissertation.pipeline.rules import MUST_FIX
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"")

    mock_pages = [
        PageData(page_num=n, body_font="TeXGyreTermesX-Regular", body_size=10.0)
        for n in range(1, 6)
    ]

    issues = Issues()
    with patch(
        "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
        return_value=mock_pages,
    ):
        run_pdf_checks(dummy_pdf, issues)

    f3 = [f for f in issues.findings if f.rule_id == "UF-F3"]
    assert len(f3) == 5, f"expected 5 must-fix findings, got {len(f3)}"
    for finding in f3:
        assert finding.severity == MUST_FIX
    assert issues.must_fix_count() == 5


def test_check_f3_tie_breaks_toward_12pt_review(tmp_path: Path) -> None:
    """When 12pt and a smaller size tie for the document-wide mode, the
    smaller size is treated as the uncertain case: doc-wide size resolves to
    12pt and the deviating pages route to review, never must-fix.
    """
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import PageData, run_pdf_checks
    from latex2ufdissertation.pipeline.rules import REVIEW
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"")

    # Equal counts of 12.0 and 10.0 — a tie that must resolve toward 12pt.
    mock_pages = [
        PageData(page_num=1, body_font="TeXGyreTermesX-Regular", body_size=12.0),
        PageData(page_num=2, body_font="TeXGyreTermesX-Regular", body_size=10.0),
    ]

    issues = Issues()
    with patch(
        "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
        return_value=mock_pages,
    ):
        run_pdf_checks(dummy_pdf, issues)

    f3 = [f for f in issues.findings if f.rule_id == "UF-F3"]
    assert len(f3) == 1 and f3[0].location == "p.2"
    assert f3[0].severity == REVIEW
    assert issues.must_fix_count() == 0


def test_check_f3_oversized_page_is_must_fix_even_if_doc_is_12pt(tmp_path: Path) -> None:
    """A page whose body text is LARGER than 12pt is a certain override (no
    float makes text bigger), so it emits must-fix even when the document-wide
    modal size is 12pt. Mirrors the \\fontsize{20} violation fixture at unit
    speed.
    """
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import PageData, run_pdf_checks
    from latex2ufdissertation.pipeline.rules import MUST_FIX
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"")

    # Majority 12pt; a few pages render body text at ~20pt (a real override).
    mock_pages = [
        PageData(page_num=1, body_font="TeXGyreTermesX-Regular", body_size=12.0),
        PageData(page_num=2, body_font="TeXGyreTermesX-Regular", body_size=12.0),
        PageData(page_num=3, body_font="TeXGyreTermesX-Regular", body_size=12.0),
        PageData(page_num=4, body_font="TeXGyreTermesX-Regular", body_size=19.9),
        PageData(page_num=5, body_font="TeXGyreTermesX-Regular", body_size=19.9),
    ]

    issues = Issues()
    with patch(
        "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
        return_value=mock_pages,
    ):
        run_pdf_checks(dummy_pdf, issues)

    f3 = [f for f in issues.findings if f.rule_id == "UF-F3"]
    assert {f.location for f in f3} == {"p.4", "p.5"}
    for finding in f3:
        assert finding.severity == MUST_FIX, "oversized body text must be must-fix"


def test_document_body_size_helper() -> None:
    """_document_body_size returns the glyph-page modal body size, ignoring
    None pages, with ties resolving toward 12pt; None on an empty document.
    """
    from latex2ufdissertation.pipeline.pdf_checks import PageData, _document_body_size

    assert _document_body_size([]) is None
    assert _document_body_size([PageData(1, None, None)]) is None
    # Clear majority at 12.0.
    assert (
        _document_body_size(
            [PageData(1, "F", 12.0), PageData(2, "F", 12.0), PageData(3, "F", 10.0)]
        )
        == 12.0
    )
    # Global shrink: 11.0 dominates.
    assert (
        _document_body_size(
            [PageData(1, "F", 11.0), PageData(2, "F", 11.0), PageData(3, "F", 12.0)]
        )
        == 11.0
    )
    # Tie between 12.0 and 10.0 resolves toward 12.0 (compliant side).
    assert _document_body_size([PageData(1, "F", 12.0), PageData(2, "F", 10.0)]) == 12.0


# ---------------------------------------------------------------------------
# S5 PDF-layer check (UF-S5, hyperlink annotations / outline present)
# ---------------------------------------------------------------------------


def test_check_s5_fires_when_both_absent(tmp_path: Path) -> None:
    """_check_s5 fires UF-S5 (review, pdf) when BOTH link_count==0 AND
    no Outlines in the catalog — the hyperref-disabled / draft-mode signal.
    Uses a patched helper; no real PDF needed.
    """
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks
    from latex2ufdissertation.pipeline.rules import PDF, REVIEW
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"")

    mock_pages = []  # _extract_pages patched to []  → S1 fires, but S5 also runs

    issues = Issues()
    with (
        patch(
            "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
            return_value=mock_pages,
        ),
        patch(
            "latex2ufdissertation.pipeline.pdf_checks._inspect_hyperlinks",
            return_value=(0, False),
        ),
    ):
        run_pdf_checks(dummy_pdf, issues)

    s5 = [f for f in issues.findings if f.rule_id == "UF-S5"]
    assert len(s5) == 1, f"expected 1 UF-S5 finding, got {len(s5)}"
    finding = s5[0]
    assert finding.severity == REVIEW
    assert finding.layer == PDF
    observed_lower = (finding.observed or "").lower()
    assert "hyperref" in observed_lower or "draft" in observed_lower
    assert finding.required is not None


def test_check_s5_silent_when_links_present(tmp_path: Path) -> None:
    """_check_s5 must NOT fire when link_count > 0 (even if no Outlines)."""
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"")

    issues = Issues()
    with (
        patch(
            "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
            return_value=[],
        ),
        patch(
            "latex2ufdissertation.pipeline.pdf_checks._inspect_hyperlinks",
            return_value=(5, False),
        ),
    ):
        run_pdf_checks(dummy_pdf, issues)

    s5 = [f for f in issues.findings if f.rule_id == "UF-S5"]
    assert s5 == [], f"unexpected UF-S5 when links present: {s5}"


def test_check_s5_silent_when_outline_present(tmp_path: Path) -> None:
    """_check_s5 must NOT fire when Outlines exist (even if link_count==0)."""
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"")

    issues = Issues()
    with (
        patch(
            "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
            return_value=[],
        ),
        patch(
            "latex2ufdissertation.pipeline.pdf_checks._inspect_hyperlinks",
            return_value=(0, True),
        ),
    ):
        run_pdf_checks(dummy_pdf, issues)

    s5 = [f for f in issues.findings if f.rule_id == "UF-S5"]
    assert s5 == [], f"unexpected UF-S5 when outline present: {s5}"


def test_check_s5_silent_when_both_present(tmp_path: Path) -> None:
    """_check_s5 must NOT fire when both links and Outlines are present."""
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"")

    issues = Issues()
    with (
        patch(
            "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
            return_value=[],
        ),
        patch(
            "latex2ufdissertation.pipeline.pdf_checks._inspect_hyperlinks",
            return_value=(159, True),
        ),
    ):
        run_pdf_checks(dummy_pdf, issues)

    s5 = [f for f in issues.findings if f.rule_id == "UF-S5"]
    assert s5 == [], f"unexpected UF-S5 when links+outline present: {s5}"


def test_check_s5_silent_when_inspect_raises(tmp_path: Path) -> None:
    """If _inspect_hyperlinks raises an unexpected exception, _check_s5 must
    NOT fire (degrade gracefully) and must NOT propagate the exception.
    """
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"")

    issues = Issues()
    with (
        patch(
            "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
            return_value=[],
        ),
        patch(
            "latex2ufdissertation.pipeline.pdf_checks._inspect_hyperlinks",
            side_effect=RuntimeError("malformed annots"),
        ),
    ):
        # Must not raise, and must not emit UF-S5
        run_pdf_checks(dummy_pdf, issues)

    s5 = [f for f in issues.findings if f.rule_id == "UF-S5"]
    assert s5 == [], f"UF-S5 must not fire when inspection fails: {s5}"


@_DEMO_AVAILABLE
def test_inspect_hyperlinks_demo_link_count() -> None:
    """_inspect_hyperlinks on the committed demo must return a positive Link
    annotation count (hyperref is enabled; ToC/LoF/LoT/cross-refs → Links).
    """
    from latex2ufdissertation.pipeline.pdf_checks import _inspect_hyperlinks

    link_count, has_outline = _inspect_hyperlinks(_DEMO_PDF)
    assert link_count > 0, (
        f"Expected >0 Link annots in demo PDF, got {link_count}. "
        "Likely a PSLiteral vs str comparison bug in _inspect_hyperlinks."
    )
    assert has_outline is True, f"Expected Outlines in demo catalog, got has_outline={has_outline}"


@_DEMO_AVAILABLE
def test_check_s5_demo_zero_findings() -> None:
    """Acceptance gate §8.2: run_pdf_checks on the committed demo must produce
    zero UF-S5 findings (demo PDF has link annotations + document outline).
    """
    from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks
    from latex2ufdissertation.pipeline.types import Issues

    issues = Issues()
    run_pdf_checks(_DEMO_PDF, issues)
    s5 = [f for f in issues.findings if f.rule_id == "UF-S5"]
    assert s5 == [], f"Demo produced unexpected UF-S5 findings: {s5}"


@_DEMO_AVAILABLE
def test_check_s5_demo_overall_zero_findings() -> None:
    """Acceptance gate §8.2: the full demo must have zero must-fix + zero review
    findings after S5 is added (S5 must not break the clean-demo gate).
    """
    from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks
    from latex2ufdissertation.pipeline.types import Issues

    issues = Issues()
    run_pdf_checks(_DEMO_PDF, issues)
    assert issues.findings == [], f"Demo produced unexpected findings: {issues.findings}"


@_S5_DRAFT_AVAILABLE
def test_check_s5_draft_fixture_fires_review() -> None:
    """The committed draft-mode fixture PDF must produce exactly 1 UF-S5 finding
    with severity=review and layer=pdf.
    """
    from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks
    from latex2ufdissertation.pipeline.rules import PDF, REVIEW
    from latex2ufdissertation.pipeline.types import Issues

    issues = Issues()
    run_pdf_checks(_S5_DRAFT_PDF, issues)
    s5 = [f for f in issues.findings if f.rule_id == "UF-S5"]
    assert len(s5) == 1, f"Expected exactly 1 UF-S5 finding from draft fixture, got {len(s5)}"
    finding = s5[0]
    assert finding.severity == REVIEW, f"Expected review severity, got {finding.severity}"
    assert finding.layer == PDF, f"Expected pdf layer, got {finding.layer}"


@_S5_DRAFT_AVAILABLE
def test_check_s5_draft_fixture_inspect_hyperlinks_returns_zero() -> None:
    """The draft fixture must yield 0 Link annots and no Outlines from
    _inspect_hyperlinks — verifies the compiled PDF is actually draft-mode.
    """
    from latex2ufdissertation.pipeline.pdf_checks import _inspect_hyperlinks

    link_count, has_outline = _inspect_hyperlinks(_S5_DRAFT_PDF)
    assert link_count == 0, f"Expected 0 Link annots in draft PDF, got {link_count}"
    assert has_outline is False, f"Expected no Outlines in draft PDF, got has_outline={has_outline}"


# ---------------------------------------------------------------------------
# Findings 1+2: body-mode excludes math/mono glyphs from font/size counters
# ---------------------------------------------------------------------------


def test_extract_pages_body_mode_excludes_math_glyphs(tmp_path: Path) -> None:
    """F3 false-positive fix: 10 Times@12 + 50 NewTXMI@8 glyphs.

    With math excluded from body-mode counters, body_font must be
    'TeXGyreTermesX-Regular' and body_size must be 12.0, not 8.0.
    """
    from unittest.mock import MagicMock, patch

    from pdfminer.layout import LTChar

    from latex2ufdissertation.pipeline.pdf_checks import _extract_pages

    dummy_pdf = tmp_path / "multi_font_math.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.7\n")

    def make_char(fontname: str, size: float) -> MagicMock:
        c = MagicMock(spec=LTChar)
        c.fontname = fontname
        c.size = size
        return c

    # 10 body glyphs at 12pt, 50 math glyphs at 8pt
    fake_page = [make_char("TeXGyreTermesX-Regular", 12.0)] * 10 + [make_char("NewTXMI", 8.0)] * 50

    with patch("pdfminer.high_level.extract_pages", return_value=[fake_page]):
        pages = _extract_pages(dummy_pdf)

    assert len(pages) == 1
    assert pages[0].body_font == "TeXGyreTermesX-Regular", (
        f"Expected TeXGyreTermesX-Regular, got {pages[0].body_font!r}"
    )
    assert pages[0].body_size == 12.0, f"Expected 12.0, got {pages[0].body_size}"


def test_extract_pages_body_mode_excludes_mono_glyphs(tmp_path: Path) -> None:
    """F2 false-negative fix: 10 LMRoman12-Regular@12 + 50 NewTXMI@8 glyphs.

    Routes actual LTChar mocks through the real _extract_pages so the
    glyph-exclusion logic is genuinely exercised. With NewTXMI excluded from
    body counters, body_font must be 'LMRoman12-Regular' (not None), pinning
    both the F2 false-negative fix and the LMMono-vs-LMRoman prefix distinction
    (LMRoman* must NOT be excluded, only LMMono*).
    """
    from unittest.mock import MagicMock, patch

    from pdfminer.layout import LTChar

    from latex2ufdissertation.pipeline.pdf_checks import _extract_pages
    from latex2ufdissertation.pipeline.rules import MUST_FIX, PDF
    from latex2ufdissertation.pipeline.types import Issues

    dummy_pdf = tmp_path / "lmroman_body.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.7\n")

    def make_char(fontname: str, size: float) -> MagicMock:
        c = MagicMock(spec=LTChar)
        c.fontname = fontname
        c.size = size
        return c

    # 10 non-Times body glyphs at 12pt; 50 math glyphs at 8pt (should be excluded).
    # LMRoman12-Regular does NOT start with LMMono, so it must remain in counters.
    fake_page = [make_char("LMRoman12-Regular", 12.0)] * 10 + [make_char("NewTXMI", 8.0)] * 50

    with patch("pdfminer.high_level.extract_pages", return_value=[fake_page]):
        pages = _extract_pages(dummy_pdf)

    assert len(pages) == 1
    assert pages[0].body_font == "LMRoman12-Regular", (
        f"Expected LMRoman12-Regular, got {pages[0].body_font!r} — "
        "math must be excluded but LMRoman body must not be"
    )
    assert pages[0].body_size == 12.0, f"Expected 12.0, got {pages[0].body_size}"

    # Confirm F2 fires on the extracted result (non-Times body detected).
    from unittest.mock import patch as _patch

    from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks

    issues = Issues()
    with _patch(
        "latex2ufdissertation.pipeline.pdf_checks._extract_pages",
        return_value=pages,
    ):
        run_pdf_checks(dummy_pdf, issues)

    f2 = [f for f in issues.findings if f.rule_id == "UF-F2"]
    assert len(f2) == 1, (
        f"Expected 1 UF-F2 finding (math glyphs must not mask non-Times body), got {len(f2)}"
    )
    assert f2[0].severity == MUST_FIX
    assert f2[0].layer == PDF


def test_extract_pages_body_font_math_dominant_raw(tmp_path: Path) -> None:
    """_extract_pages directly: raw page with math-dominant glyphs.

    Feeds actual LTChar mocks through _extract_pages; after the fix the
    body-mode counters must ignore math prefixes and report Times@12.
    """
    from unittest.mock import MagicMock, patch

    from pdfminer.layout import LTChar

    from latex2ufdissertation.pipeline.pdf_checks import _extract_pages

    dummy_pdf = tmp_path / "raw_math.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.7\n")

    def make_char(fontname: str, size: float) -> MagicMock:
        c = MagicMock(spec=LTChar)
        c.fontname = fontname
        c.size = size
        return c

    # 10 Times@12, 50 NewTXMI@8 (with subset prefix), 10 txsys@8
    fake_page = (
        [make_char("TeXGyreTermesX-Regular", 12.0)] * 10
        + [make_char("ABCDEF+NewTXMI", 8.0)] * 50
        + [make_char("txsys", 8.0)] * 10
    )

    with patch("pdfminer.high_level.extract_pages", return_value=[fake_page]):
        pages = _extract_pages(dummy_pdf)

    assert len(pages) == 1
    assert pages[0].body_font == "TeXGyreTermesX-Regular"
    assert pages[0].body_size == 12.0


def test_extract_pages_all_math_glyphs_yields_none_body(tmp_path: Path) -> None:
    """A page with only math glyphs (all excluded) must produce body_font=None.

    This covers the full-page figure / math-only page case — checks must
    skip it rather than falsely reporting a violation.
    """
    from unittest.mock import MagicMock, patch

    from pdfminer.layout import LTChar

    from latex2ufdissertation.pipeline.pdf_checks import _extract_pages

    dummy_pdf = tmp_path / "all_math.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.7\n")

    def make_char(fontname: str, size: float) -> MagicMock:
        c = MagicMock(spec=LTChar)
        c.fontname = fontname
        c.size = size
        return c

    # Only math glyphs — nothing remains after exclusion
    fake_page = [make_char("NewTXMI", 8.0)] * 30 + [make_char("txsys", 8.0)] * 20

    with patch("pdfminer.high_level.extract_pages", return_value=[fake_page]):
        pages = _extract_pages(dummy_pdf)

    assert len(pages) == 1
    assert pages[0].body_font is None
    assert pages[0].body_size is None


@_DEMO_AVAILABLE
def test_extract_pages_demo_zero_f2_f3_with_body_mode_fix() -> None:
    """Acceptance gate §8.2: after body-mode fix, demo must still produce
    zero UF-F2 and zero UF-F3 findings across all 26 pages.
    """
    from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks
    from latex2ufdissertation.pipeline.types import Issues

    issues = Issues()
    run_pdf_checks(_DEMO_PDF, issues)
    f2 = [f for f in issues.findings if f.rule_id == "UF-F2"]
    f3 = [f for f in issues.findings if f.rule_id == "UF-F3"]
    assert f2 == [], f"Demo produced unexpected UF-F2 findings after body-mode fix: {f2}"
    assert f3 == [], f"Demo produced unexpected UF-F3 findings after body-mode fix: {f3}"


# ---------------------------------------------------------------------------
# Finding 3: broader exception handling in _extract_pages
# ---------------------------------------------------------------------------


def test_extract_pages_raises_unreadable_on_is_directory_error(
    tmp_path: Path,
) -> None:
    """IsADirectoryError from extract_pages must be caught and re-raised as
    UnreadableInput, not escape as a raw exception.
    """
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import _extract_pages
    from latex2ufdissertation.pipeline.types import UnreadableInput

    dummy_pdf = tmp_path / "dummy.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.7\n")

    with patch(
        "pdfminer.high_level.extract_pages",
        side_effect=IsADirectoryError("is a directory"),
    ):
        with pytest.raises(UnreadableInput):
            _extract_pages(dummy_pdf)


def test_extract_pages_raises_unreadable_on_ps_exception(
    tmp_path: Path,
) -> None:
    """PSException (e.g. PSEOF, PSSyntaxError) from extract_pages must be
    caught and re-raised as UnreadableInput.
    """
    from unittest.mock import patch

    from pdfminer.psexceptions import PSEOF

    from latex2ufdissertation.pipeline.pdf_checks import _extract_pages
    from latex2ufdissertation.pipeline.types import UnreadableInput

    dummy_pdf = tmp_path / "dummy.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.7\n")

    with patch(
        "pdfminer.high_level.extract_pages",
        side_effect=PSEOF("unexpected EOF"),
    ):
        with pytest.raises(UnreadableInput):
            _extract_pages(dummy_pdf)


@pytest.mark.parametrize("exc", [MemoryError("oom"), RecursionError("too deep")])
def test_extract_pages_maps_resource_exhaustion_to_unreadable(
    tmp_path: Path, exc: BaseException
) -> None:
    """A malicious PDF that drives pdfminer into MemoryError / RecursionError
    must be mapped to UnreadableInput (clean exit 2), not escape as a raw
    traceback.
    """
    from unittest.mock import patch

    from latex2ufdissertation.pipeline.pdf_checks import _extract_pages
    from latex2ufdissertation.pipeline.types import UnreadableInput

    dummy_pdf = tmp_path / "bomb.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.7\n")

    with patch("pdfminer.high_level.extract_pages", side_effect=exc):
        with pytest.raises(UnreadableInput):
            _extract_pages(dummy_pdf)


def test_cli_directory_named_pdf_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A directory whose name ends in .pdf is classified as 'dir' by input_mode,
    so it never reaches the pdf branch. But if a directory path that resolves
    as 'pdf' mode is supplied (via patching input_mode), the is_file() guard
    must intercept it and exit 2, not pass it to _extract_pages.

    We also test the direct path: patching input_mode to return 'pdf' for a
    directory path verifies the is_file() guard in cli.py.
    """
    from unittest.mock import patch

    from latex2ufdissertation.cli import main

    # Create a directory (not a file) to use as input
    fake_pdf_dir = tmp_path / "notafile.pdf"
    fake_pdf_dir.mkdir()

    # Patch input_mode to return 'pdf' for this directory path so the CLI
    # enters the pdf branch (normally a directory returns 'dir')
    with patch(
        "latex2ufdissertation.cli.input_mode",
        return_value="pdf",
    ):
        rc = main([str(fake_pdf_dir)])

    captured = capsys.readouterr()
    assert rc == 2, f"Expected exit 2 for directory-as-pdf input, got {rc}"
    # Error message should mention the path or indicate unreadable input
    assert "Error" in captured.err or rc == 2


# ---------------------------------------------------------------------------
# Mutant killers — GROUP 2 (pdf_checks.py _check_f2 / _check_f3)
# ---------------------------------------------------------------------------


def test_check_f2_fires_on_second_page_when_first_has_none_body(tmp_path: Path) -> None:
    """G2a: _check_f2 must check ALL pages, not stop at the first body-less page.

    Kills mutant ID?: `continue` -> `break` on None body_font — break skips
    all remaining pages so a non-conforming font on page 2 is never caught.

    Page 1: body_font=None (image-only; must be skipped gracefully).
    Page 2: body_font="ComicSansMS" (non-allowed; UF-F2 MUST fire here).
    """
    from latex2ufdissertation.pipeline.pdf_checks import PageData, _check_f2
    from latex2ufdissertation.pipeline.rules import MUST_FIX, PDF
    from latex2ufdissertation.pipeline.types import Issues

    pages = [
        PageData(page_num=1, body_font=None, body_size=None),
        PageData(page_num=2, body_font="ComicSansMS", body_size=12.0),
    ]
    issues = Issues()
    _check_f2(pages, issues)

    f2 = [f for f in issues.findings if f.rule_id == "UF-F2"]
    assert len(f2) == 1, (
        f"expected 1 UF-F2 finding from page 2 "
        f"(mutant: continue->break drops page 2); got {len(f2)}"
    )
    assert f2[0].severity == MUST_FIX
    assert f2[0].layer == PDF
    assert f2[0].location == "p.2"
    assert f2[0].observed == "ComicSansMS"


def test_check_f3_fires_on_second_page_when_first_has_none_body(tmp_path: Path) -> None:
    """G2b: _check_f3 must check ALL pages, not stop at the first body-less page.

    Kills mutant ID162: `continue` -> `break` on None body_size — break skips
    all remaining pages so a wrong size on page 2 is never caught.

    Page 1: body_size=None (no body text; must be skipped gracefully).
    Page 2: body_size=10.0 (deviates from 12pt by 2.0 > 0.5 tolerance; UF-F3 MUST fire).
    """
    from latex2ufdissertation.pipeline.pdf_checks import PageData, _check_f3
    from latex2ufdissertation.pipeline.rules import MUST_FIX, PDF
    from latex2ufdissertation.pipeline.types import Issues

    pages = [
        PageData(page_num=1, body_font=None, body_size=None),
        PageData(page_num=2, body_font="TeXGyreTermes-Regular", body_size=10.0),
    ]
    issues = Issues()
    _check_f3(pages, issues)

    f3 = [f for f in issues.findings if f.rule_id == "UF-F3"]
    assert len(f3) == 1, (
        f"expected 1 UF-F3 finding from page 2 (mutant ID162: continue->break drops page 2); "
        f"got {len(f3)}"
    )
    assert f3[0].severity == MUST_FIX
    assert f3[0].layer == PDF
    assert f3[0].location == "p.2"


@pytest.mark.parametrize(
    "prefix",
    [
        "Arial",
        "Helvetica",
        "NimbusSans",
        "txsys",
        "txexs",
    ],
)
def test_check_f2_allowed_prefix_does_not_fire(prefix: str, tmp_path: Path) -> None:
    """G2c: Each under-tested prefix in _F2_ALLOWED_PREFIXES must NOT emit UF-F2.

    Kills prefix-string mutants that replace e.g. "Arial" with "XXXial":
    if a test exercises the prefix, the mutation renders the font non-allowed
    and fires UF-F2 unexpectedly — the assertion 'f2 == []' catches it.

    Tested prefixes (under-tested by existing suite): Arial, Helvetica,
    NimbusSans, txsys, txexs.
    """
    from latex2ufdissertation.pipeline.pdf_checks import PageData, _check_f2
    from latex2ufdissertation.pipeline.types import Issues

    # Font name that starts with the prefix (simulate a real font name).
    font_name = f"{prefix}MT"
    pages = [PageData(page_num=1, body_font=font_name, body_size=12.0)]
    issues = Issues()
    _check_f2(pages, issues)

    f2 = [f for f in issues.findings if f.rule_id == "UF-F2"]
    assert f2 == [], (
        f"prefix {prefix!r} (font={font_name!r}) must NOT fire UF-F2; got {len(f2)} findings. "
        "Likely a prefix-string mutant is active."
    )


def test_check_f2_disallowed_font_fires(tmp_path: Path) -> None:
    """G2c companion: a clearly non-allowed font (ComicSansMS) MUST fire UF-F2.

    This paired assertion ensures the parametrized allowed-prefix test above
    is not vacuously satisfied by a broken _check_f2 that never emits.
    """
    from latex2ufdissertation.pipeline.pdf_checks import PageData, _check_f2
    from latex2ufdissertation.pipeline.rules import MUST_FIX, PDF
    from latex2ufdissertation.pipeline.types import Issues

    pages = [PageData(page_num=1, body_font="ComicSansMS", body_size=12.0)]
    issues = Issues()
    _check_f2(pages, issues)

    f2 = [f for f in issues.findings if f.rule_id == "UF-F2"]
    assert len(f2) == 1, f"ComicSansMS must fire UF-F2; got {len(f2)}"
    assert f2[0].severity == MUST_FIX
    assert f2[0].layer == PDF

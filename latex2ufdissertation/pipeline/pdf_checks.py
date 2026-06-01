"""PDF-layer validation checks for UF dissertations.

Entry point: `run_pdf_checks(pdf_path, issues)`. pdfminer.six is lazy-
imported inside the function so source-only / --dry-run paths never import
it. All checks are named `_check_*` private helpers called from
`run_pdf_checks`; later units (F2, F3, S5, ...) add their helpers here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from latex2ufdissertation.pipeline.types import Issues, MissingToolchain, UnreadableInput

# Random 6-uppercase-letter subset prefix added by the PDF engine per compile;
# strip before recording font names so findings are deterministic.
_SUBSET_RE = re.compile(r"^[A-Z]{6}\+")


@dataclass(frozen=True)
class PageData:
    """Per-page summary extracted from the PDF.

    page_num: 1-based page index.
    body_font: most-common font name by glyph count (subset prefix stripped),
        or None when the page has zero text glyphs.
    body_size: most-common rounded glyph size (1 decimal), or None when
        body_font is None.
    """

    page_num: int
    body_font: str | None
    body_size: float | None


def _iter_chars(element):  # type: ignore[no-untyped-def]
    """Recursively yield every LTChar inside *element*.

    Chars can be nested inside LTFigure or other containers; a fixed
    LTPage→LTTextBox→LTTextLine→LTChar assumption silently misses them.
    """
    from pdfminer.layout import LTChar

    for item in element:
        if isinstance(item, LTChar):
            yield item
        else:
            try:
                yield from _iter_chars(item)
            except TypeError:
                pass


def _extract_pages(pdf_path: Path) -> list[PageData]:
    """Walk *pdf_path* with pdfminer and return one PageData per page.

    body_font = most-common font name by glyph count (subset prefix stripped).
    body_size = most-common round(char.size, 1) by glyph count.
    Tie-break: (count desc, name desc) — deterministic across Python versions.

    Raises MissingToolchain if pdfminer.six is not installed.
    Raises UnreadableInput if pdfminer cannot parse the PDF.
    """
    try:
        from pdfminer.high_level import extract_pages
        from pdfminer.pdfexceptions import PDFException
    except ImportError as exc:
        raise MissingToolchain(
            "pdfminer.six not installed — run `pip install pdfminer.six`"
        ) from exc

    from collections import Counter

    results: list[PageData] = []
    try:
        for page_num, page_layout in enumerate(extract_pages(str(pdf_path)), start=1):
            font_counter: Counter[str] = Counter()
            size_counter: Counter[float] = Counter()
            for char in _iter_chars(page_layout):
                fname = _SUBSET_RE.sub("", char.fontname)
                font_counter[fname] += 1
                size_counter[round(char.size, 1)] += 1
            if font_counter:
                # Tie-break: count desc then name desc → deterministic.
                body_font = max(
                    font_counter.items(), key=lambda kv: (kv[1], kv[0])
                )[0]
                body_size = max(
                    size_counter.items(), key=lambda kv: (kv[1], kv[0])
                )[0]
            else:
                body_font = None
                body_size = None
            results.append(PageData(page_num=page_num, body_font=body_font, body_size=body_size))
    except PDFException as exc:
        raise UnreadableInput(f"Cannot parse PDF: {pdf_path.name} — {exc}") from exc

    return results


def _check_s1(pages: list[PageData], issues: Issues) -> None:
    """UF-S1: PDF must have at least one page with extractable text.

    S1 fires when the PDF has zero pages, or when every page's body_font
    is None (all-image / fully-encrypted PDF). A file that raised a
    PDFSyntaxError is already caught upstream as UnreadableInput; this
    check covers the narrower 'parses but empty' case.
    """
    if not pages or all(p.body_font is None for p in pages):
        issues.add(
            "UF-S1",
            observed="PDF has no extractable text/pages",
            required="a rendered PDF with content",
        )


def run_pdf_checks(pdf_path: Path, issues: Issues) -> None:
    """Run all PDF-layer checks against *pdf_path*, appending findings to
    *issues*. pdfminer.six is imported lazily here so callers that never
    reach the PDF layer (--dry-run, source-only) do not pay the import cost.

    Raises MissingToolchain (exit 3) if pdfminer.six is not installed.
    Raises UnreadableInput (exit 2) if the PDF cannot be parsed at all.
    """
    # _extract_pages propagates MissingToolchain / UnreadableInput on its own.
    pages = _extract_pages(pdf_path)

    _check_s1(pages, issues)
    # Future checks (F2, F3, S5, …) are added here as _check_*(pages, issues).

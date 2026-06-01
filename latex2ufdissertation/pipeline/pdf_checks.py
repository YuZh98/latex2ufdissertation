"""PDF-layer validation checks for UF dissertations.

Entry point: `run_pdf_checks(pdf_path, issues)`. pdfminer.six is lazy-
imported inside the function so source-only / --dry-run paths never import
it. All checks are named `_check_*` private helpers called from
`run_pdf_checks`; later units (F2, F3, S5, ...) add their helpers here.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from latex2ufdissertation.pipeline.rules import PDF
from latex2ufdissertation.pipeline.types import Issues, MissingToolchain, UnreadableInput

# Random 6-uppercase-letter subset prefix added by the PDF engine per compile;
# strip before recording font names so findings are deterministic.
_SUBSET_RE = re.compile(r"^[A-Z]{6}\+")

# Font-name prefixes that represent math or monospace glyphs.
# These are excluded from the body-mode font/size counters in _extract_pages so
# that pages with heavy math or code listings don't skew body_font / body_size:
#   NewTX*  — newtx math glyphs (NewTXMI, NewTXSY, …)
#   txsys   — newtx symbol font
#   txexs   — newtx extra-symbol font
#   LMMono  — Computer Modern Monospace (code/verbatim; NOT LMRoman which is body)
# Applied to the subset-stripped font name, so ABCDEF+NewTXMI is also excluded.
_NON_BODY_FONT_PREFIXES: tuple[str, ...] = (
    "NewTX",
    "txsys",
    "txexs",
    "LMMono",
)

# UF-F3 constants: required body-mode size and rounding tolerance (pt).
# A deviation of more than _F3_SIZE_TOLERANCE_PT from _F3_REQUIRED_BODY_PT
# indicates the student overrode the template's 12-point default globally.
_F3_REQUIRED_BODY_PT: float = 12.0
_F3_SIZE_TOLERANCE_PT: float = 0.5

# UF-F2 allowlist: family name prefixes that are legitimate for UF dissertations.
#
# Derived from the canonical demo PDF (examples/demo_dissertation/main.pdf) plus
# UF's explicit Arial allowance. The demo's body-mode font across all 26 pages is
# exclusively TeXGyreTermesX-* (Times New Roman equivalent loaded by the newtx
# family). The remaining prefixes cover math-dominant and monospace-dominant pages
# that appear in real dissertations with heavy math or code listings:
#
#   TeXGyreTermes  — Times body (newtx/TeXGyreTermes, UF default)
#   NewTX          — newtx math glyphs (NewTXMI, etc.)
#   txsys          — newtx symbol font
#   txexs          — newtx extra-symbol font
#   LMMono         — Computer Modern monospace (code/verbatim pages)
#   Arial          — UF's explicit Arial allowance (Windows CID font)
#   Helvetica      — metric-compatible Arial substitute
#   NimbusSans     — GhostScript/TeXLive Helvetica substitute
#
# The prefixes below cover real Times New Roman embeds from pdf-input mode (a PDF
# compiled with a true Times font rather than the template's TeXGyreTermes). UF
# allows Times New Roman or Arial; both render paths are conforming:
#
#   Times          — covers TimesNewRomanPSMT (Windows/Adobe CID embed),
#                    Times-Roman (Type 1 canonical), TimesNewRoman (bare stem)
#   NimbusRom      — covers NimbusRomNo9L / NimbusRoman
#                    (GhostScript/TeXLive Times substitute, parallel to NimbusSans
#                    which is already listed as the Helvetica/Arial substitute)
#
# Any font whose prefix-stripped base name does NOT start with one of these
# prefixes is a non-conforming body font (e.g. LMRoman*, cmr10, Palatino-Roman).
_F2_ALLOWED_PREFIXES: tuple[str, ...] = (
    "TeXGyreTermes",
    "NewTX",
    "txsys",
    "txexs",
    "LMMono",
    "Arial",
    "Helvetica",
    "NimbusSans",
    # Real Times New Roman render names (pdf-input mode; UF allows Times or Arial).
    "Times",  # TimesNewRomanPSMT / Times-Roman / TimesNewRoman
    "NimbusRom",  # NimbusRomNo9L / NimbusRoman (GhostScript Times substitute)
)


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
        from pdfminer.psexceptions import PSException
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
                # Exclude math and monospace glyphs so body_font/body_size
                # reflect actual body text, not incidental math/code content.
                if any(fname.startswith(pfx) for pfx in _NON_BODY_FONT_PREFIXES):
                    continue
                font_counter[fname] += 1
                size_counter[round(char.size, 1)] += 1
            if font_counter:
                # Tie-break: count desc then name desc → deterministic.
                body_font = max(font_counter.items(), key=lambda kv: (kv[1], kv[0]))[0]
                body_size = max(size_counter.items(), key=lambda kv: (kv[1], kv[0]))[0]
            else:
                body_font = None
                body_size = None
            results.append(PageData(page_num=page_num, body_font=body_font, body_size=body_size))
    except (PDFException, PSException, OSError, MemoryError, RecursionError) as exc:
        # MemoryError / RecursionError are not OSError subclasses; a malicious or
        # pathological PDF can drive pdfminer into either. Map them to a clean
        # UnreadableInput (exit 2) rather than letting a raw traceback escape.
        raise UnreadableInput(f"Cannot parse PDF: {pdf_path.name} — {exc}") from exc

    return results


def _check_f2(pages: list[PageData], issues: Issues) -> None:
    """UF-F2: body-mode font must belong to a UF-approved family (PDF layer).

    For each page whose body-mode font is not None: if the font's base name
    does not start with any of the prefixes in _F2_ALLOWED_PREFIXES, emit a
    must-fix finding with layer=PDF (the registry layer for UF-F2 is BOTH;
    the PDF layer is the authoritative must-fix half).

    The source-layer half (checks.py UF-F2 emit sites) emits at severity
    REVIEW so that font overrides neutralized by the template's newtx reload
    do not produce a false must-fix in the absence of a compiled PDF.
    """
    for page in pages:
        if page.body_font is None:
            continue
        if not any(page.body_font.startswith(prefix) for prefix in _F2_ALLOWED_PREFIXES):
            issues.add(
                "UF-F2",
                layer=PDF,
                location=f"p.{page.page_num}",
                observed=page.body_font,
                required="Times New Roman or Arial body font",
                fix_hint=(
                    "Rendered body font is not Times New Roman or Arial; "
                    "remove any \\fontfamily / \\setmainfont override in the source."
                ),
            )


def _check_f3(pages: list[PageData], issues: Issues) -> None:
    r"""UF-F3: body-mode size must be 12pt throughout (PDF layer).

    For each page whose body_size is not None: if the size deviates from
    _F3_REQUIRED_BODY_PT by more than _F3_SIZE_TOLERANCE_PT, emit a must-fix
    finding with layer=PDF. The registry severity for UF-F3 is must-fix so
    no per-call severity override is needed; pass layer=PDF to mark this as
    the PDF-authoritative half.

    The source-layer half (checks.py UF-F3 emit sites) emits at severity
    REVIEW so that localized legal sizing (a one-off ``\fontsize`` on a
    title/caption) does not produce a false must-fix in the absence of a
    compiled PDF.
    """
    for page in pages:
        if page.body_size is None:
            continue
        if abs(page.body_size - _F3_REQUIRED_BODY_PT) > _F3_SIZE_TOLERANCE_PT:
            issues.add(
                "UF-F3",
                layer=PDF,
                location=f"p.{page.page_num}",
                observed=f"{page.body_size}pt body text",
                required="12-point body text",
                fix_hint=(
                    "Rendered body text is not 12 pt; "
                    "check for a \\fontsize{...}{...}\\selectfont override affecting the body."
                ),
            )


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


def _inspect_hyperlinks(pdf_path: Path) -> tuple[int, bool]:
    """Inspect *pdf_path* for Link annotations and a document Outline.

    Returns ``(link_annot_count, has_outline)`` where:
    - *link_annot_count* is the total number of ``/Subtype /Link`` annotations
      across all pages.
    - *has_outline* is True when the document catalog contains an ``Outlines``
      entry (i.e. bookmarks were generated by hyperref).

    Lazy-imports pdfminer pieces at call time (consistent with module style).
    Raises any pdfminer import error or PDFException if the file is
    unreadable; callers that need graceful degradation must wrap accordingly.
    """
    from pdfminer.pdfdocument import PDFDocument
    from pdfminer.pdfpage import PDFPage
    from pdfminer.pdfparser import PDFParser
    from pdfminer.pdftypes import resolve1
    from pdfminer.psparser import literal_name

    link_count = 0
    with open(pdf_path, "rb") as fh:
        parser = PDFParser(fh)
        doc = PDFDocument(parser)

        # Count /Link annotations across all pages.
        # pdfminer parses PDF name objects (e.g. /Link) as PSLiteral instances,
        # not plain strings, so we use literal_name() to extract the string value
        # rather than comparing PSLiteral directly to "Link" (which is always False).
        for page in PDFPage.create_pages(doc):
            if page.annots is None:
                continue
            annots = resolve1(page.annots)
            if not isinstance(annots, list):
                continue
            for annot_ref in annots:
                annot = resolve1(annot_ref)
                if not isinstance(annot, dict):
                    continue
                subtype = annot.get("Subtype")
                if subtype is not None and literal_name(resolve1(subtype)) == "Link":
                    link_count += 1

        has_outline = "Outlines" in doc.catalog

    return link_count, has_outline


def _check_s5(pdf_path: Path, issues: Issues) -> None:
    """UF-S5: PDF must carry functional hyperlink annotations and a document
    outline, indicating hyperref is enabled.

    Fires ONLY when BOTH link_annot_count == 0 AND no Outlines in the
    catalog — the "hyperref disabled / draft mode" signal. A document with
    no cross-references but a populated outline (has_outline=True) is valid;
    requiring both avoids false positives on short documents.

    Degrades gracefully: if annotation/outline inspection raises an unexpected
    exception (e.g. malformed-but-parseable structure), S5 does NOT fire and
    does NOT propagate. UnreadableInput/MissingToolchain already propagated
    from _extract_pages before this function is reached, so a broad catch here
    is safe and intentional (S5 is advisory / review-tier).
    """
    try:
        link_count, has_outline = _inspect_hyperlinks(pdf_path)
    except Exception as exc:  # noqa: BLE001  (advisory check — must not crash the run)
        logging.getLogger(__name__).warning("UF-S5 hyperlink inspection skipped: %s", exc)
        return

    if link_count == 0 and not has_outline:
        issues.add(
            "UF-S5",
            layer=PDF,
            observed=(
                "no link annotations or document outline"
                " (hyperref appears disabled, e.g. \\hypersetup{draft})"
            ),
            required="functional hyperlinks (hyperref enabled)",
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
    _check_f2(pages, issues)
    _check_f3(pages, issues)
    _check_s5(pdf_path, issues)

"""UF rule registry — single source of truth for rule metadata.

Each Rule entry mirrors a heading in docs/uf-rules.md. The registry is
hand-synced with the catalog; tests/test_rules.py asserts that every
UF-* identifier in the catalog has a matching Rule entry here (and vice
versa), so the two cannot drift silently.

A v0.1 emit site rebrands to `issues.add(rule_id="UF-XYZ", ...)`. The
collector resolves severity, layer, source_url, and fix_hint from this
registry so call sites stay terse.
"""

from __future__ import annotations

from dataclasses import dataclass

# Severity tier literals. Constants instead of free strings so a typo
# fails at import time rather than silently producing an unknown tier.
MUST_FIX = "must-fix"
REVIEW = "review"

# Validation layer literals. Same rationale.
SOURCE = "source"
PDF = "pdf"
BOTH = "both"

# Stable enumeration of fatal-failure reasons. Mirrored in
# Issues.exit_reason and the JSON `summary.exit_reason` field.
EXIT_REASON_CLEAN = "clean"
EXIT_REASON_REVIEW_PRESENT = "review_present"
EXIT_REASON_MUST_FIX_PRESENT = "must_fix_present"
EXIT_REASON_COMPILE_FAILURE = "compile_failure"
EXIT_REASON_UNREADABLE_INPUT = "unreadable_input"
EXIT_REASON_THESIS_INPUT = "thesis_input"
EXIT_REASON_MISSING_TOOLCHAIN = "missing_toolchain"

EXIT_REASONS = frozenset(
    {
        EXIT_REASON_CLEAN,
        EXIT_REASON_REVIEW_PRESENT,
        EXIT_REASON_MUST_FIX_PRESENT,
        EXIT_REASON_COMPILE_FAILURE,
        EXIT_REASON_UNREADABLE_INPUT,
        EXIT_REASON_THESIS_INPUT,
        EXIT_REASON_MISSING_TOOLCHAIN,
    }
)

_CATALOG = "https://github.com/YuZh98/latex2ufdissertation/blob/main/docs/uf-rules.md"


def _anchor(rule_id: str, slug: str) -> str:
    # GitHub-Markdown auto-anchor for headings of the form
    # `### UF-F1 — Margins` → `#uf-f1--margins` (em-dash drops, double
    # hyphen from the surrounding spaces). Construct once per rule.
    return f"{_CATALOG}#{rule_id.lower()}--{slug}"


@dataclass(frozen=True)
class Rule:
    id: str
    severity: str
    layer: str
    title: str
    source_url: str
    fix_hint: str | None = None


RULES: dict[str, Rule] = {
    # Formatting (F)
    "UF-F1": Rule(
        "UF-F1",
        MUST_FIX,
        BOTH,
        "Margins",
        _anchor("UF-F1", "margins"),
        fix_hint=(
            "Remove the margin override; the UF template's `geometry` package "
            "(cls:153-157) sets the required 1 inch all around."
        ),
    ),
    "UF-F2": Rule(
        "UF-F2",
        MUST_FIX,
        BOTH,
        "Font family",
        _anchor("UF-F2", "font-family"),
        fix_hint=(
            "Remove the font override; UF requires Times New Roman or Arial "
            "(cls:167-169 loads them). Note: the template's newtx reload at "
            "\\begin{document} may neutralize some overrides — the PDF layer "
            "adjudicates whether the rendered body is actually non-conforming."
        ),
    ),
    "UF-F3": Rule(
        "UF-F3",
        MUST_FIX,
        BOTH,
        "Font size 12pt",
        _anchor("UF-F3", "font-size-12pt"),
        fix_hint=(
            "Remove the `\\fontsize{...}{...}\\selectfont` override; "
            "the UF template's `\\LoadClass[12pt]` (cls:1) sets 12-point throughout."
        ),
    ),
    "UF-F4": Rule(
        "UF-F4",
        MUST_FIX,
        BOTH,
        "Line spacing",
        _anchor("UF-F4", "line-spacing"),
        fix_hint=(
            "Remove the line-spacing override; the UF template's `\\doublespacing` "
            "(cls:198) sets the required body spacing with documented exceptions."
        ),
    ),
    "UF-F5": Rule(
        "UF-F5",
        MUST_FIX,
        SOURCE,
        "Text alignment (ragged-right)",
        _anchor("UF-F5", "text-alignment-ragged-right"),
        fix_hint=(
            "Remove the override; the UF template's `\\raggedright` (cls:171) "
            "produces the required ragged-right alignment."
        ),
    ),
    "UF-F6": Rule(
        "UF-F6",
        MUST_FIX,
        BOTH,
        "Page numbering (arabic, bottom-center)",
        _anchor("UF-F6", "page-numbering-arabic-bottom-center"),
        fix_hint=(
            "Remove the page-numbering override; UF requires arabic numerals "
            "centered at bottom (cls:179-188). `\\pagenumbering{arabic}` is fine."
        ),
    ),
    "UF-F7": Rule(
        "UF-F7",
        MUST_FIX,
        SOURCE,
        "Paragraph indentation",
        _anchor("UF-F7", "paragraph-indentation"),
        fix_hint=(
            "Remove the zero-`\\parindent` override; the UF template's "
            "`\\indentfirst` (cls:203) + `\\parindent=1cm` (cls:1010) "
            "produce the required first-line indentation."
        ),
    ),
    "UF-F8": Rule(
        "UF-F8",
        MUST_FIX,
        SOURCE,
        "Required page order + presence",
        _anchor("UF-F8", "required-page-order--presence"),
        fix_hint="Set the missing \\set*File macro in main.tex and ensure the file exists.",
    ),
    "UF-F9": Rule(
        "UF-F9",
        MUST_FIX,
        SOURCE,
        "Singleton structure",
        _anchor("UF-F9", "singleton-structure"),
        fix_hint=(
            "UF requires a singleton structure (one abstract, one ToC, "
            "one reference list). Remove the duplicate."
        ),
    ),
    "UF-F10": Rule(
        "UF-F10",
        MUST_FIX,
        SOURCE,
        "Chapter scaffold",
        _anchor("UF-F10", "chapter-scaffold"),
        fix_hint=(
            "Add chapters until the document has at least 3 "
            "(UF S1 + S3: introductory + main body + closing summary)."
        ),
    ),
    "UF-F11": Rule(
        "UF-F11",
        MUST_FIX,
        SOURCE,
        "Heading styles (5-tier hierarchy)",
        _anchor("UF-F11", "heading-styles-5-tier-hierarchy"),
        fix_hint=(
            "Remove the `\\titleformat` redefinition; the UF template enforces "
            "the 5-tier heading hierarchy by construction (cls:304-362)."
        ),
    ),
    "UF-F12": Rule(
        "UF-F12",
        REVIEW,
        PDF,
        "Text flow within chapter (no blank gaps)",
        _anchor("UF-F12", "text-flow-within-chapter-no-blank-gaps"),
    ),
    "UF-F13": Rule(
        "UF-F13",
        MUST_FIX,
        SOURCE,
        "Document class is `ufdissertation`",
        _anchor("UF-F13", "document-class-is-ufdissertation"),
        fix_hint="Set \\documentclass{ufdissertation} (Fall 2025+ template required).",
    ),
    "UF-F14": Rule(
        "UF-F14",
        MUST_FIX,
        SOURCE,
        "Required metadata macros set",
        _anchor("UF-F14", "required-metadata-macros-set"),
        fix_hint="Set the missing metadata macro with a non-empty value in main.tex.",
    ),
    "UF-F15": Rule(
        "UF-F15",
        MUST_FIX,
        BOTH,
        "Abstract word count ≤ 350",
        _anchor("UF-F15", "abstract-word-count--350"),
        fix_hint=(
            "Trim the abstract to <= 350 words "
            "(catalog § UF-F15, template's own abstractFile.tex specifies this cap)."
        ),
    ),
    "UF-F16": Rule(
        "UF-F16",
        REVIEW,
        SOURCE,
        "Subsection pairing",
        _anchor("UF-F16", "subsection-pairing"),
    ),
    # Submission + structural (S)
    "UF-S1": Rule(
        "UF-S1", MUST_FIX, PDF, "PDF output present", _anchor("UF-S1", "pdf-output-present")
    ),
    "UF-S2": Rule(
        "UF-S2",
        MUST_FIX,
        SOURCE,
        "Required sections present (rejection-driver subset of F8)",
        _anchor("UF-S2", "required-sections-present-rejection-driver-subset-of-f8"),
    ),
    "UF-S3": Rule(
        "UF-S3",
        MUST_FIX,
        SOURCE,
        "Broken internal cross-references",
        _anchor("UF-S3", "broken-internal-cross-references"),
        fix_hint=(
            "Declare the missing \\label{...} (for \\ref / \\eqref / \\pageref) "
            "or add the bib key to the .bib file (for \\cite)."
        ),
    ),
    "UF-S4": Rule(
        "UF-S4",
        REVIEW,
        PDF,
        "External URL liveness (deferred)",
        _anchor("UF-S4", "external-url-liveness-deferred"),
    ),
    "UF-S5": Rule(
        "UF-S5",
        REVIEW,
        PDF,
        "Hyperlink annotations clickable in PDF",
        _anchor("UF-S5", "hyperlink-annotations-clickable-in-pdf"),
    ),
    # Doc-class options (D)
    "UF-D1": Rule(
        "UF-D1",
        REVIEW,
        SOURCE,
        "`editMode` option not left on for submission",
        _anchor("UF-D1", "editmode-option-not-left-on-for-submission"),
        fix_hint="Remove `editMode` from the \\documentclass options before submitting.",
    ),
    "UF-D2": Rule(
        "UF-D2",
        MUST_FIX,
        SOURCE,
        "LuaLaTeX compiler directive",
        _anchor("UF-D2", "lualatex-compiler-directive"),
        fix_hint="Use `% !TEX program = lualatex` (or omit the directive) — UF requires LuaLaTeX.",
    ),
    "UF-D3": Rule(
        "UF-D3",
        REVIEW,
        SOURCE,
        "`overrideTitles` / `overrideChapters` options",
        _anchor("UF-D3", "overridetitles--overridechapters-options"),
        fix_hint=(
            "If you didn't need to, remove `overrideTitles` / `overrideChapters` "
            "from \\documentclass to silence the template's warning."
        ),
    ),
    # Presence (P)
    "UF-P1": Rule(
        "UF-P1",
        MUST_FIX,
        SOURCE,
        "`\\set*File` companions exist on disk",
        _anchor("UF-P1", "setfile-companions-exist-on-disk"),
        fix_hint="Create the named file next to the master .tex (or fix the macro argument).",
    ),
    # Journal-article (J)
    "UF-J1": Rule(
        "UF-J1",
        REVIEW,
        SOURCE,
        "Self-publication first-page footnote (when applicable)",
        _anchor("UF-J1", "self-publication-first-page-footnote-when-applicable"),
    ),
    "UF-J2": Rule(
        "UF-J2",
        REVIEW,
        SOURCE,
        "Co-author acknowledgment (when applicable)",
        _anchor("UF-J2", "co-author-acknowledgment-when-applicable"),
    ),
    # Accessibility (A)
    "UF-A1": Rule(
        "UF-A1", REVIEW, PDF, "PDF tagged structure", _anchor("UF-A1", "pdf-tagged-structure")
    ),
    "UF-A2": Rule(
        "UF-A2",
        REVIEW,
        PDF,
        "Known template accessibility limitations",
        _anchor("UF-A2", "known-template-accessibility-limitations"),
    ),
}


def rule_ids() -> list[str]:
    """Return all known UF-* rule identifiers in catalog order."""
    return list(RULES.keys())

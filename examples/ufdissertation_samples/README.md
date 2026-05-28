# UF Graduate School formatting samples

Reference snapshots downloaded from the UF Graduate School Thesis & Dissertation production page. Each file demonstrates how a single structural element of a dissertation is expected to be formatted.

These files exist as **authoritative tiebreakers** when the rule catalog in [`../../docs/uf-rules.md`](../../docs/uf-rules.md) leaves a formatting question ambiguous (e.g. block-quote indent depth, "short" vs "long" bulleted-list threshold, caption placement, equation numbering). When in doubt, open the matching sample.

## Provenance

- **Source:** [https://success.grad.ufl.edu/td/formatting/](https://success.grad.ufl.edu/td/formatting/)
- **Retrieved:** 2026-05-28
- **Origin format:** Microsoft Word (`.docx`) — these are the UF-supplied samples for the Word submission path, not the LaTeX path
- **Maintained by:** UF Graduate Editorial Office
- **License:** UF does not publish an explicit license for these samples; vendored here as a dated reference snapshot with provenance, consistent with educational fair use. The live UF page is the authoritative source; if a sample here disagrees with the live page, the live page wins.

## Status

**Reference only.** These files are **not** test fixtures. They are not wired into pytest and they do not represent compliance with the LaTeX template this tool targets (`\documentclass{ufdissertation}`). UF maintains separate Word and LaTeX templates with intentional formatting differences; visual equivalence between this directory and `../demo_dissertation/main.pdf` is approximate, not exact.

Treat each sample as an **upper bound on what UF accepts**, not a lower bound on what the LaTeX validator must produce. The validator's source of truth remains [`../../docs/uf-rules.md`](../../docs/uf-rules.md).

## Files

| Element | File |
|---|---|
| Title Page | `TDP-Title-Page.docx` |
| Copyright Page | `TDP-Copyright-Page.docx` |
| Abstract | `TDP-Abstract.docx` |
| Acknowledgments | `TDP-Acknowledgments.docx` |
| Biographical Sketch | `TDP-Biographical-Sketch.docx` |
| Table of Contents | `TDP-Table-of-Contents.docx` |
| List of Figures | `TDP-List-of-Figures.docx` |
| List of Tables | `TDP-List-of-Tables.docx` |
| Block Quote | `TDP-Block-Quote.docx` |
| Bulleted List (short) | `TDP-Short-Bulleted-List.docx` |
| Bulleted List (long) | `TDP-Long-Bulleted-List.docx` |
| Equation | `TDP-Equation.docx` |
| Figure | `TDP-Figure.docx` |
| Table | `TDP-Table.docx` |

## Optional: render to PDF for visual comparison

The samples are most useful when rendered to PDF and compared side-by-side with the corresponding section of `../demo_dissertation/main.pdf`. To regenerate PDFs locally:

    # macOS / Linux with LibreOffice installed:
    mkdir -p _pdf && \
      libreoffice --headless --convert-to pdf --outdir _pdf examples/ufdissertation_samples/*.docx

    # Alternative with pandoc + a LaTeX engine:
    cd examples/ufdissertation_samples && mkdir -p _pdf && \
      for f in *.docx; do pandoc "$f" -o "_pdf/${f%.docx}.pdf"; done

PDFs are intentionally **not committed** — they are derivable from the docx originals on demand, and a reference snapshot rendered locally with whatever tooling you have on hand is more useful than a stale committed PDF.

## Limitations

- Structural-element samples only. Whole-document concerns (chapter numbering across the body, ToC entry rendering, running heads, page-number reset at preliminary→body boundary) are not represented here. Consult `../demo_dissertation/` or `../../docs/uf-rules.md` for those.
- Word styling cannot be diffed against LaTeX source. The samples are a visual reference, not a source-layer comparator.
- UF may update the page (and the underlying files) without warning. The retrieval date above is when this snapshot was taken; if a sample disagrees with the live UF page, the live page wins.

## Why these files are in the repo

- **Reproducibility.** A reader who clones the repo at a future date sees the exact samples this project was designed against, even if UF updates or removes the page.
- **Rule-design audit trail.** When `docs/uf-rules.md` cites a sample as authority for a specific severity or wording choice, the cited artifact is right here.
- **Future PDF-layer fixtures.** Once the PDF-layer of the validator ships, rendered PDFs of these samples become candidate "known compliant" inputs for PDF-side tests.

If the directory ever needs to be slimmed, `TDP-Figure.docx` (~700 KB, embedded image) is the only large file; everything else is ~30 KB.

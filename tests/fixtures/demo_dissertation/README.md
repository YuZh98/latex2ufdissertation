# Demo dissertation — known-good fixture

This directory is a hand-crafted UF dissertation project that satisfies
every must-fix rule in `docs/uf-rules.md`. It serves two purposes:

1. **Regression fixture.** Running
   `latex2ufdissertation tests/fixtures/demo_dissertation/`
   must produce a clean report — zero must-fix findings, zero review
   findings. Any check that fires on this input is either wrong or the
   demo is wrong; both need fixing.

2. **Pedagogical reference.** Every file is annotated with comments
   pointing back to the specific UF rule it satisfies. New graduate
   students can read this project top-to-bottom to learn what a
   compliant dissertation looks like.

## File map

| File | Role | Rule citations |
|---|---|---|
| `main.tex` | Master file with metadata and `\set*File` macros | F13, F14, D1, D2, D3, F8, F10 |
| `abstractFile.tex` | 350-word-or-fewer abstract prose | F15 |
| `dedicationFile.tex` | Optional one-line dedication | F8 (conditional) |
| `acknowledgementsFile.tex` | Required acknowledgements prose | F8, S2 |
| `abbreviations.tex` | Optional List of Abbreviations as a description list | F8 (conditional) |
| `chapter1.tex` | Introduction chapter | F10, F11 |
| `chapter2.tex` | Main body with section, paired subsections, three figures (TikZ + pgfplots), three tables (simple, `threeparttable` with footnote, `longtable`), equation, lemma, theorem, algorithm pseudocode, block quote, and two `\addObject` calls | F10, F11, F16, F12 |
| `chapter3.tex` | Closing summary chapter | F10 |
| `appendix.tex` | Two appendices (A, B); demonstrates `\multipleAppendixtrue` | F8 (conditional) |
| `biographyFile.tex` | Required biographical sketch | F8, S2 |
| `referenceFile.bib` | Bibliography entries cited from the body | F8, S2, S3 |

## Sections exercised in the compiled PDF

The current compiled `main.pdf` is **26 pages** (LuaLaTeX, TeX Live
2025). In rendered order, with conditional sections marked (cond):

1. Title page (unnumbered, F8 #1)
2. Copyright page (auto-generated, F8 #2)
3. Dedication (cond, F8 #3)
4. Acknowledgements (F8 #4)
5. Table of Contents (auto, F8 #5)
6. List of Tables (cond, F8 #6) — driven by `\haveTablestrue`
7. List of Figures (cond, F8 #7) — driven by `\haveFigurestrue`
8. List of Objects (cond, F8 #8) — driven by `\haveObjectstrue`
9. List of Abbreviations (cond, F8 #9) — driven by `\setAbbreviationsFile`
10. Academic Abstract (F8 #10) — see word count note below
11. Chapter 1: Introduction (F8 #11, first of ≥3 per F10)
12. Chapter 2: Methods (F8 #11) — figures and tables follow the body
13. Chapter 3: Conclusion (F8 #11)
14. Appendix A: Supplementary Validator Rules (cond, F8 #12)
15. Appendix B: Sample Broken Inputs (cond, F8 #12)
16. Appendix C: Submission Checklist for the Student (cond, F8 #12)
17. List of References (F8 #13)
18. Biographical Sketch (F8 #14)

The abstract in `abstractFile.tex` is **297 words** (per the most recent
revision). UF-F15 caps the abstract at 350 words; the fixture stays
well under the cap. Future edits to the abstract should keep the count
≤ 350.

## LaTeX features demonstrated

- `\chapter`, `\section`, `\subsection` — three of the five heading tiers per F11 (`\subsubsection` and `\paragraph` are intentionally absent; see "What the demo intentionally does not do" below)
- Theorem environments (`\begin{theorem}`, `\begin{lemma}`) — defined by the class
- Equation w/ `\label` and `\ref`
- Figure environment w/ caption + `\label` and `\ref` (two figures)
- Table environment w/ caption + `\label` and `\ref`
- `\addObject{...}` — the class hijacks the algorithm environment to produce a List of Objects
- `\citep` / `\citet` — natbib-style citations (the `plainnat` style is loaded via `\setReferenceFile{bibname}{plainnat}`)
- `description` environment — abbreviations list
- `itemize` environment — single-spaced via class override
- `quote` environment — block quote inside chapter 2
- Multiple appendices via `\multipleAppendixtrue`

## A note on the meta abstract

The demo's abstract describes the validator tool itself rather than a
generic fictional research topic. This is intentional: the demo serves
both as a regression fixture and as a teaching aid, and a
self-referential abstract lets a student reading the demo learn what
the tool does at the same time they learn what a compliant abstract
looks like.

When the demo is used as a `--init --demo` scaffold for a new
dissertation, the student should replace the abstract with their own
research summary before submitting.

## What the demo intentionally does *not* do

- Does **not** include `editMode` in `\documentclass` (UF-D1). The
  bundled example template ships with `editMode` ON; the demo turns it
  off because submission requires it off.
- Does **not** override the template's defaults for margins, fonts,
  spacing, alignment, page numbering, or heading styles. The
  `ufdissertation` class handles all of those automatically.
- Does **not** use `\paragraph` (per UF-F11 — the template explicitly
  discourages it). Paragraph-level emphasis is done with `\textbf{...}`
  inline.

## Compiling locally

Requires LuaLaTeX with TeX Live 2025 (per UF-D2). From this directory:

```
lualatex main
bibtex main
lualatex main
lualatex main
```

### Why the cls and the PDF are bundled

A copy of `ufdissertation.cls` is included in this directory so the
fixture compiles standalone. The canonical class file lives at
`latex2ufdissertation/pipeline/template/ufdissertation.cls`; this copy
is derived from there and must be re-synced when the upstream class
changes. `ufdissertation.cls` is **not** authored by this project — it
is the UF Information Technology Help Desk's class file, redistributed
here for fixture-compilation purposes only. See the provenance header
at the top of the file. (A conftest fixture that copies the cls at
test time would be cleaner, but duplication is simpler today; this
arrangement is subject to revision if a copy-on-the-fly approach turns
out to be lower-maintenance.)

`main.pdf` is committed alongside the source so the PDF-layer checks
have a known-good fixture to validate against without requiring a TeX
installation on every CI machine. If CI grows to include a LuaLaTeX
step and on-the-fly compilation becomes cheap, the committed PDF can
be dropped in favor of generating it at test time.

**Note on TeX Live version.** If `main.pdf` is compiled on TeX Live
2024 or earlier, the output PDF will not be tagged for accessibility
(`Tagged: no` in `pdfinfo`). Real submissions must be compiled on TeX
Live 2025 for tagging to take effect. The validator's UF-A1 check
will surface a `review` finding on a 2024-compiled PDF.

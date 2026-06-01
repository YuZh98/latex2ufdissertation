# UF Dissertation Formatting Rules — Canonical Reference

Source: UF Graduate School Editorial Office (https://success.grad.ufl.edu/td/) + UF IT Help Desk (https://it.ufl.edu/helpdesk/graduate-resources/) + the LaTeX template (`ufdissertation.cls` v Fall 2025, fetched 2026-05-27 from UF IT). Cross-referenced against `exampleMasterFile.tex` + `chapter1.tex` of the bundled template.

> **Citations are pinned to a snapshot.** Every `C1:NNN` reference below points to specific line numbers in the Fall 2025 release of `ufdissertation.cls` as published by UF, located in this repo at `latex2ufdissertation/pipeline/template/ufdissertation.cls` (the canonical 1083-line copy). Do **not** cite line numbers against `examples/demo_dissertation/ufdissertation.cls` — that copy carries a 22-line provenance header prepended by this project, so its line numbers are offset by +22 from the canonical.
>
> **When UF publishes a new cls, every citation may shift.** Maintainer obligation on cls re-sync: open each `C1:NNN` citation in this file and confirm the cited line range still contains the construct described. Cited construct moved? Update the number. Cited construct removed or refactored? Update the rule.

This document is the authoritative rule set the validator checks against. Every rule has:

- Stable ID
- Citation back to UF source (web doc and/or cls line range)
- Severity (`must-fix` / `review`)
- Detection strategy keyed to: **template-enforced** (cls handles it, student can only break by override), **presence** (student must provide), **content** (student writes text the tool inspects), or **pdf-rendered** (only the compiled output can confirm)
- Validation layer (source / pdf / both / skip)

Severity tiers:

- **must-fix** — Documented UF rule. Violations cause submission rejection.
- **review** — Likely issue. Requires human judgment; tool flags, student decides.

---

## Contents

- [Part 0 — What the template enforces vs what the student can break](#part-0--what-the-template-enforces-vs-what-the-student-can-break)
- [Sources](#sources)
- [Formatting rules (UF-F1 … UF-F16)](#formatting-rules)
- [Submission + structural rules (UF-S1 … UF-S5)](#submission--structural-rules)
- [Document-class option hygiene (UF-D1 … UF-D3)](#document-class-option-hygiene)
- [Required file presence + macro argument hygiene (UF-P1)](#required-file-presence--macro-argument-hygiene)
- [Journal-article dissertation rules (UF-J1 … UF-J2)](#journal-article-dissertation-rules)
- [Accessibility (UF-A1 … UF-A2)](#accessibility)
- [Layer + strategy summary](#layer--strategy-summary) — one-line table of every rule

### Rule shape

Every rule entry uses the same five-field shape, so you can skim down the page:

- **Severity** — `must-fix` or `review`
- **Source** — UF web doc and/or cls line range
- **Layer** — `source`, `pdf`, or both
- **Strategy** — what the validator does to detect a violation
- **Note** *(optional)* — exceptions, allowlists, or caveats

---

## Part 0 — What the template enforces vs what the student can break

The UF LaTeX template (`ufdissertation.cls`) does heavy lifting. Most formatting rules are enforced by construction. This changes the validator's job from "is the output compliant?" to "did the student override the template's correct defaults?"

| Rule area | Cls handles it? | Student-breaking pattern | Default check strategy |
|---|---|---|---|
| Margins (1") | yes (cls:153) | `\newgeometry`, second `\geometry`, removing class | source override scan |
| Font family | yes (cls:167-169) | `\setmainfont`, `\renewcommand\familydefault`, extra font pkgs | source override scan |
| Font size (12pt) | yes (`\LoadClass[12pt]{report}`, cls:1) | `\fontsize`, `\Large`, `\small` outside allowed contexts | source override scan |
| Line spacing | yes (cls:198 + exceptions cls:58, 199, 201, 774, 982) | `\singlespacing` / `\onehalfspacing` / `\setstretch` outside allowed contexts | source override scan |
| Alignment (ragged-right) | yes (cls:171) | `\justifying` | source override scan |
| Paragraph indent (1cm) | yes (cls:203, 1010) | global `\setlength{\parindent}{0pt}`, excessive `\noindent` | source override scan |
| Page numbering (arabic, bottom-center) | yes (cls:180-188) | `\pagenumbering{roman}`, custom `\fancyfoot` | source override scan |
| Page order (14 sections) | yes (cls:666-1004) | overriding `\AtBeginDocument` (rare) | presence check on `\set*File` macros |
| Title page | yes (cls:280-296 `\maketitle`) | bypassing `\maketitle` | presence check on `\title`, `\author`, etc. |
| Copyright page | yes (cls:675-681) | bypassing template body insert | presence check on `\degreeYear`, `\author` |
| Heading styles (5 tiers) | yes (cls:304-362, 797-806) | manual `\titleformat`, `\textbf{\Large ...}` patterns | source override scan |
| Auto-capitalization (chapters, title) | yes (cls:279, 309-313) | `overrideTitles` / `overrideChapters` options | class option scan |
| Hyperlink colors | yes (cls:42-48) | hyperref override | source override scan |
| Internal `\ref`/`\cite` resolution | partial — cls enables hyperref; broken refs surface as `??` | typo, deletion | source-level resolver |
| Bibliography style | template-driven (cls:980-983) | wrong `.bst` file in `\setReferenceFile{}{style}` | content check |
| Content of each section file | no — student writes | empty file, missing required content | content check |

**Implication:** most must-fix rules collapse to **source override scans + presence checks**. PDF-layer is needed only for:

- Verifying the rendered output actually matches expectations (defense in depth)
- Catching cases where the student bypassed the template entirely (e.g. wrong `\documentclass`)
- Things the template can't enforce in source (blank gaps, accessibility tagging, abstract word count in rendered output)

---

## Sources

| ID | URL | What it covers |
|---|---|---|
| S1 | https://success.grad.ufl.edu/td/formatting/ | Formatting rules — primary spec |
| S2 | https://success.grad.ufl.edu/td/submission/ | Submission flow + required documents |
| S3 | https://success.grad.ufl.edu/td/faq/ | FAQ — rejection reasons, journal-article handling |
| S4 | https://it.ufl.edu/helpdesk/graduate-resources/ms-word--latex-templates/ | Template downloads + LuaLaTeX/TeX Live 2025 requirement |
| S5 | https://www.overleaf.com/blog/accessible-pdfs-with-latex | Accessibility framing |
| C1 | `latex2ufdissertation/pipeline/template/ufdissertation.cls` Fall 2025, fetched from S4 | Class file source of truth |
| C2 | `latex2ufdissertation/pipeline/template/exampleMasterFile.tex` | Reference student-facing entry point |
| C3 | `latex2ufdissertation/pipeline/template/abstractFile.tex` | Source of 350-word abstract cap |
| C4 | `latex2ufdissertation/pipeline/template/chapter1.tex` | Source of heading rules, sub-section pairing rule |

---

## Formatting rules

### UF-F1 — Margins

- **Severity:** must-fix
- **Source:** S1 (*"One inch (1") all around"*) + C1:153-157
- **Layer:** source primary, pdf backup
- **Strategy:** template-enforced (1.0in via `geometry`). Source: scan for override patterns:
  - `\newgeometry`, additional `\geometry{...}` calls
  - `\usepackage[...]{geometry}` with non-1in values overriding the class
  - `\hoffset`, `\voffset`, `\textwidth`, `\textheight` direct sets
- **PDF backup:** sample ≥10 pages, compute text bbox vs page box, flag any margin < 1.0in (catches cases where source bypassed template)

### UF-F2 — Font family

- **Severity:** must-fix
- **Source:** S1 (*"Times New Roman or Arial"*) + C1:167-169
- **Layer:** source primary, pdf backup
- **Strategy:** template-enforced (Times default; Arial via `\renewcommand{\familydefault}{\sfdefault}`). Source: scan for override patterns:
  - `\setmainfont{...}` (fontspec override)
  - Additional font packages: `mathpazo`, `mathptmx`, `libertine`, etc.
  - Manual `\fontfamily{...}\selectfont`
- **PDF backup (authoritative):** per-page **body-mode** font — the most-common glyph font on each page (subset prefix `^[A-Z]{6}\+` stripped), *not* a document-wide font list. Math (`NewTXMI`, `txsys`, `txexs`) and monospace (`LMMono`) are legitimate template fonts and must not be flagged; the body-mode excludes them because body text dominates by glyph count. Flag a page whose body-mode font is outside the Times/Termes/Arial/Helvetica family. Verified: `\fontfamily{ppl}\selectfont` renders the body as `LMRoman` (non-Times); `\usepackage{mathpazo}` does **not** change the body-mode (newtx wins).
- **Layer authority** (per [`spec-v1.0.md`](./spec-v1.0.md) §7.1.2): the source override-scan flags *intent* and over-fires on overrides the template neutralizes (the "mirage" — `newtx` reloads at `\begin{document}`, so the body still renders Times). Source therefore fires as `review`; the PDF layer holds the `must-fix` verdict. Registry severity stays `must-fix` (the source emit site passes a per-call `review` override), preserving catalog↔registry parity.

### UF-F3 — Font size 12pt

- **Severity:** must-fix
- **Source:** S1 (*"12-point ... throughout"*) + C1:1 `\LoadClass[12pt]{report}`
- **Layer:** source primary, pdf backup
- **Strategy:** template-enforced via `\LoadClass[12pt]`. Source: scan for size override patterns inappropriate to context:
  - `\fontsize{...}{...}\selectfont` in body
  - `\tiny`, `\scriptsize`, `\footnotesize`, `\small`, `\large`, `\Large`, `\LARGE`, `\huge`, `\Huge` in body text
  - Allowed contexts: captions, headings (template-handled — flag only direct user override)
- **PDF backup:** per-page **body-mode** size; flag a page whose body-mode size ≠ 12 pt (tolerance ±0.5 pt). This is the authoritative check: the source scan over-fires on *localized-legal* sizing (a one-off `\fontsize` on a title/caption — issue #47), whereas body-mode ignores non-body runs. Verified: `\fontsize{20}{24}\selectfont` moves the body-mode to ~20 pt; legitimate captions/headings do not. Source therefore fires as `review`; PDF holds the `must-fix` verdict.

### UF-F4 — Line spacing

- **Severity:** must-fix
- **Source:** S1 (*"Double-space paragraph text; single-space headings, table titles, figure captions; refs single-spaced with blank line between"*) + C1:198 (`\doublespacing`) + exceptions at C1:58 (captions), C1:199 (longtable), C1:201 (itemize), C1:774 (abstract block), C1:982 (bibliography)
- **Layer:** source primary, pdf backup
- **Strategy:** template-enforced. Source: scan for override patterns:
  - `\singlespacing`, `\onehalfspacing`, `\setstretch{...}` outside allowed scopes (within `longtable`, `itemize`, caption, abstract, bib — fine)
  - `\renewcommand{\baselinestretch}{...}`
- **PDF backup:** measure the **gap/font-size ratio** per page (≈2.0 double-spaced, ≈1.2 single), *not* the absolute line gap — verified this conflates spacing with font size (`\singlespacing`+`\fontsize{20}{24}` still measures ~24 pt absolute gap because `\fontsize` resets `\baselineskip`). Exclude the legitimately single-spaced bibliography page-range, identified via the `/Names/Dests` `REFERENCES` destination (degrade to page-global if hyperref destinations are absent, e.g. under `\hypersetup{draft}`).

### UF-F5 — Text alignment (ragged-right)

- **Severity:** must-fix
- **Source:** S1 (*"Left-aligned text with ragged right-hand margin — do not justify text"*) + C1:171 `\raggedright`
- **Layer:** source primary
- **Strategy:** template-enforced globally. Source: scan for override patterns:
  - `\justifying`, `\justify`
  - `ragged2e` package w/ overrides
  - `\begin{flushleft}`/`\end{flushleft}` mass usage (acceptable in local contexts)
- **Caveat (verified):** `\justifying` is **undefined** in this template (it loads raw `\raggedright`, not `ragged2e`) — a doc using bare `\justifying` fails to compile (exit 2), so it never reaches an F5 finding. The realistic re-justification vector is `\setlength{\rightskip}{0pt}`, which the command scan above does **not** catch. The sound check is therefore at the PDF layer: measure the **right-edge distribution** (ragged = high variance; justified = a dominant identical right edge plus a few short last lines). The source scan is best-effort for the `\usepackage{ragged2e}\justifying` path only.
- **Note:** Default `report` class justifies. Template's `\raggedright` is what makes ragged-right the actual behavior. Without it, output would justify. So this rule is real.
- **Not-an-override allowlist:** `\sloppy` (and the equivalent `sloppypar` environment) loosens LaTeX's line-breaking criteria to reduce overfull-hbox warnings but does **not** justify text. The bundled UF example file uses `\sloppy` on the same line as `\documentclass`, in the form `\documentclass[editMode]{ufdissertation}\sloppy`. The validator's F5 override scan must allowlist `\sloppy` regardless of position — on its own line, on the same line as `\documentclass`, or anywhere else in the preamble or body.

### UF-F6 — Page numbering (arabic, bottom-center)

- **Severity:** must-fix
- **Source:** S1 (*"Arabic numbers ... centered at bottom"*) + C1:179-188
- **Layer:** source primary, pdf backup
- **Strategy:** template-enforced. Source: scan for override patterns:
  - `\pagenumbering{roman}`, `\pagenumbering{Roman}`, `\pagenumbering{alph}`, etc.
  - `\renewcommand{\thepage}{...}`
  - Custom `\fancyfoot` / `\fancyhead` / `\cfoot` redefinitions
- **PDF backup — not viable / moot (verified):** the demo has **no `/PageLabels`** (the original PDF-backup plan is infeasible), and the template numbers **arabic throughout** (cls:177; demo front matter is "2".."11", no roman region), so there is no front-matter/body numbering boundary for the PDF to police. The source scan already catches `\pagenumbering{roman}`/`\renewcommand{\thepage}`. PDF-F6 adds essentially nothing and is not planned.
- **Note:** Title page unnumbered by template (`\thispagestyle{empty}` cls:282) — accept as exception.

### UF-F7 — Paragraph indentation

- **Severity:** must-fix
- **Source:** S1 (*"Indent the first line of each paragraph"*) + C1:203 (`\indentfirst`) + C1:1010 (`\parindent=1cm`)
- **Layer:** source primary
- **Strategy:** template-enforced. Source: scan for override patterns:
  - `\setlength{\parindent}{0pt}` globally
  - `\parindent=0pt` globally
  - Removing `indentfirst` package usage (unlikely)

### UF-F8 — Required page order + presence

- **Severity:** must-fix
- **Source:** S1 (14-section list) + C1:666-1004 (auto-insertion order)
- **Layer:** source primary
- **Strategy:** template enforces order. Source: presence check on `\set*File` macros required for each conditional + unconditional section. Title-page metadata macros are owned by UF-F14, not F8 — F8 covers section files and `\have*true` flags only.
- **Required (unconditional):**
  - Title page → see UF-F14 (title-page metadata macros: `\title`, `\author`, `\degreeType`, `\thesisType`, `\degreeYear`, `\degreeMonth`, `\major`, `\chair`)
  - Copyright page → auto-generated (no student input)
  - Acknowledgements → `\setAcknowledgementsFile{name}` + file exists
  - Table of Contents → auto (no student input)
  - Academic abstract → `\setAbstractFile{name}` + file exists
  - Chapters → `\include`/`\input` calls (≥3 per F10)
  - List of References → `\setReferenceFile{bibname}{bststyle}` + `.bib` file exists
  - Biographical Sketch → `\setBiographicalFile{name}` + file exists
- **Conditional (must be set if document has the section):**
  - Dedication → `\setDedicationFile{name}`
  - List of Tables → `\haveTablestrue` (cls:136)
  - List of Figures → `\haveFigurestrue` (cls:140)
  - List of Objects → `\haveObjectstrue` (cls:144)
  - List of Abbreviations → `\setAbbreviationsFile{name}`
  - Appendices → `\setAppendixFile{name}` (+ `\multipleAppendixtrue` if >1)

### UF-F9 — Singleton structure

- **Severity:** must-fix
- **Source:** S1 (*"only **one** abstract, table of contents, and reference list"*)
- **Layer:** source primary
- **Strategy:** template ensures single instances of each. Source: scan for student-added duplicates:
  - Multiple `\setAbstractFile` calls
  - Multiple `\tableofcontents`
  - Multiple `\bibliography` / `\setReferenceFile`
  - Manual `\chapter{ABSTRACT}` / `\chapter{REFERENCES}` outside template

### UF-F10 — Chapter scaffold

- **Severity:** must-fix
- **Source:** S1 (*"introductory chapter, main body, closing summary chapter"*) + S3 (*"Minimum: 3 chapters required"*)
- **Layer:** source
- **Strategy:** count `\chapter{...}` calls + `\include` calls resolving to chapter-bearing files. Require ≥3.
- **Note:** Can't auto-detect "introductory" vs "summary" role. Flag chapter 1 title + last chapter title for student review.

### UF-F11 — Heading styles (5-tier hierarchy)

- **Severity:** must-fix
- **Source:** S1 (5 explicit tiers) + C1:304-362, 797-806
- **Layer:** source
- **Strategy:** template enforces by construction via `titlesec`. Source: scan for override/bypass patterns:
  - `\titleformat{\chapter}`, `\titleformat{\section}`, etc. redefining template
  - `\paragraph` usage — discouraged per C4 ("Do not use the Paragraph heading feature in LaTeX")
  - Manual heading impersonation: `\textbf{\Large ...}` / `\textbf{\centering ...}` patterns at section breaks
- **Note:** Direct usage of `\section`, `\subsection`, `\subsubsection` is template-conformant — these are the **happy path**, not violations.

### UF-F12 — Text flow within chapter (no blank gaps)

- **Severity:** review
- **Source:** S1 (*"It's best to place all tables and figures at the end of their chapter"*, *"avoid inserting them into the chapter's text unless you can do so without leaving blank gaps"*)
- **Layer:** pdf only
- **Strategy:** detect large vertical whitespace blocks within chapter body (>2x normal leading) via PDF bbox analysis. Flag location + page.
- **Note:** Wording is "best to" → review, not must-fix.

### UF-F13 — Document class is `ufdissertation`

- **Severity:** must-fix
- **Source:** S1 (*"templates ... you must use"*) + S4 (Fall 2025 template required)
- **Layer:** source
- **Strategy:** scan main `.tex` for `\documentclass[opts]{ufdissertation}`. If different class → must-fix.

### UF-F14 — Required metadata macros set

- **Severity:** must-fix
- **Source:** S1 (UF Grad School policy: title, abstract, and copyright pages are required prefatory matter) backed by C1:280-296 (title page), C1:756-792 (abstract page), C1:675-681 (copyright page) — the cls renders these pages from the metadata macros below, so missing any macro means the required page cannot render and the submission cannot be accepted.
- **Layer:** source
- **Strategy:** scan for presence + non-empty arguments of:
  - `\title{...}` — required for title + abstract pages
  - `\author{...}` — required for title + copyright + abstract pages
  - `\degreeType{...}` — required for title + abstract pages
  - `\thesisType{...}` — required for title page; must be "Dissertation" for v1.0 scope (not "Thesis")
  - `\degreeYear{...}` — required for title + abstract + copyright pages
  - `\degreeMonth{...}` — required for abstract page (May, August, or December per C2:41)
  - `\major{...}` — required for abstract page
  - `\chair{...}` — required for abstract page
- **Note:** `\thesisType{Thesis}` triggers v1.0 out-of-scope refusal — separate from F14.

### UF-F15 — Abstract word count ≤ 350

- **Severity:** must-fix
- **Source:** C3 (abstractFile.tex literal text: *"It should be 350 words or less"*)
- **Layer:** source content check, pdf backup
- **Strategy:** locate file referenced by `\setAbstractFile{name}`, strip LaTeX commands, count words. Flag if > 350.
- **PDF backup:** extract abstract page text via PDF parser, count words.
- **Note:** Threshold from template's own abstract file, not from UF web docs. Verify w/ help desk before final lock.

### UF-F16 — Subsection pairing

- **Severity:** review
- **Source:** C4 (chapter1.tex literal text: *"If you divide a section, you must divide it into two, or more, parts"*) — UF template instruction
- **Layer:** source
- **Strategy:** parse chapter structure; flag any `\section` containing exactly one `\subsection`, or `\subsection` with exactly one `\subsubsection`.
- **Note:** Review not must-fix — orphan subsection is style, not formal rejection per UF web docs.

---

## Submission + structural rules

### UF-S1 — PDF output present

- **Severity:** must-fix
- **Source:** S2 (*"Your dissertation must be submitted in PDF format"*)
- **Layer:** pdf
- **Strategy:** if input mode is zip/dir without PDF and no compile step succeeded → must-fix. If pdf input mode → trivially satisfied.
- **Note (verified):** on the source/compile path this is near-tautological — a failed compile is already exit 2 (`build.py`) *before* the PDF layer runs, so S1 cannot fire there. Its only non-trivial niche is a present-but-empty/0-page PDF (narrow the check to "parses + ≥1 page"); a fully unparseable input PDF is exit-2 unreadable-input, not an S1 finding.

### UF-S2 — Required sections present (rejection-driver subset of F8)

- **Severity:** must-fix
- **Source:** S3 — common rejection reasons include *"absent sections (Acknowledgments, Abstract, References, Biographical Sketch)"*
- **Layer:** source primary
- **Strategy:** subset of UF-F8 with elevated detection priority. These four are the most-rejected omissions.
- **Note:** Implementation-wise, F8 already covers them — S2 is a marketing-friendly grouping in the report output, not a separate code path.

### UF-S3 — Broken internal cross-references

- **Severity:** must-fix
- **Source:** S3 (*"non-functional hyperlinks"* listed as rejection reason)
- **Layer:** source
- **Strategy:** parse all `\ref{key}`, `\eqref{key}`, `\pageref{key}`, `\cite{key}` calls. Cross-reference against:
  - `\label{key}` declarations across all source files
  - `.bib` entries (keys) for `\cite{}`
- Flag unresolved keys.

### UF-S4 — External URL liveness (deferred)

- **Severity:** review (when implemented)
- **Source:** S3 (*"non-functional hyperlinks"* — possible interpretation)
- **Layer:** pdf, network-dependent
- **Strategy:** deferred to v1.1, gated behind `--check-links` flag. Out of v1.0 scope per offline-purity principle.

### UF-S5 — Hyperlink annotations clickable in PDF

- **Severity:** review
- **Source:** S3 implied
- **Layer:** pdf
- **Strategy:** extract `/Annots` from PDF; verify presence + correct `/URI` or `/Dest` per `\href` and `\ref` in source. Template (cls:42-48) sets `colorlinks=true` which produces annotations by default — failure here = template was broken upstream.

---

## Document-class option hygiene

### UF-D1 — `editMode` option not left on for submission

- **Severity:** review
- **Source:** C1:1041-1045 + C2:1 (example ships with `editMode` on)
- **Layer:** source
- **Strategy:** scan `\documentclass` options for `editMode`. If present → review (likely forgot to remove for submission).
- **Note:** Example template ships w/ `editMode` enabled (C2:1) — meaning a student following the example must remember to remove it. Real risk. Help desk likely catches + asks resubmit rather than formally rejecting, so review not must-fix.

### UF-D2 — LuaLaTeX compiler directive

- **Severity:** must-fix
- **Source:** S4 (*"LuaLaTeX with TexLive 2025 (required for accessibility)"*)
- **Layer:** source
- **Strategy:** scan main `.tex` for `% !TEX program = ...` directives. Flag if non-LuaLaTeX (pdflatex / xelatex / latex). Absence = OK (default LuaLaTeX assumed).
- **PDF backup (planned):** read the PDF `/Producer` engine name — a determinism-safe, stable field (unlike `/CreationDate`/`/ID`). Canonical LuaLaTeX stamps `LuaTeX-…`; pdfTeX stamps `pdfTeX`; `xdvipdfmx` is ambiguous (XeLaTeX or LuaLaTeX-via-dvi). The `% !TEX` hint is *not* the compiler — a project silently built with pdflatex passes the source check; `/Producer` confirms the *actual* engine. This is a backup, not a replacement: it reliably catches `pdfTeX` but cannot positively confirm "LuaLaTeX-direct" when the value is `xdvipdfmx`.

### UF-D3 — `overrideTitles` / `overrideChapters` options

- **Severity:** review
- **Source:** C1:1018-1037 (template warns on use)
- **Layer:** source
- **Strategy:** scan `\documentclass` options; if either present → review w/ template's warning text: *"If you didn't need to, remove ... to fix this."*

---

## Required file presence + macro argument hygiene

### UF-P1 — `\set*File` companions exist on disk

- **Severity:** must-fix
- **Source:** C1:542-596 — each `\set*File` macro saves a filename; template `\input{...}` calls it
- **Layer:** source
- **Strategy:** for each of the 8 `\set*File` macros defined by the class (C1:540-596) — `\setCopyrightFile`, `\setDedicationFile`, `\setAcknowledgementsFile`, `\setAbbreviationsFile`, `\setAbstractFile`, `\setAppendixFile`, `\setReferenceFile`, `\setBiographicalFile` — when present in source, verify the companion `name.tex` (or `name.<ext>`) exists in project. For `\setReferenceFile{bibname}{style}`, verify `bibname.bib` exists. P1 applies to any of the 8 present; the required/optional distinction is UF-F8's concern (only the four required macros fire F8 "not set" when absent — see § UF-F8).
- **v0.1 status:** this was E3–E9. Fix `_setfile_arg` regex to handle two-arg `\setReferenceFile{bibname}{style}` correctly without producing `bibname.bib.bib` lookup.

---

## Journal-article dissertation rules

### UF-J1 — Self-publication first-page footnote (when applicable)

- **Severity:** review
- **Source:** S3 (*"Cite on first page in unnumbered footnote with full citation"*)
- **Layer:** source content check
- **Strategy:** detect `\footnotetext[0]{...}` pattern at chapter start (the pattern C4:4 demonstrates). If chapter contains this pattern → presence confirmed. If document looks like a multi-article dissertation (multiple chapters with `\footnotetext[0]` patterns) but missing on one → flag for review.
- **Note:** Can't auto-detect "is this chapter from a published article" w/o student annotation. Surface this as a checklist item in `--guide` mode rather than auto-checking.

### UF-J2 — Co-author acknowledgment (when applicable)

- **Severity:** review (manual checklist only)
- **Source:** S3 (*"please make sure to acknowledge any work that your co-authors have done"*)
- **Layer:** content check, low-confidence
- **Strategy:** if multiple `\footnotetext[0]` patterns detected (suggesting journal-article mode), surface a checklist item: "verify co-authors acknowledged in Acknowledgments section." No auto-detect.

**Dropped from prior draft:**
- ~~J1 single abstract/ToC/refs across articles~~ → redundant with F9; dropped
- ~~J2 separate intro+conclusion chapters in article mode~~ → no discriminator for article mode; coverage achieved by F10 (≥3 chapters); dropped

---

## Accessibility

### UF-A1 — PDF tagged structure

- **Severity:** review
- **Source:** S5 (PDF/UA-1, PDF/UA-2, WCAG 2.1/2.2 AA) + S4 (*"required for accessibility"* — template uses LuaLaTeX + TeX Live 2025 for tagging)
- **Layer:** pdf
- **Strategy — corrected (verified):** the original premise is wrong. A **canonical** LuaLaTeX + TeX Live 2025 build of this template produces an **untagged** PDF (no `/StructTreeRoot`, `/MarkInfo`, or `/Lang` — confirmed on the demo). Missing tags are the template's *normal* output, **not** a sign of the wrong compiler. Enforcing A1 (even as `review`) would therefore fire on every conforming dissertation and break acceptance gate §8.2. A1 is consequently **not a per-run finding**; the untagged-output fact is surfaced as standing informational text under UF-A2 (per [`spec-v1.0.md`](./spec-v1.0.md) §6). Accessibility tagging is unverifiable on this template by construction.

### UF-A2 — Known template accessibility limitations

- **Severity:** review (informational)
- **Source:** S4 — known limitations: figure captions, numbered equations, table header declarations, page headers/footers, PDF metadata
- **Layer:** pdf
- **Strategy:** surface as informational note in report — these are known template caveats, not student fault.

---

## Layer + strategy summary

| Rule | Severity | Layer | Strategy |
|---|---|---|---|
| F1 margins | must-fix | source+pdf | template-enforced override scan |
| F2 font family | must-fix | source+pdf | template-enforced override scan |
| F3 font size | must-fix | source | template-enforced override scan |
| F4 line spacing | must-fix | source+pdf | template-enforced override scan |
| F5 alignment | must-fix | source | template-enforced override scan |
| F6 page numbering | must-fix | source+pdf | template-enforced override scan |
| F7 paragraph indent | must-fix | source | template-enforced override scan |
| F8 page order + presence | must-fix | source | presence check on `\set*File` + macros |
| F9 singleton structure | must-fix | source | duplicate `\set*File` / `\chapter` scan |
| F10 ≥3 chapters | must-fix | source | count `\chapter` / `\include` |
| F11 heading styles | must-fix | source | override scan + `\paragraph` flag |
| F12 blank gaps | review | pdf | vertical-whitespace detection |
| F13 documentclass | must-fix | source | `\documentclass` parse |
| F14 metadata macros | must-fix | source | presence check |
| F15 abstract ≤ 350 words | must-fix | source+pdf | word count |
| F16 subsection pairing | review | source | structural parse |
| S1 PDF present | must-fix | pdf | trivial |
| S2 rejection-driver sections | must-fix | source | F8 subset (report grouping) |
| S3 broken internal refs | must-fix | source | label/cite resolver |
| S4 external URL liveness | review (v1.1) | pdf + network | deferred |
| S5 hyperlink annotations | review | pdf | `/Annots` parse |
| D1 editMode left on | review | source | `\documentclass` option scan |
| D2 LuaLaTeX directive | must-fix | source | `% !TEX program` scan |
| D3 overrideTitles/Chapters | review | source | `\documentclass` option scan |
| P1 setFile companions exist | must-fix | source | filesystem check |
| J1 self-pub footnote | review (checklist) | content | `\footnotetext[0]` pattern |
| J2 co-author ack | review (checklist) | content | manual checklist if article mode signaled |
| A1 PDF tagged | review | pdf | `/StructTreeRoot` parse |
| A2 template caveats | review | pdf | informational surfacing |

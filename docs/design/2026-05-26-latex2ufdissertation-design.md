# latex2ufdissertation — v0.1 design

**Status:** Accepted
**Date:** 2026-05-26
**Scope:** Initial release (v0.1) of the latex2ufdissertation CLI.

## Goal

One command produces a UF Graduate School-compliant compiled PDF for dissertation or thesis submission, validating the project against the published format rules before submission time.

## Non-goals (v0.1)

- Cleanup of `\todo`, comments, draft packages (PDF submission carries no source artifacts).
- PDF-level checks (font embedding, margin probe, abstract word count via text extraction).
- Accessibility coverage (alt-text scanning, table-header configuration verification).
- MCP server, VS Code extension, GitHub Action, pre-commit hook surfaces.
- Auto-fixing of source errors.
- Sharing code with `latex2arxiv` via a published library. Reuse is by copy-and-adapt.

## Inputs and outputs

- **Inputs accepted:** `.zip`, project directory, or git URL (https or ssh). Mirrors latex2arxiv.
- **Default output name:** `<stem>_ufdissertation.pdf`.
- **Default output location:**
  - Directory input → PDF lands inside the input directory.
  - Zip input → PDF lands in the zip's parent directory.
  - Git URL → PDF lands in the current working directory, stem derived from repo name.
  - Explicit positional `OUT.pdf` → exactly that path.

## CLI surface

```
latex2ufdissertation INPUT [OUTPUT.pdf] [options]
```

| Flag | Behavior |
|---|---|
| (no flag) | Validate + compile → emit PDF |
| `--init DIR` | Scaffold a new project at DIR (mutually exclusive with INPUT) |
| `--dry-run` | Validate only, skip compile |
| `--main FILENAME` | Override auto-detect of master `.tex` |
| `--json` | Machine-readable summary on stdout; progress on stderr |
| `--version` | Print version and exit |

Compile is mandatory on the default path because the PDF is the deliverable.

## Exit codes

- `0` — no errors (warnings allowed).
- `1` — validation error or compile failure.
- `2` — bad input (missing path, not a zip / dir / git URL).
- `3` — LuaLaTeX not installed.

## Architecture

```
latex2ufdissertation/
├── converter.py             # CLI entry, argparse, orchestration
├── pipeline/
│   ├── __init__.py
│   ├── types.py             # Issues collector (copied from latex2arxiv)
│   ├── resolve.py           # input → root directory (zip / dir / git URL)
│   ├── main_tex.py          # auto-detect master via \documentclass{ufdissertation}
│   ├── checks.py            # all source-level + class-config checks
│   ├── init.py              # --init: fetch UF IT site, bundled fallback
│   ├── build.py             # LuaLaTeX driver + error parsing
│   └── template/            # bundled UF template (--init fallback)
├── tests/
│   └── fixtures/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
└── LICENSE                  # MIT
```

### What is copied from latex2arxiv (with light adaptation)

- `Issues` collector (`pipeline/types.py`).
- Compile-error formatter (`!` + `l.NN` block parsing) → into `pipeline/build.py`.
- Main-tex auto-detection logic → into `pipeline/main_tex.py`.
- `argparse` skeleton, `--json` schema and `--version` plumbing → into `converter.py`.
- pytest fixture/baseline conventions → `tests/`.

### What is new

- `pipeline/init.py` — `urllib.request` fetch with timeout, bundled fallback.
- `pipeline/checks.py` — UF class-command and class-option checks.
- LuaLaTeX driver in `pipeline/build.py` (replaces pdflatex driver).
- Input resolution returns a directory only (no zip-output plumbing).

### Dependencies

- Runtime: Python stdlib only. No `requests`, no `PyYAML`.
- Dev: `pytest`, `ruff`. Matches latex2arxiv toolchain.

## Data flow

### Default path

```
INPUT (.zip | dir | git URL)
   │
   ▼
resolve.resolve()          → root: Path
   │
   ▼
main_tex.detect()          → master.tex
   │
   ▼
checks.run()               → Issues (errors + warns)
   │
   ▼
if --dry-run:
    print summary; exit(0 or 1)
else:
    build.compile()        → PDF (or None on failure)
    emit PDF at <stem>_ufdissertation.pdf
    print combined summary
    open PDF (best-effort)
    exit(0 or 1)
```

### `--init DIR` path

```
fetch UF IT template URL (timeout 30s)
   ├── on success: extract zip into DIR
   └── on any failure (network, 404, bad zip):
          warn "couldn't reach UF IT site; using bundled template"
          copy pipeline/template/ → DIR
print scaffold-ready message
exit(0)
```

## Validation checks (v0.1)

All checks run against the resolved master `.tex` and the project root. No PDF inspection.

### `[error]` — block submission

| # | Trigger | Message |
|---|---|---|
| E1 | `\documentclass{...}` is not `ufdissertation` or missing | `wrong document class — UF requires \documentclass{ufdissertation}` |
| E2 | `\title{...}` missing or empty | `\title is required` |
| E3 | `\author{...}` missing or empty | `\author is required` |
| E4 | `\degreeType{...}` missing | `\degreeType is required (e.g. "Doctor of Philosophy")` |
| E5 | `\thesisType{...}` missing | `\thesisType is required (Dissertation or Thesis)` |
| E6 | `\setAcknowledgementsFile{X}` missing OR `X.tex` not found at project root | `Acknowledgements file required` |
| E7 | `\setAbstractFile{X}` missing OR `X.tex` not found | `Abstract file required` |
| E8 | `\setReferenceFile{X}{style}` missing OR `X.bib` not found | `Reference file required` |
| E9 | `\setBiographicalFile{X}` missing OR `X.tex` not found | `Biographical sketch required` |

### `[warn]` — advisory

| # | Trigger | Message |
|---|---|---|
| W1 | `\documentclass[...editMode...]{ufdissertation}` | `editMode option set — remove before final submission` |
| W2 | Non-LuaLaTeX compiler hint detected (Makefile, `% !TEX program =`, or similar) | `UF requires LuaLaTeX — pdflatex/xelatex hint detected` |

### Deferred to v0.2+

- `\major`, `\chair` required (treat as warn-only in v0.1).
- `\degreeMonth` ∈ {May, August, December}.
- `\degreeYear` four-digit plausibility.
- `\haveTablestrue` / `\haveFigurestrue` / `\haveObjectstrue` consistency with actual content.
- Structural-order check (the 14 required sections in mandated sequence).
- Old template version detection.
- Accessibility checks (alt text on `\includegraphics`, TikZ alt text, table-header configuration).
- PDF-level checks (margins, embedded fonts, abstract word count).

## Error handling

| Situation | Behavior | Exit |
|---|---|---|
| Input path missing or unrecognized | Print message, no traceback | `2` |
| LuaLaTeX not installed | Print install hint (TeX Live 2025), no traceback | `3` |
| Validation `[error]` (no compile attempted) | Print issues report | `1` |
| Validation `[error]` and compile attempted | Print issues + last 5 `! ... l.NN` blocks | `1` |
| Compile fails with no validation errors | Print compile errors only | `1` |
| Network failure on `--init` | Warn, fall back to bundled template, continue | `0` |
| All clean | Print PDF path, open it | `0` |

Compile failure does not suppress the validation report. Both are emitted; the validation report appears first.

## Testing strategy

- **Test runner:** `pytest`.
- **Coverage target:** 80% (relaxed vs latex2arxiv's 85%; tightens once shape stabilizes).
- **Per-rule pinning:** each E1–E9 and W1–W2 rule gets one positive (rule fires) and one negative (rule does not fire) test. ~22 unit tests.
- **Fixtures:**
  - `fixtures/01-minimal-valid/` — bare-minimum project that passes all v0.1 checks.
  - `fixtures/02-missing-required/` — parametrized: strips one required command at a time.
  - `fixtures/03-editmode-still-on/` — final-stage project that left `editMode` on.
  - `fixtures/00-real-dissertation/` — author's actual dissertation (added once available; baseline JSON committed, source gitignored if private).
- **CI matrix:** Python 3.10–3.13, Ubuntu only. No macOS or live-LuaLaTeX smoke job in v0.1 — added in v0.2.

## Release plan

- **v0.1:** Init + Compile + Validate (this design).
- **v0.2:** Validate expansion (`\major`/`\chair` to error, structural-order check, PDF-level checks), macOS CI matrix, live-LuaLaTeX smoke job.
- **v0.3:** Cleanup pass (strip `\todo`, comments, draft packages, drop `editMode` automatically).
- **v0.4+:** MCP server, VS Code extension, GitHub Action.

## Open questions

- **Compatibility with old template versions.** UF allows pre-Fall-2025 templates through Summer 2026. v0.1 targets the new template only; old-template detection is a v0.2 warn.
- **Git URL vs local-dir parity.** Git URL input runs the same pipeline but writes the PDF to cwd, not to the cloned tmp dir. Edge case: collisions on repeated runs.
- **Coverage of the `editMode` warn.** The class file may have other option flags worth catching (`draftMode`, `chapterMode`); v0.1 covers `editMode` only.

## References

- UF Graduate School format guide — https://success.grad.ufl.edu/td/formatting/
- UF IT template page — https://it.ufl.edu/helpdesk/graduate-resources/ms-word--latex-templates/
- UF ETD specs (detailed) — https://grad.ufl.edu/academics/editorial/etd-specs/
- Bundled template — `pipeline/template/` (sourced from UF IT distribution, Nov 2025)

# latex2ufdissertation

[![CI](https://github.com/YuZh98/latex2ufdissertation/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/YuZh98/latex2ufdissertation/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

A safety-net validator for UF doctoral dissertations written with the University of Florida `ufdissertation` LaTeX template (Fall 2025+, and the immediately-prior revision). Point it at your project and it prints a severity-tiered report — every finding tagged with the UF rule it comes from — so you get one more pair of eyes before clicking submit.

> **Advisory only.** A clean report means none of the mechanical formatting rules in [`docs/uf-rules.md`](./docs/uf-rules.md) were violated. It is **not** a substitute for review by the UF Graduate Editorial Office and does **not** guarantee your dissertation will be accepted. You remain responsible for your submission.

## Install

Requires **Python 3.10+**. Not yet on PyPI (a `pip install latex2ufdissertation` lands with v1.0.0). For now, install from GitHub — pin a release tag, or drop `@v…` for the latest `main`:

```bash
pip install "git+https://github.com/YuZh98/latex2ufdissertation.git@v0.4.0"
```

The default validation is pure Python and needs no LaTeX install. The optional `--compile` step (below) additionally requires **LuaLaTeX with TeX Live 2025**, which is the toolchain UF mandates for the template.

## Demo dissertation

[`examples/demo_dissertation/`](./examples/demo_dissertation/) is a hand-crafted "fake" UF dissertation that passes every rule we test for, so it serves as a known-good reference. The file contains the illustration of this tool latex2ufdissertation and lists UF rules on dissertation formatting, so it doubles as a teaching aid.

- Compiled output: [`examples/demo_dissertation/main.pdf`](./examples/demo_dissertation/main.pdf) (20+ pages, LuaLaTeX + TeX Live 2025)
- Compile it yourself: `cd examples/demo_dissertation && lualatex main && bibtex main && lualatex main && lualatex main`
- `latex2ufdissertation --demo` prints its location.

## Usage

By default the tool **validates your LaTeX source and stops** — it does not compile:

```bash
latex2ufdissertation my-thesis/
```

Point it at any of these — the input type is auto-detected:

```bash
latex2ufdissertation thesis.zip            # a project archive
latex2ufdissertation main.tex              # the master .tex (its folder becomes the project root)
latex2ufdissertation https://github.com/you/thesis.git   # a git URL
latex2ufdissertation dissertation.pdf      # a compiled PDF (PDF-layer checks only)
```

Add `--compile` to also compile with LuaLaTeX and run the PDF-layer checks (font family/size, hyperlinks) against the rendered output:

```bash
latex2ufdissertation --compile my-thesis/
```

Starting fresh? Scaffold a project from the bundled UF template, then validate it:

```bash
latex2ufdissertation --init my-thesis/
latex2ufdissertation my-thesis/
```

## Example

A clean project — exit code `0`:

```console
$ latex2ufdissertation my-thesis/
  validating main.tex

Summary: 0 must-fix, 0 review — clean.
Severity guide: must-fix = will likely cause UF Graduate School rejection; review = discretionary, verify manually.
Scope: clean means no violations of the rules this tool checks (targeting the Fall-2025+ UF ufdissertation template). It does NOT guarantee Graduate School acceptance — the editorial office checks requirements beyond this tool's scope.
PDF layer did not run (validate-only mode, the default). UF-F2, UF-F3, and other PDF-authoritative rules were not verified. Re-run with --compile for full coverage.
```

A project with problems — findings grouped by severity, one line each, and exit code `1`:

```console
$ latex2ufdissertation my-thesis/
  validating main.tex

Must-fix (4)

  UF-F14  main.tex  \degreeYear missing or empty
  UF-F14  main.tex  \degreeMonth missing or empty
  UF-F14  main.tex  \major missing or empty
  UF-F14  main.tex  \chair missing or empty
    Fix: Set the missing metadata macro with a non-empty value in main.tex.

Summary: 4 must-fix, 0 review.
[ ... severity guide + scope notes, as above ... ]
```

Every finding line is `UF-<rule>  <location>  <observed>`. Look up any rule ID in [`docs/uf-rules.md`](./docs/uf-rules.md) for the full requirement and its UF source.

For scripting, `--json` emits the machine-readable v1 schema on stdout (progress stays on stderr, so `latex2ufdissertation --json my-thesis/ | jq …` works unfiltered):

```json
{
  "schema_version": "1.0",
  "input": "my-thesis/",
  "detected_mode": "dir",
  "template_version": "unknown",
  "findings": [
    {
      "severity": "must-fix",
      "rule_id": "UF-F14",
      "layer": "source",
      "location": "main.tex",
      "observed": "\\degreeYear missing or empty",
      "required": "\\degreeYear{...} with a non-empty argument",
      "fix_hint": "Set the missing metadata macro with a non-empty value in main.tex.",
      "source_url": "https://github.com/YuZh98/latex2ufdissertation/blob/main/docs/uf-rules.md#uf-f14--required-metadata-macros-set"
    }
  ],
  "summary": { "must_fix_count": 4, "review_count": 0, "exit_code": 1, "exit_reason": "must_fix_present" }
}
```

Output is deterministic: the same input produces byte-identical JSON (`sort_keys=True`).

## Inputs

| Input | Source-layer checks | PDF-layer checks | Compiles? |
|---|---|---|---|
| Project directory | yes | only with `--compile` | only with `--compile` (uses a bundled `main.pdf` if present) |
| `*.zip` archive | yes | only with `--compile` | only with `--compile` (uses a bundled PDF if present) |
| Git URL (https or ssh) | yes | only with `--compile` | only with `--compile` |
| `*.tex` master file | yes (parent dir becomes the root) | only with `--compile` | only with `--compile` |
| `*.pdf` (already compiled) | skipped | yes | no |

PDF-layer checks currently implemented: **F2** (font family), **F3** (font size), **S1** (PDF present/readable), **S5** (hyperlink annotations). Further PDF backups (F1, F4, F6, F12) are planned.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | No `must-fix` findings (`review` findings are advisory and do not change this) |
| `1` | One or more `must-fix` findings |
| `2` | Fatal on this input (compile failure, unreadable input, master's-thesis input) |
| `3` | Fatal on this environment (missing toolchain, e.g. no LuaLaTeX with `--compile`) |

## Severity tiers

- **`must-fix`** — a documented UF rule violation the Editorial Office is expected to require fixing. Trips exit code `1`.
- **`review`** — a likely issue needing human judgment: the tool flags, you decide. Does not affect the exit code.

Some `must-fix` rules rest on heuristics or soft sources — see [`docs/spec-v1.0.md`](./docs/spec-v1.0.md) §7.2 for the caveats.

## Flags

| Flag | What it does |
|---|---|
| (no flag) | Validate the LaTeX source and print the report |
| `--compile` | Also compile with LuaLaTeX and run the PDF-layer checks |
| `--init DIR` | Scaffold a new project from the bundled UF template at `DIR` |
| `--main FILE` | Override master `.tex` auto-detection |
| `--json` | Emit the machine-readable v1 schema on stdout |
| `--demo` | Print the location of the bundled demo dissertation and exit |
| `--version` | Print the version and exit |

## UF dissertation submission resources

This tool checks a subset of the mechanical rules; UF's own resources are authoritative for the full process.

| Resource | What it covers |
|---|---|
| [Graduate ETD support hub](https://it.ufl.edu/helpdesk/graduate-resources/) | The Thesis & Dissertation Support Center — the starting point for template, tutorials, and reviews |
| [Official MS Word & LaTeX templates](https://it.ufl.edu/helpdesk/graduate-resources/ms-word--latex-templates/) | The authoritative template downloads; LuaLaTeX + TeX Live 2025 required |
| [Formatting tutorials](https://it.ufl.edu/helpdesk/graduate-resources/online-tutorials/) | How-to walkthroughs for tables, figures, and the template overall |
| [Book a document review](https://it.ufl.edu/helpdesk/graduate-resources/book-an-appointment/) | One-on-one appointments and email document reviews |
| [Graduate Editorial Office](https://it.ufl.edu/helpdesk/graduate-resources/graduate-editorial-office/) | Reference systems and copyright/documentation questions |
| [UF Graduate School](https://graduateschool.ufl.edu/) | Submission deadlines and degree requirements |
| [Deadlines](https://success.grad.ufl.edu/td/deadlines/) | The official UF Graduate School deadlines for each semester |

## Scope

**In scope.** Doctoral dissertations using `\documentclass{ufdissertation}` (Fall 2025+ and the immediately-prior revision). Source-layer validation by default; PDF-layer validation with `--compile`. Five input modes: directory, zip, `.tex` master, git URL, compiled PDF. CLI + machine-readable JSON.

**Out of scope.** Master's theses (deferred — same template, different `\thesisType`). Source cleanup or Overleaf-export normalization. External URL liveness. A hosted web service or GUI. See [`docs/spec-v1.0.md`](./docs/spec-v1.0.md) for the locked specification.

## Security

`--compile` runs LuaLaTeX on your sources. Only compile projects you trust — see [`SECURITY.md`](./SECURITY.md) for the threat model.

## Documentation

- [`docs/spec-v1.0.md`](./docs/spec-v1.0.md): what v1.0 is and is not (locked sections + acceptance gates).
- [`docs/uf-rules.md`](./docs/uf-rules.md): the rule catalog (UF-F1 … UF-A2, each with its UF citation).
- [`docs/json-schema.md`](./docs/json-schema.md): the `--json` output contract.
- [`CONTRIBUTING.md`](./CONTRIBUTING.md): engineering gates.
- [`CHANGELOG.md`](./CHANGELOG.md): release history.

## Status

v0.4.0 released (pre-1.0). v1.0 work in progress (see [`docs/spec-v1.0.md`](./docs/spec-v1.0.md) for the tentative acceptance criteria and current gate status). MIT license.

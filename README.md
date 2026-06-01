# latex2ufdissertation

[![CI](https://github.com/YuZh98/latex2ufdissertation/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/YuZh98/latex2ufdissertation/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

A safety-net validator for UF doctoral dissertations using the Fall 2025+ University of Florida LaTeX template. Given a project archive, project directory, or git URL, it produces a severity-tiered report citing the originating UF rule for each finding — one more pair of eyes before clicking submit. (PDF-only input and a separate PDF-layer of checks are planned for v1.0.)

> **The validator is advisory.** It is not a substitute for review by the UF Graduate Editorial Office. A clean report means none of the documented mechanical formatting rules in [`docs/uf-rules.md`](./docs/uf-rules.md) were violated; it does not guarantee UF will accept the dissertation. The student remains responsible.

## Install

Not yet published to PyPI. Install from GitHub — pin a release tag, or omit `@v…` for the latest `main`:

    pip install "git+https://github.com/YuZh98/latex2ufdissertation.git@v0.2.0"

Requires Python 3.10+ and (for the compile path) LuaLaTeX with TeX Live 2025.

## Demo dissertation

A hand-crafted UF dissertation that satisfies every must-fix rule lives at [**`examples/demo_dissertation/`**](./examples/demo_dissertation/) — a known-good reference you can compile and read top-to-bottom to see what a compliant project looks like. Every section file is annotated with the UF rule it satisfies, so the demo doubles as a teaching aid for students.

- Browse the source: [`examples/demo_dissertation/`](./examples/demo_dissertation/)
- View the compiled output: [`examples/demo_dissertation/main.pdf`](./examples/demo_dissertation/main.pdf) (26 pages, LuaLaTeX + TeX Live 2025)
- Local compile: `cd examples/demo_dissertation && lualatex main && bibtex main && lualatex main && lualatex main`
- From an install: `latex2ufdissertation --demo` prints the GitHub link (and a local path when run from a source checkout)

## Quickstart

Scaffold a new project from the bundled UF template, then validate + compile:

    latex2ufdissertation --init my-thesis/
    cd my-thesis/
    latex2ufdissertation .

The default command validates the project and compiles to PDF with LuaLaTeX. If you do not have a TeX installation, validate without compiling:

    latex2ufdissertation --dry-run .

## Inputs

| Input | Source-layer validation | Compile |
|---|---|---|
| Project directory | yes | yes (unless `--dry-run`) |
| `*.zip` archive | yes | yes (unless `--dry-run`) |
| Git URL (https or ssh) | yes | yes (unless `--dry-run`) |

PDF-only input and a separate PDF-layer of checks are planned for v1.0; see [`docs/spec-v1.0.md`](./docs/spec-v1.0.md).

## Outputs

- **Human-readable report** (default): findings grouped by validation layer and rule category, each line tagged with severity, `UF-*` rule ID, file:line location, and a link to the rule's source documentation.
- **Machine-readable JSON** (`--json`): emits the v1 schema to stdout (single JSON document, `sort_keys=True` for byte-identical output across runs). Progress messages go to stderr so `latex2ufdissertation --json … | jq …` works without filtering.

The JSON schema v1 shape:

```
{
  "schema_version": "1.0",
  "input": "...",
  "template_version": "..." | null,
  "findings": [ {severity, rule_id, layer, location, observed, required, fix_hint, source_url}, ... ],
  "summary": {must_fix_count, review_count, exit_code, exit_reason}
}
```

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Zero `must-fix` findings (`review`-only findings are advisory) |
| `1` | One or more `must-fix` findings |
| `2` | Fatal on this input (unsupported template, compile failure, unreadable input) |
| `3` | Fatal on this environment (missing required toolchain, e.g. no LuaLaTeX) |

## Severity tiers

Two tiers only:

- **`must-fix`** — documented UF rule violation; submission will be rejected. Contributes to exit code 1.
- **`review`** — likely issue requiring human judgment; the tool flags, the student decides. Does not contribute to exit code.

Every finding carries a `UF-*` rule ID and a link back to the rule's catalog entry in [`docs/uf-rules.md`](./docs/uf-rules.md). See [`docs/spec-v1.0.md`](./docs/spec-v1.0.md) for the full output contract.

## Flags

| Flag | What it does |
|---|---|
| (no flag) | Validate + compile → emit PDF |
| `--init DIR` | Scaffold a new project at DIR |
| `--demo` | Print location of the bundled demo dissertation and exit |
| `--dry-run` | Validate only, skip compile |
| `--main FILE` | Override master `.tex` auto-detect |
| `--json` | Machine-readable summary on stdout |
| `--version` | Print version and exit |

## Scope

**In scope for v0.1 (shipping today).** Doctoral dissertations using `\documentclass{ufdissertation}` (Fall 2025+). Source-layer validation. Three input modes: zip, directory, git URL. CLI as the engine. LuaLaTeX compile driver.

**Planned for v1.0.** PDF-layer validation, PDF-only input mode, ETD-upload walkthrough (`--guide`). See [`docs/spec-v1.0.md`](./docs/spec-v1.0.md) for the full v1.0 specification.

**Out of scope for v1.0.** Master's theses (deferred, same template, different `\thesisType`). The pre-Fall-2025 UF template (refused with a migration message). Source cleanup or Overleaf-export normalization. External URL liveness (reserved for `--check-links` in a future release). MCP server, browser extensions, editor extensions (separate artifacts that wrap the CLI). Hosted web service or GUI.

## Security

This tool compiles LaTeX. Only run it on sources you trust — see [`SECURITY.md`](./SECURITY.md) for the threat model.

## Documentation

- [`docs/spec-v1.0.md`](./docs/spec-v1.0.md) — what v1.0 is and is not (locked sections + acceptance criteria).
- [`docs/uf-rules.md`](./docs/uf-rules.md) — the rule catalog the validator checks against (UF-F1 … UF-A2 with citations).
- [`examples/demo_dissertation/`](./examples/demo_dissertation/) — the known-good demo dissertation linked above; doubles as a teaching reference.
- [`CONTRIBUTING.md`](./CONTRIBUTING.md) — engineering gates and what goes in committed artifacts.
- [`CHANGELOG.md`](./CHANGELOG.md) — release history.

## Status

v0.1 released. v1.0 work in progress; see [`docs/spec-v1.0.md`](./docs/spec-v1.0.md) for acceptance criteria. MIT license.

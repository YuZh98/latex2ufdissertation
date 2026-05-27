# latex2ufdissertation

A safety-net validator for UF doctoral dissertations using the Fall 2025+ University of Florida LaTeX template. Given a project archive, project directory, or compiled PDF, it produces a grouped, severity-tiered report citing the originating UF rule for each finding — one more pair of eyes before clicking submit.

> **The validator is advisory.** It is not a substitute for review by the UF Graduate Editorial Office. A clean report means none of the documented mechanical formatting rules in [`docs/uf-rules.md`](./docs/uf-rules.md) were violated; it does not guarantee UF will accept the dissertation. The student remains responsible.

## Install

    pip install latex2ufdissertation

Requires Python 3.10+ and (for the compile path) LuaLaTeX with TeX Live 2025.

## Quickstart

Scaffold a new project from the bundled UF template, then validate + compile:

    latex2ufdissertation --init my-thesis/
    cd my-thesis/
    latex2ufdissertation .

The default command runs both validation layers and compiles to PDF. Compile-only or validate-only modes are available via flags below.

## Inputs

| Input | Source layer | PDF layer | Compile |
|---|---|---|---|
| Project directory | yes | yes (bundled PDF or compiled output) | only if no PDF present |
| `*.zip` archive | yes | yes (bundled PDF or compiled output) | only if no PDF in archive |
| `*.pdf` | skipped (noted in report) | yes | no |

## Outputs

- **Human-readable report** (default): grouped by rule category. Each finding shows severity, UF rule ID, location (file:line or page), observed vs required, fix hint, and a URL to the UF source.
- **Machine-readable JSON** (`--json`): versioned schema for downstream tooling. Progress goes to stderr; stdout is JSON only.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Zero must-fix findings (review-only findings are advisory) |
| `1` | One or more must-fix findings |
| `2` | Fatal on this input (unsupported template, compile failure, unreadable input, master's thesis, pre-Fall-2025 template) |
| `3` | Fatal on this environment (missing required toolchain, e.g. no LuaLaTeX) |

## Severity tiers

- **must-fix** — documented UF rule violation; submission will be rejected.
- **review** — likely issue requiring human judgment; the tool flags, the student decides.

Two tiers only. No INFO / TIP / SUGGESTION.

## Flags

| Flag | What it does |
|---|---|
| (no flag) | Validate + compile → emit PDF |
| `--init DIR` | Scaffold a new project at DIR |
| `--dry-run` | Validate only, skip compile |
| `--main FILE` | Override master `.tex` auto-detect |
| `--json` | Machine-readable summary on stdout |
| `--guide` | ETD-upload walkthrough for GIMS |
| `--version` | Print version and exit |

## Scope

**In scope.** Doctoral dissertations using `\documentclass{ufdissertation}` (Fall 2025+). Two-layer validation: LaTeX source + compiled PDF. Three input modes: zip, directory, PDF. CLI as the engine. Machine-readable JSON output.

**Out of scope for v1.0.** Master's theses (deferred, same template, different `\thesisType`). The pre-Fall-2025 UF template (refused with a migration message). Source cleanup or Overleaf-export normalization. External URL liveness (reserved for `--check-links` in a future release). MCP server, browser extensions, editor extensions (separate artifacts that wrap the CLI). Hosted web service or GUI.

## Documentation

- [`docs/spec-v1.0.md`](./docs/spec-v1.0.md) — what v1.0 is and is not (locked sections + acceptance criteria).
- [`docs/uf-rules.md`](./docs/uf-rules.md) — the rule catalog the validator checks against (UF-F1 … UF-A2 with citations).
- [`tests/fixtures/demo_dissertation/`](./tests/fixtures/demo_dissertation/) — a hand-crafted dissertation that satisfies every must-fix rule; doubles as a teaching reference.
- [`CONTRIBUTING.md`](./CONTRIBUTING.md) — engineering gates and what goes in committed artifacts.
- [`CHANGELOG.md`](./CHANGELOG.md) — release history.

## Status

v0.1 released. v1.0 work in progress; see [`docs/spec-v1.0.md`](./docs/spec-v1.0.md) for acceptance criteria. MIT license.

# latex2ufdissertation

A safety-net validator for UF doctoral dissertations using the Fall 2025+ University of Florida LaTeX template. Given a project archive, project directory, or compiled PDF, it produces a grouped, severity-tiered report citing the originating UF rule for each finding — one more pair of eyes before clicking submit.

> **The validator is advisory.** It is not a substitute for review by the UF Graduate Editorial Office. A clean report means none of the documented mechanical formatting rules in [`docs/uf-rules.md`](./docs/uf-rules.md) were violated; it does not guarantee UF will accept the dissertation. The student remains responsible.

## Install

    pip install latex2ufdissertation

Requires Python 3.10+ and (for the compile path) LuaLaTeX with TeX Live 2025.

## Demo dissertation

A hand-crafted UF dissertation that satisfies every must-fix rule lives at [**`examples/demo_dissertation/`**](./examples/demo_dissertation/) — a known-good reference you can compile and read top-to-bottom to see what a compliant project looks like. Every section file is annotated with the UF rule it satisfies, so the demo doubles as a teaching aid for students.

- Browse the source: [`examples/demo_dissertation/`](./examples/demo_dissertation/)
- View the compiled output: [`examples/demo_dissertation/main.pdf`](./examples/demo_dissertation/main.pdf) (26 pages, LuaLaTeX + TeX Live 2025)
- Local compile: `cd examples/demo_dissertation && lualatex main && bibtex main && lualatex main && lualatex main`
- From an install: `latex2ufdissertation --demo` prints the location and link

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

- **Human-readable report** (default): each finding prints with a severity tag, the rule, and the location.
- **Machine-readable JSON** (`--json`): emits `{input, output, main_tex, dry_run, errors, warnings, compile_result}` to stdout; progress messages go to stderr.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | No errors |
| `1` | One or more errors |
| `2` | Fatal on this input (unsupported template, compile failure, unreadable input) |
| `3` | Fatal on this environment (missing required toolchain, e.g. no LuaLaTeX) |

## Severity tiers

v0.1 emits two tiers:

- **error** — documented UF rule violation; blocks submission.
- **warn** — likely issue; review and decide.

v1.0 will rebrand these to **must-fix** and **review** respectively, and expand the JSON schema to include `schema_version`, structured `findings`, and per-finding source URLs. See [`docs/spec-v1.0.md`](./docs/spec-v1.0.md).

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

**Planned for v1.0.** PDF-layer validation, PDF-only input mode, machine-readable JSON output (`--json`), ETD-upload walkthrough (`--guide`). See [`docs/spec-v1.0.md`](./docs/spec-v1.0.md) for the full v1.0 specification.

**Out of scope for v1.0.** Master's theses (deferred, same template, different `\thesisType`). The pre-Fall-2025 UF template (refused with a migration message). Source cleanup or Overleaf-export normalization. External URL liveness (reserved for `--check-links` in a future release). MCP server, browser extensions, editor extensions (separate artifacts that wrap the CLI). Hosted web service or GUI.

## Documentation

- [`docs/spec-v1.0.md`](./docs/spec-v1.0.md) — what v1.0 is and is not (locked sections + acceptance criteria).
- [`docs/uf-rules.md`](./docs/uf-rules.md) — the rule catalog the validator checks against (UF-F1 … UF-A2 with citations).
- [`examples/demo_dissertation/`](./examples/demo_dissertation/) — the known-good demo dissertation linked above; doubles as a teaching reference.
- [`CONTRIBUTING.md`](./CONTRIBUTING.md) — engineering gates and what goes in committed artifacts.
- [`CHANGELOG.md`](./CHANGELOG.md) — release history.

## Status

v0.1 released. v1.0 work in progress; see [`docs/spec-v1.0.md`](./docs/spec-v1.0.md) for acceptance criteria. MIT license.

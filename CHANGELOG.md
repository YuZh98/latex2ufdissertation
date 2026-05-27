# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · SemVer.

## [Unreleased]

### Added
- `docs/spec-v1.0.md` — locked v1.0 product specification (goal, scope, users, inputs, outputs, behavior, hard rules, soft rules, acceptance criteria).
- `docs/uf-rules.md` — canonical UF rule catalog (UF-F1 … UF-A2) with stable IDs, UF source citations, severity tiers, detection strategies, and validation layer per rule.
- `examples/demo_dissertation/` — hand-crafted known-good dissertation that satisfies every must-fix rule; doubles as a teaching reference. Includes a committed compiled `main.pdf` so PDF-layer tests run without a TeX installation. (Previously located at `tests/fixtures/demo_dissertation/`; promoted to a top-level `examples/` directory for student discoverability.)
- `--demo` CLI flag prints the location and GitHub URL of the bundled demo dissertation so students can quickly find a known-good reference project.
- `CONTRIBUTING.md` — engineering gates (CI matrix, coverage threshold, pre-commit hook set, deprecation-strict pytest pass, determinism pinning test) and committed-artifact policy.
- `SECURITY.md` — vulnerability reporting policy and supported-version table.
- `.github/ISSUE_TEMPLATE/{bug_report,feature_request}.md` and `.github/PULL_REQUEST_TEMPLATE.md`.
- Exit code `3` for missing toolchain (e.g. no LuaLaTeX on `PATH`), distinguishing environment failure from input failure.
- `.github/workflows/ci.yml` — CI workflow enforcing pre-commit, the Python 3.10/3.11/3.12/3.13 test matrix, a coverage floor, and a deprecation-strict pytest pass.
- `.pre-commit-config.yaml` — pre-commit hooks for trailing whitespace, EOF newline, merge-conflict markers, YAML/TOML syntax, large-file blocker, and `ruff` format + lint. Vendored upstream files are excluded.
- `CODE_OF_CONDUCT.md` — adapted from the Contributor Covenant 2.1; reporting flow points at the maintainer with a separate channel for security issues.
- `.github/dependabot.yml` — weekly grouped minor/patch updates for both pip and github-actions ecosystems.
- README CI status, license, and Python-version badges at the top so visitors landing on the public repo see project status at a glance.
- `docs/v1.0-rule-rebrand.md` — design document for v1.0 sub-project #1 (rule rebrand + ID system). Locked architecture, finding shape, v0.1 → UF-* mapping, JSON schema v1 freeze, and testing strategy.
- **v1.0 sub-project #1 implementation: rule rebrand + ID system.**
  - `latex2ufdissertation/pipeline/rules.py` — single-source-of-truth registry for every `UF-*` rule. `Rule` dataclass + `RULES` dict mirror the 29 entries in `docs/uf-rules.md`. Severity / layer / `exit_reason` literals are constants in this module so a typo fails at import time.
  - `latex2ufdissertation/pipeline/types.py` — new `Finding` dataclass with the eight v1 schema fields (`severity`, `rule_id`, `layer`, `location`, `observed`, `required`, `fix_hint`, `source_url`). `Issues` collector replaces `errors` / `warnings` lists with `findings: list[Finding]`; `Issues.add(rule_id, ...)` resolves metadata from `RULES`. New `ConverterError` subclasses (`UnreadableInput`, `UnsupportedTemplate`, `ThesisInput`, `MissingToolchain`) carry per-exception `exit_reason`.
  - `latex2ufdissertation/pipeline/report.py` — `format_human(issues)` (grouped by layer + rule category, sorted for determinism) and `format_json(issues)` (JSON schema v1: `schema_version`, `input`, `template_version`, `findings`, `summary`). Both buffer-then-emit; checks never print directly.
  - `latex2ufdissertation/pipeline/checks.py` — every v0.1 emit site rebranded to `issues.add(rule_id="UF-XYZ", ...)` per the mapping in `docs/v1.0-rule-rebrand.md`.
  - Public API frozen via `__all__` in `latex2ufdissertation/__init__.py`: `Issues`, `Finding`, `Rule`, `RULES`, `run_checks`, exception types, `__version__`.
  - Tests: `tests/test_rules.py` asserts every `UF-*` ID in `docs/uf-rules.md` has a matching `Rule` entry (and vice versa); `tests/test_report.py` exercises the v1 JSON schema shape and sort order; `tests/test_determinism.py` runs the validator twice on the demo dissertation with `--dry-run --json` and asserts byte-identical stdout (xfail placeholder removed).
  - Coverage floor ratcheted 60% → 70%; actual coverage 74.54%.

### Fixed
- `--json` stdout was being contaminated by progress / diagnostic output, breaking the documented "stdout is JSON only" contract. All progress messages (`[warn]` / `[error]` lines, `Summary:` line, `validating` / `compiling` lines, compile-error blocks, all `--init` scaffold log lines including the final "scaffold ready" line) now route to stderr. The `--demo` output block and the `--json` payload stay on stdout; `--version` uses argparse's built-in stdout path. New regression test in `tests/test_cli.py` guards the split.
- README opening sentence no longer advertises PDF input (the v0.1 resolver rejects `.pdf`; PDF input is a v1.0 plan documented later in the README).
- README `--demo` line now explicitly says the local path appears only for source checkouts.

### Changed
- README rewritten to honestly distinguish what's shipping (source-layer validation, three input modes, `--dry-run` on-ramp) from what's planned (PDF input + PDF layer, `--guide`). Severity-tier section now describes the v1.0 `must-fix` / `review` vocabulary and the JSON schema v1 shape directly (no more "v0.1 emits errors/warns" framing).

### Changed (breaking)
- **JSON output schema is the new v1 shape.** Old keys (`errors`, `warnings`, `dry_run`, `main_tex`, `compile_result`) are removed from `--json` stdout; the new payload has `schema_version`, `input`, `template_version`, `findings: [{severity, rule_id, layer, location, observed, required, fix_hint, source_url}]`, and `summary: {must_fix_count, review_count, exit_code, exit_reason}`. Downstream consumers parsing the old shape must update.
- **Human-readable report format changed.** Findings group by layer + rule category, each tagged with severity + `UF-*` ID + location + source URL. Old `[warn] / [error]` prefixed lines are replaced by `[must-fix] / [review] UF-XYZ` lines.
- **`Issues.warn()` / `Issues.error()` removed.** Public collector API is `Issues.add(rule_id=..., location=..., observed=..., required=..., fix_hint=...)`. Downstream code calling the old methods will fail.
- `docs/uf-rules.md` citations now reference the canonical `latex2ufdissertation/pipeline/template/ufdissertation.cls`; the fixture copy carries a 22-line provenance header and is no longer the citation target.

### Removed
- Internal planning and design documents (`docs/plans/`, `docs/design/`) are no longer tracked; they were scratch artifacts and have been stripped from history.

## [0.1.0] - 2026-05-26

Initial release. Validate + compile UF dissertation/thesis projects with the new UF template.

### Added
- CLI: `latex2ufdissertation INPUT [OUTPUT.pdf] [--init|--dry-run|--main|--json|--version]`
- Source-level validation: 9 errors + 2 warns against UF format rules (the v1.0 spec rebrands these severity tiers to `must-fix` / `review`)
- LuaLaTeX compile driver
- `--init` scaffolds from UF IT site, falls back to bundled template
- Accepts zip / directory / git URL inputs

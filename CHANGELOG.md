# Changelog

All notable changes to this project will be documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · SemVer.

## [Unreleased]

v1.0 sub-project #1 lands: `UF-*` rule IDs, `must-fix` / `review` severity tiers, JSON schema v1. Infrastructure baseline: CI matrix, pre-commit hooks, dependabot, Code of Conduct, issue and PR templates. Demo dissertation promoted to top-level `examples/`. Version bumped 0.1.0 → 0.2.0 (breaking JSON output + public `Issues` API).

### Added
- `docs/spec-v1.0.md`: v1.0 product specification (goal, scope, users, inputs, outputs, hard rules, soft rules, acceptance criteria)
- `docs/uf-rules.md`: canonical UF rule catalog (`UF-F1` … `UF-A2`) with citations, severity tiers, detection strategies
- `examples/demo_dissertation/`: hand-crafted known-good dissertation that satisfies every must-fix rule; doubles as a teaching reference. Includes committed `main.pdf` so PDF-layer tests run without a TeX install
- `--demo` flag: prints the GitHub URL of the bundled demo (and local path for source checkouts)
- `latex2ufdissertation/pipeline/rules.py`: single-source-of-truth `Rule` dataclass + `RULES` dict covering all 29 catalog entries
- `latex2ufdissertation/pipeline/report.py`: `format_human` (grouped + sorted) + `format_json` (JSON schema v1)
- `Finding` dataclass with the eight v1 fields (`severity`, `rule_id`, `layer`, `location`, `observed`, `required`, `fix_hint`, `source_url`)
- `Issues.add(rule_id, ...)` resolves metadata from `RULES` so call sites stay terse
- `ConverterError` subclasses (`UnreadableInput`, `UnsupportedTemplate`, `ThesisInput`, `MissingToolchain`) carry per-exception `exit_reason`
- Public API frozen via `__all__` in `latex2ufdissertation/__init__.py`
- Exit code `3` for missing toolchain (e.g. no LuaLaTeX on `PATH`); distinguishes environment failure from input failure
- `CONTRIBUTING.md`: engineering gates and committed-artifact policy
- `SECURITY.md`: vulnerability-reporting flow (GitHub Security Advisory)
- `CODE_OF_CONDUCT.md`: adapted from Contributor Covenant 2.1
- `.github/workflows/ci.yml`: pre-commit job + Python 3.10–3.13 matrix on ubuntu + macOS spot-check + coverage gate + deprecation-strict pytest + coverage XML artifact
- `.pre-commit-config.yaml`: trailing-whitespace, EOF newline, merge-conflict, YAML/TOML syntax, 500 KB large-file blocker, `ruff` format + lint; vendored upstream files excluded
- `.github/dependabot.yml`: weekly grouped minor/patch updates for pip and github-actions ecosystems
- `.github/ISSUE_TEMPLATE/{bug_report,feature_request}.md` and `.github/PULL_REQUEST_TEMPLATE.md`
- `latex2ufdissertation/pipeline/template/README.md`: provenance + re-sync procedure for the vendored UF template
- README CI / license / Python-version badges
- Determinism pinning test: two `--dry-run --json` runs on the demo dissertation must produce byte-identical stdout
- Drift tests: catalog ↔ registry parity (ID, severity, layer); silent parse failures fail loudly

### Changed (breaking)
- JSON output schema: old keys (`errors`, `warnings`, `dry_run`, `main_tex`, `compile_result`) removed; new payload `{schema_version, input, template_version, findings: [{severity, rule_id, layer, location, observed, required, fix_hint, source_url}], summary: {must_fix_count, review_count, exit_code, exit_reason}}`
- Human-readable report: findings grouped by layer + rule category, each line tagged with severity + `UF-*` ID + location + source URL; old `[error]` / `[warn]` prefixes replaced
- Public `Issues` API: `Issues.warn()` / `Issues.error()` removed in favor of `Issues.add(rule_id=..., location=..., observed=..., required=..., fix_hint=...)`
- `Issues.dry_run`, `Issues.output_path`, `Issues.compile_result` removed (never read after the JSON schema change)
- `compile_pdf()` signature: dropped unused `issues: Issues` parameter
- `UF-D2` (LuaLaTeX directive) severity promoted from `warn` to `must-fix` per the catalog
- Version bumped 0.1.0 → 0.2.0

### Changed
- Stdout / stderr split: progress and diagnostic output (`Issues.add` lines, `Summary:` line, `validating` / `compiling` lines, compile-error blocks, `--init` scaffold log) routed to stderr so `--json` stdout stays a single JSON document
- `docs/uf-rules.md` citations now reference the canonical `latex2ufdissertation/pipeline/template/ufdissertation.cls`; the fixture copy has a 22-line provenance header and is no longer the citation target
- README rewritten to distinguish shipping behavior from v1.0-planned features; severity-tier section describes the v1.0 vocabulary directly
- Coverage floor ratcheted 60% → 70% (actual 74.65%)

### Fixed
- `summary.exit_code` on fatal-path JSON payloads: previously derived from findings only, so a process exiting 2 (unreadable input) or 3 (missing toolchain) reported `exit_code: 0` in the JSON. Now resolved via `exit_reason` mapping
- JSON sort order diverged from spec §6 `(layer, rule_id, location)`: a category-rank tiebreaker was interpolated for human-readability and leaked into JSON. Sort functions now split — `_spec_sort_key` for JSON, `_human_sort_key` for the report
- README opening sentence no longer claims PDF input acceptance (the resolver rejects `.pdf`; PDF input is a v1.0 plan)
- `MissingToolchain` fatal paths no longer emit a misleading "Summary: 0 must-fix, 0 review — clean" line to stderr while the process exits 3

### Removed
- `docs/plans/` and `docs/design/`: internal planning artifacts stripped from history with `git-filter-repo`; both directories now gitignored

### Internal
- 107 tests (was 14); coverage 74.65% (was 0%)
- `tests/test_rules.py`: catalog / registry parity gate
- `tests/test_report.py`: JSON schema v1 shape + sort order + `sort_keys` round-trip
- Dependency direction: `rules.py` → `types.py` → `checks.py` → `report.py` → `cli.py`

## [0.1.0] - 2026-05-26

Initial release. One command validates and compiles UF dissertation / thesis projects against the new UF template.

### Added
- CLI: `latex2ufdissertation INPUT [OUTPUT.pdf] [--init|--dry-run|--main|--json|--version]`
- Source-level validation: 9 errors + 2 warns against UF format rules (rebranded to `must-fix` / `review` in [Unreleased])
- LuaLaTeX compile driver
- `--init` scaffolds from the UF IT site; falls back to bundled template on network failure
- Accepts `.zip`, directory, or git URL inputs

[Unreleased]: https://github.com/YuZh98/latex2ufdissertation/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/YuZh98/latex2ufdissertation/releases/tag/v0.1.0

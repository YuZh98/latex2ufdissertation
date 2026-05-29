# Changelog

All notable changes to this project will be documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · SemVer.

## [Unreleased]

### Added
- `docs/spec-v1.0.md`: v1.0 product specification (goal, scope, inputs, outputs, acceptance criteria)
- `docs/uf-rules.md`: canonical UF rule catalog (`UF-F1` … `UF-A2`) with citations and severity tiers
- `docs/json-schema.md`: JSON output schema reference (closes v1.0 acceptance gate 5)
- `latex2ufdissertation/pipeline/template/README.md`: provenance + re-sync procedure for the vendored UF template
- `examples/demo_dissertation/`: known-good dissertation satisfying every must-fix rule; committed `main.pdf` enables PDF-layer tests without a TeX install
- `examples/ufdissertation_samples/`: 14 UF Graduate School docx samples as reference snapshots for rule-design tiebreakers; not wired into pytest
- `--demo` flag: prints the GitHub URL of the bundled demo (and local path for source checkouts)
- `latex2ufdissertation/pipeline/rules.py`: single-source-of-truth `Rule` dataclass + `RULES` dict for all 29 catalog entries
- `latex2ufdissertation/pipeline/report.py`: `format_human` (grouped + sorted) and `format_json` (JSON schema v1)
- `Finding` dataclass with eight v1 fields (`severity`, `rule_id`, `layer`, `location`, `observed`, `required`, `fix_hint`, `source_url`)
- `Issues.add(rule_id, ...)` resolves metadata from `RULES` so call sites stay terse
- `ConverterError` subclasses (`UnreadableInput`, `UnsupportedTemplate`, `ThesisInput`, `MissingToolchain`) carry per-exception `exit_reason`
- Public API frozen via `__all__` in `latex2ufdissertation/__init__.py`
- Exit code `3` for missing toolchain (distinguishes environment failure from input failure)
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- `.github/workflows/ci.yml`: pre-commit + Python 3.10–3.13 matrix on ubuntu + macOS spot-check + coverage gate
- `.pre-commit-config.yaml`: trailing-whitespace, EOF newline, merge-conflict, YAML/TOML syntax, 500 KB large-file blocker, `ruff` format + lint
- `.github/dependabot.yml`: weekly grouped minor/patch updates for pip and github-actions
- `.github/ISSUE_TEMPLATE/{bug_report,feature_request}.md` and `.github/PULL_REQUEST_TEMPLATE.md`
- README CI / license / Python-version badges
- Determinism pinning test: two `--dry-run --json` runs must produce byte-identical stdout
- Drift tests: catalog ↔ registry parity (ID, severity, layer)
- `tests/fixtures/` snapshot harness: per-rule `input/` + `expected_findings.json` + `expected_report.txt` with `LATEX2UFD_REGEN_FIXTURES=1` regen workflow and a dir-non-empty gate. 17 must-fix fixtures covering `UF-D1`, `D2`, `D3`, `F1`, `F2`, `F3`, `F4`, `F5`, `F6`, `F7`, `F8`, `F9`, `F10`, `F11`, `F13`, `F14`, `F15`, `P1`, `S3`.
- Source-layer detectors for 18 of 19 must-fix catalog rules (only S1 PDF-only and S2 catalog-marked-no-code-path remain): `UF-D3`, `F1`, `F2`, `F3`, `F4`, `F5`, `F6`, `F7`, `F8`, `F9`, `F10`, `F11`, `F13`, `F14`, `F15`, `P1`, `S3`. Each ships a default `fix_hint` in the registry; per-rule scope decisions (relative-size commands for F3, `\flushleft` mass usage for F5, F4 scoped exceptions, manual heading impersonation for F11) pinned by negative tests
- `UF-F14` extended from 4 to all 8 catalog metadata macros (added `\degreeYear`, `\degreeMonth`, `\major`, `\chair`); `\degreeMonth` value-constraint enum (May / August / December, case-sensitive); closes #16
- `docs/uf-rules.md` § UF-F14 source citation gains S1 backing (previously C1-only)
- 231 tests; coverage 74.65%

### Changed
- JSON output schema (breaking): old keys removed; new payload `{schema_version, input, template_version, findings: [...], summary: {must_fix_count, review_count, exit_code, exit_reason}}`
- Human-readable report: findings grouped by layer + rule category, tagged with severity + `UF-*` ID + location + source URL
- `Issues` API (breaking): `.warn()` / `.error()` removed in favor of `.add(rule_id=..., location=..., observed=..., required=..., fix_hint=...)`
- `Issues.dry_run`, `Issues.output_path`, `Issues.compile_result` removed
- `compile_pdf()` signature: dropped unused `issues` parameter
- `UF-D2` (LuaLaTeX directive) severity promoted from `warn` to `must-fix` per the catalog
- Stdout / stderr split: progress and diagnostics routed to stderr so `--json` stdout stays a single JSON document
- `docs/uf-rules.md` citations reference the canonical vendored `ufdissertation.cls`
- README rewritten to distinguish shipping behavior from v1.0-planned features
- Coverage floor ratcheted 60% → 70% (actual 74.65%)
- Version bumped 0.1.0 → 0.2.0

### Fixed
- `summary.exit_code` on fatal-path JSON payloads: exit 2/3 used to report `exit_code: 0`
- JSON sort order: category-rank tiebreaker leaked from human report into JSON; sort functions now split (`_spec_sort_key` for JSON, `_human_sort_key` for report)
- README no longer claims PDF input acceptance (PDF input is a v1.0 plan)
- `MissingToolchain` fatal paths no longer emit a misleading "clean" summary line while exiting 3
- `_has_command` regex now accepts the optional-bracket argument form (`\chair[Co-chair]{Chair}`); pre-existing bug, masked until `\chair` joined `_REQUIRED_TOPLEVEL`
- `UF-F3` detector loop variable shadowed the outer `\documentclass` match, breaking UF-D3 when both fired on the same project; renamed `m` → `f3m`, regression test pinned

### Removed
- `docs/plans/` and `docs/design/`: internal planning artifacts stripped from history with `git-filter-repo`; both directories now gitignored

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

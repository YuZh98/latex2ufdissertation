# Changelog

All notable changes to this project will be documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · SemVer.

## [Unreleased]

### Added
- `docs/spec-v1.0.md`: v1.0 product specification (goal, scope, inputs, outputs, acceptance criteria)
- `docs/uf-rules.md`: canonical UF rule catalog (`UF-F1` … `UF-A2`) with citations and severity tiers
- `docs/json-schema.md`: authoritative JSON output schema reference (closes v1.0 acceptance gate 5)
- `latex2ufdissertation/pipeline/template/README.md`: provenance + re-sync procedure for the vendored UF template
- `examples/demo_dissertation/`: known-good dissertation satisfying every must-fix rule; committed `main.pdf` enables PDF-layer tests without a TeX install
- `examples/ufdissertation_samples/`: UF Graduate School Thesis & Dissertation Production samples (14 `.docx` files) as reference snapshots for rule-design tiebreakers; not wired into pytest
- `--demo` flag: prints the GitHub URL of the bundled demo (and local path for source checkouts)
- `latex2ufdissertation/pipeline/rules.py`: single-source-of-truth `Rule` dataclass + `RULES` dict for all 29 catalog entries
- `latex2ufdissertation/pipeline/report.py`: `format_human` (grouped + sorted) and `format_json` (JSON schema v1)
- `Finding` dataclass with eight v1 fields (`severity`, `rule_id`, `layer`, `location`, `observed`, `required`, `fix_hint`, `source_url`)
- `Issues.add(rule_id, ...)` resolves metadata from `RULES` so call sites stay terse
- `ConverterError` subclasses (`UnreadableInput`, `UnsupportedTemplate`, `ThesisInput`, `MissingToolchain`) with per-exception `exit_reason`
- Public API frozen via `__all__` in `latex2ufdissertation/__init__.py`
- Exit code `3` for missing toolchain; distinguishes environment failure from input failure
- `CONTRIBUTING.md`: engineering gates and committed-artifact policy
- `SECURITY.md`: vulnerability-reporting flow (GitHub Security Advisory)
- `CODE_OF_CONDUCT.md`: adapted from Contributor Covenant 2.1
- `.github/workflows/ci.yml`: pre-commit + Python 3.10–3.13 matrix on ubuntu + macOS spot-check + coverage gate
- `.pre-commit-config.yaml`: trailing-whitespace, EOF newline, merge-conflict, YAML/TOML syntax, 500 KB large-file blocker, `ruff` format + lint
- `.github/dependabot.yml`: weekly grouped minor/patch updates for pip and github-actions
- `.github/ISSUE_TEMPLATE/{bug_report,feature_request}.md` and `.github/PULL_REQUEST_TEMPLATE.md`
- README CI / license / Python-version badges
- Determinism pinning test: two `--dry-run --json` runs must produce byte-identical stdout
- Drift tests: catalog ↔ registry parity (ID, severity, layer)
- `tests/fixtures/` snapshot harness with per-rule `input/` + `expected_findings.json` + `expected_report.txt`; covered rules so far: `UF-D1`, `UF-D2`, `UF-D3` (D-series complete for source-layer detection), `UF-F5`, `UF-F8`, `UF-F13`, `UF-F14`, `UF-P1`
- `UF-D3` source detector for `overrideTitles` / `overrideChapters` `\documentclass` options (one finding per option present); registry gains a default fix_hint
- `UF-F14` detector extended from 4 to all 8 catalog-listed required metadata macros (`\degreeYear`, `\degreeMonth`, `\major`, `\chair` added). Closes #16. Tracking-bumped to a true 6/21 must-fix gate-1 coverage; previously was 5/21 + 1 partial.
- `UF-F14` value-constraint check: `\degreeMonth` must be `May` / `August` / `December` (case-sensitive, per catalog § UF-F14 / C2:41); any other value trips a must-fix finding citing the observed value.
- `UF-F5` source detector for `\justifying` / `\justify` text-alignment overrides per catalog § UF-F5. Negative-lookahead prevents false positives on `\justifyFoo` and avoids double-counting `\justifying`. Allowlist: `\sloppy` / `\sloppypar` (line-breaking helpers, catalog-explicit), `\raggedright` (template's own command). `\flushleft` mass-usage check deferred (catalog gives no numeric threshold). Registry gains default fix_hint citing template's `\raggedright` at cls:171.
- `tests/fixtures/uf_f14_missing_committee_metadata/`: broken-input fixture covering the 4 newly-checked macros (4 must-fix findings)
- D-series fixtures (`uf_d1_editmode`, `uf_d2_compiler_directive`, `uf_d3_override_options`) grow committee macros so each fixture is compile-ready end-to-end (no out-of-tree splice required to produce a PDF)
- `uf_d1_editmode` body grows `\authorRemark` / `\editorRemark` calls so the compiled PDF visibly demonstrates the consequence editMode enables (colored bold inline annotations); validator output unchanged
- `docs/uf-rules.md` § UF-F14 source citation rewritten to include S1 backing (previously C1-only, which describes class behavior but does not directly justify must-fix severity)
- 127 tests (was 14); coverage 74.65% (was 0%)

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
- `summary.exit_code` on fatal-path JSON payloads: previously derived from findings only, so exit 2/3 reported `exit_code: 0` in JSON
- JSON sort order: category-rank tiebreaker leaked into JSON; sort functions now split (`_spec_sort_key` for JSON, `_human_sort_key` for report)
- README no longer claims PDF input acceptance (PDF input is a v1.0 plan)
- `MissingToolchain` fatal paths no longer emit a misleading "clean" summary line while exiting 3
- `_has_command` regex now accepts the LaTeX optional-bracketed argument form (`\chair[Co-chair]{Chair}` per the UF template). Pre-existing bug, masked until `\chair` joined `_REQUIRED_TOPLEVEL`; without this fix the demo dissertation would trip a false-positive UF-F14

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

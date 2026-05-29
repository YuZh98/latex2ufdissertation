# Changelog

All notable changes to this project will be documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · SemVer.

## [Unreleased]

This release turns the v0.1 single-PR validator into a complete source-layer engine for the Fall 2025+ UF dissertation template. The validator now catches 18 of the 19 must-fix rules in the UF rule catalog before you click submit, ships a known-good demo project you can compile and read top-to-bottom, and emits machine-readable JSON for downstream tooling. JSON and human-readable report formats are both pinned by per-rule snapshot fixtures, so output regressions fail CI.

### Added

**UF rule coverage.** Source-layer detectors for 18 of the 19 must-fix rules in [`docs/uf-rules.md`](docs/uf-rules.md):

- D-series (document-class options): `UF-D1` (editMode), `UF-D2` (LuaLaTeX directive), `UF-D3` (overrideTitles / overrideChapters)
- F-series (formatting): `UF-F1` (margins), `UF-F2` (font family), `UF-F3` (font size 12pt), `UF-F4` (line spacing), `UF-F5` (ragged-right alignment), `UF-F6` (page numbering), `UF-F7` (paragraph indent), `UF-F8` (required `\set*File` macros), `UF-F9` (singleton sections), `UF-F10` (≥ 3 chapters), `UF-F11` (5-tier heading hierarchy), `UF-F13` (`\documentclass{ufdissertation}`), `UF-F14` (8 required metadata macros + `\degreeMonth` enum), `UF-F15` (abstract ≤ 350 words)
- P-series (filesystem): `UF-P1` (`\set*File` companion files exist on disk)
- S-series (semantics): `UF-S3` (broken `\ref` / `\cite` cross-references)

Only `UF-S1` (PDF output present, PDF-only) and `UF-S2` (catalog-marked redundant with F8) remain unimplemented. F1 / F2 / F4 / F6 ship source-halves only; PDF-layer backups defer to v1.0. Every detector ships a default `fix_hint`.

**Output formats.**

- `--json` emits the v1.0 JSON schema documented at [`docs/json-schema.md`](docs/json-schema.md). Schema version is mandatory, sort order is contractual, stdout is JSON-only (progress goes to stderr).
- Human-readable report groups findings by layer + rule category, tags each with severity (`must-fix` / `review`), rule ID, location, and a link back to the catalog entry.
- Two `--dry-run --json` runs produce byte-identical stdout (pinned by `tests/test_determinism.py`).

**New CLI surface.**

- `--demo` prints the location of the bundled demo dissertation (GitHub URL for installed copies; local path for source checkouts)
- Exit code `3` for missing toolchain — distinguishes "the project is broken" (`2`) from "this host is missing tools" (`3`)

**Reference material.**

- [`docs/spec-v1.0.md`](docs/spec-v1.0.md) — locked v1.0 product specification
- [`docs/uf-rules.md`](docs/uf-rules.md) — full UF rule catalog (`UF-F1` … `UF-A2`) with severity tiers and per-rule citations into the vendored class file
- [`docs/json-schema.md`](docs/json-schema.md) — JSON output schema reference (closes v1.0 acceptance gate 5)
- [`examples/demo_dissertation/`](examples/demo_dissertation/) — known-good dissertation that satisfies every must-fix rule, committed `main.pdf` included
- [`examples/ufdissertation_samples/`](examples/ufdissertation_samples/) — UF Graduate School's 14 docx samples (Title Page, Copyright, Abstract, ToC, etc.) as a tiebreaker reference when the catalog is ambiguous

**Public API contract.** `__all__` in `latex2ufdissertation/__init__.py` enumerates the stable surface for downstream integrations: `Finding`, `Issues`, `Rule`, `RULES`, `run_checks`, `ConverterError` and its subclasses (`UnreadableInput`, `UnsupportedTemplate`, `ThesisInput`, `MissingToolchain`), `__version__`.

**Test coverage.** 17 broken-input snapshot fixtures under `tests/fixtures/` pin both JSON and human-readable outputs byte-for-byte. 231 tests total (was 14 at v0.1.0); coverage 74.65 %.

**Project hygiene.** `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`; CI matrix (Python 3.10–3.13 on ubuntu + macOS spot-check); pre-commit hooks (ruff format + lint, large-file blocker, structural checks); weekly dependabot; issue + PR templates; README CI / license / Python-version badges.

### Changed

**Breaking — JSON output schema.** Old keys removed; new payload shape is `{schema_version, input, template_version, findings: [...], summary: {must_fix_count, review_count, exit_code, exit_reason}}`. Stdout is now JSON-only under `--json` (progress + per-finding lines moved to stderr).

**Breaking — public `Issues` API.** `Issues.warn()` / `Issues.error()` removed in favor of `Issues.add(rule_id=..., location=..., observed=..., required=..., fix_hint=...)`, which resolves severity / layer / source URL from `RULES[rule_id]` automatically. Stale fields `Issues.dry_run`, `Issues.output_path`, `Issues.compile_result` removed. `compile_pdf()` no longer takes an unused `issues` parameter.

**Severity tiers rebranded** from `error` / `warn` to `must-fix` / `review`. `UF-D2` (LuaLaTeX directive) promoted from `warn` to `must-fix` per the catalog.

**Docs.** README rewritten to distinguish shipping behavior from v1.0-planned features. `docs/uf-rules.md` citations reference the canonical vendored `ufdissertation.cls` (the demo's copy has a provenance-header offset and is no longer the citation target). `docs/uf-rules.md` § UF-F14 source citation gains S1 backing (previously C1-only).

**CI tightened.** Coverage floor raised 60 % → 70 % (actual 74.65 %). Determinism-strict pytest pass on the JSON output. Version bumped 0.1.0 → 0.2.0 (carries the breaking JSON + API changes).

### Fixed

- `summary.exit_code` on fatal-path JSON payloads previously reported `0` even when the process exited `2` or `3`
- JSON sort order: a category-rank tiebreaker meant for the human report leaked into JSON; sort functions now split (`_spec_sort_key` for JSON, `_human_sort_key` for report)
- README no longer claims PDF input acceptance (PDF input is a v1.0 plan)
- `MissingToolchain` fatal paths no longer emit a misleading "clean" summary while exiting `3`
- `_has_command` regex now accepts the LaTeX optional-bracket argument form (`\chair[Co-chair]{Chair}`); pre-existing bug, would have produced a demo-dissertation false positive once `\chair` joined the required-macros list
- UF-F3 detector loop variable shadowed the outer `\documentclass` match, silently breaking UF-D3 when both rules fired on the same project

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

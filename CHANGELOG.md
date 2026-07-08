# Changelog

All notable changes to this project will be documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · SemVer.

## [Unreleased]

### Added
- Add version-sync guard (`tests/test_version_sync.py`): asserts installed package metadata, `pyproject.toml` `[project].version`, and the CLI `--version` output all agree, so a stale editable install or an unrebuilt release can no longer silently ship a runtime version that diverges from source (#89)
- `review_present` exit reason: review-only runs report `exit_reason: "review_present"` instead of bare `clean` (exit code stays `0`) so the JSON verdict stops implying nothing needs attention (#91)
- UF-F10 `\includeonly` scan: a leftover `\includeonly` in the preamble raises a review finding warning it can silently drop chapters from the compiled PDF (#91)
- Compile-tool failure surfacing: non-zero `lualatex` (per pass) and `biber` exits now print a stderr warning instead of being swallowed (#91)

### Changed
- Spec: drop the planned old-template refusal (hard-rule 9). A class-file diff shows the Fall-2025+ template and the immediately-prior revision share an identical student-facing macro surface — only maintainer formatting internals differ — so both are supported and validated rather than refused; `template_version` stays `"unknown"` by design (the class carries no version marker) (#92)
- `UF-F3` (PDF layer) severity is now calibrated so `must-fix` means certain rejection: a deviating page is `must-fix` only when the document-wide modal body size is itself off 12pt (a global override) or the page's body text is larger than 12pt (never a float); an undersized page on an otherwise-12pt document (a `\footnotesize` table or `\small` figure sub-caption) is demoted to `review` and reported as figure/table-dominated text rather than "body text" (#82)
- UF-F10 and UF-S3 now walk the `\input`/`\include` graph through the same transitive corpus as the override scan, fixing a false-negative (chapters nested under a `\part` wrapper file went uncounted) and aligning all three rule families to one depth (#91)
- UF-F4 allowlist extended with `algorithm`, `algorithmic`, `lstlisting`, `quote`, `quotation` so single-spacing inside those environments no longer raises a false must-fix (#91)
- PDF-only input: the report relabels the "clean" verdict and adds a "source layer did not run" note so a skipped source layer is not mistaken for a passed one (#91)
- Severity guide wording softened from "must-fix = will cause UF Graduate School rejection" to "will likely cause": the tool checks a subset of requirements and cannot guarantee the editorial office's decision
- Human report redesigned for clarity and consistency (JSON output unchanged): findings are grouped by **severity** (must-fix, then review) instead of by layer, so a dual-layer rule (UF-F2/UF-F3) reads as adjacent uniform lines rather than appearing in two separate `[layer]` sections with different vocabulary. One line per finding (`UF-<rule>  <location>  <observed>`), so the section-header count equals the lines shown and the `Summary` reconciles exactly. Per-page collapsing (`pp.12-16 (N pages)`) is dropped; the per-finding `see: <url>` lines are removed; each rule group shows its fix hint once, condensed to a single line

### Removed
- Remove the vestigial `UnsupportedTemplate` exception (public API) and the `unsupported_template` `exit_reason` (JSON schema enum): both had no raise site and became dead when old-template refusal was dropped (#92). Neither was ever emitted, so no run output changes; the public export list and fatal-reason enum are now pinned by `tests/test_public_api.py` (#93)
- Remove the duplicate live per-finding diagnostic stream: `Issues.add` no longer prints each finding to stderr as it is discovered. The consolidated, layer-grouped report from `format_human` is now the sole rendering, so a finding is shown once instead of twice; phase progress lines (validating/compiling/using bundled PDF) are unchanged. The now-dead `emit_progress` toggle is removed
- Remove the standing PDF/UA accessibility advisory note (the "Advisory (not a finding)" block about the template's untagged PDFs) from the human report: it added noise without an action to take. The `UF-A1`/`UF-A2` rule definitions and their documentation are unchanged

### Security
- Zip extraction now caps total declared uncompressed size (200 MB) and member count (10,000) before writing any byte, closing a zip-bomb gap on both `.zip` inputs and the `--init` template extraction; a breach raises a fatal-input error (exit code 2) (#90)
- Master `.tex` auto-detection applies the same out-of-root containment guard as `--main`, so a symlink escaping the project root is no longer read (#90)
- `git clone` runs with stdin closed and `GIT_TERMINAL_PROMPT=0`, so a private or typo'd URL fails fast instead of hanging on a credential prompt (#90)

## [0.4.0] - 2026-06-11

`.tex` direct input mode; UF-S2 rejection-driver detector; consolidated per-page findings; report framing with severity guide and scope disclaimer. Test suite hardened with security regression pinning and mutation-derived killers.

### Added
- `UF-S2` detector: absent required rejection-driver section (Acknowledgements/Abstract/References/Biographical) raises `must-fix` alongside `UF-F8` (#79)
- `.tex` input mode: `latex2ufdissertation main.tex` treats the parent directory as project root when the file contains `\documentclass{ufdissertation}`; the named file is forced as the master (no auto-detect) (#80)
- Report framing: severity guide ("must-fix = rejection; review = discretionary") and scope disclaimer appended after the Summary line on every run (#80)
- "PDF layer did not run" note: appended on `--dry-run` or source-only runs (#80)
- Security/crash regression suite: corrupt-zip/bad-PDF exit codes, `--json`-always-parseable property, `\set*File` path-traversal, flag-injection filenames, LuaLaTeX env hardening, byte-identical `--json` determinism (#79)
- Mutation-killer tests: 25 surviving-mutant gaps closed across `resolve.py`, `pdf_checks.py`, and `cli.py` (#79)

### Changed
- Bundled-PDF message: shows the fully-resolved path and a stale-source caveat (#80)
- UF-A2 advisory: suppressed on `--dry-run` runs; appears only when the PDF layer ran (#80)
- UF-F2/UF-F3 human report: per-page findings consolidated into a single page-range line (e.g. `pp.3-12,14 (10 pages)`); JSON output unaffected (#80)
- `--dry-run` + `.pdf` input: emits a warning that the flag has no effect, then runs PDF checks (#80)
- `--help` input description: lists `.tex` and `.pdf` alongside `.zip`, directory, and git URL (#80)
- `--json` stderr: per-finding diagnostic stream suppressed; consolidated report still prints (#81)

## [0.3.2] - 2026-06-01

Hardening release covering security, crash-safety, validation soundness, and documentation honesty.

### Security
- Zip extraction is containment-checked (`is_relative_to`), fixing a sibling-prefix zip-slip bypass; the same guard now covers the `--init` remote-template fetch (previously unguarded `extractall`), with a 50 MB download cap (#66)
- Git-URL handling rewritten with `urlparse`: host is exact-matched against `{github.com, gitlab.com}`; rejects subdomain-prefix (`github.com.evil.com`), IP/IMDS literals, `http://`, and embedded userinfo (`evil.com@github.com`) (#66)
- LuaLaTeX compile hardened: `-no-shell-escape` plus restricted env (`shell_escape=f`, `openin_any=p`, `openout_any=p`) blocks `\write18` and `\input{/etc/passwd}` exfiltration; master filenames starting with `-` are rejected (flag injection). Compiling untrusted LaTeX is documented as unsafe — `\directlua` cannot be disabled (#66, SECURITY.md)
- `\set*File` / abstract / `\input` path resolution is confined to the project root; an absolute or `..`-traversal argument is no longer read and can no longer crash the tool (#70)

### Fixed
- Override scans (`UF-F1`/`F2`/`F3`/`F4`/`F5`/`F6`/`F7`/`F11`) now recurse through `\input`/`\include`; overrides placed in a preamble or chapter file are no longer missed (previously a clean report on a non-conforming document) (#68)
- Error paths now exit 2 with a clean message and valid `--json` instead of a traceback: corrupt zip, `--main` outside the project root, `--init` into an unwritable path, malformed/encrypted PDF (#66, #67, #70)
- `UF-F4` no longer false-fires on `\singlespacing` inside `longtable`/`itemize`/caption/table/figure scopes (#68)
- `UF-S3` now catches broken `\cref`/`\Cref`/`\autoref`/`\nameref` (#68)
- Verbatim blocks are stripped before comments, so a `%` inside `verbatim` no longer corrupts scanning (#68)
- `_find_bundled_pdf` searches the master's own directory, so a subdirectory master's bundled PDF is found (#67)
- `--version` reads the installed package metadata instead of a hardcoded (stale) string (#67)

### Added
- Thesis refusal: `\thesisType{Thesis}` exits 2 (`thesis_input`), implementing the spec hard rule (#68)
- An empty required `\set*File` companion (exists but blank) now produces a `review` finding (presence is not content) (#68)

### Changed
- Documentation reconciled with the implementation: template-version detection and `--guide` marked deferred/not-implemented; `pdfminer.six` described accurately as a required dependency (lazy-imported, not a stdlib-only install); the `must-fix` definition softened with `D2`/`F15`/`F11` caveats; `uf-rules.md` marks rules with no automated check; §8 gate status noted (#69)

## [0.3.1] - 2026-06-01

### Fixed
- Resolve `\set*File` / `\input` / bib / abstract companions and the LuaLaTeX compile working directory relative to the master `.tex`'s own directory, not the workspace root. A project whose master lives in a subdirectory (e.g. a repo with the dissertation under `src/`) no longer gets spurious `UF-P1` "file not found" findings or a failed compile, and lualatex `stdin` is detached so a missing-file prompt can't hang on a TTY (#63)

## [0.3.0] - 2026-06-01

### Added
- PDF validation layer (`pipeline/pdf_checks.py`): runs on a bundled or freshly-compiled PDF, and on `*.pdf` input (new `pdf` input mode, which skips the source layer). A per-page body-mode primitive (most-common glyph font/size, subset-prefix stripped) backs the rendered-output checks (#53)
- PDF-layer rules: `UF-S1` (PDF parses and has content), PDF-authoritative `UF-F2` (body-mode font outside the Times/Arial family) and `UF-F3` (body-mode size ≠ 12 pt), and `UF-S5` (review — fires when link annotations *and* the document outline are both absent, e.g. `\hypersetup{draft}` left on) (#53)
- `UF-A2`: standing accessibility advisory in the human report (the `ufdissertation` template emits untagged PDFs — informational, not a finding) (#53)
- `pdfminer.six` runtime dependency, lazy-imported so the source-only and `--dry-run` paths remain stdlib-only (#53)
- `release.yml`: pushing a `vX.Y.Z` tag publishes a GitHub Release with notes from the matching CHANGELOG section and the bundled demo PDF attached

### Changed
- `UF-F2` / `UF-F3`: the `must-fix` verdict now comes from the PDF layer (which sees the rendered result); the source-layer finding is demoted to `review`. A font/size override the template neutralizes no longer rejects a compliant dissertation (#40, #47)
- `UF-F5`: source scan retargeted from `\justifying` (undefined in this template — never compiles) to the compilable `\rightskip`-zero re-justification vector, so the source-layer check is sound (#53)
- JSON output: added `detected_mode` (`dir`/`zip`/`git`/`pdf`/`unknown`); `template_version` now emits `"unknown"` instead of `null` when undetectable — reconciles `format_json` with the locked `spec-v1.0.md §5` contract (#12)

### Fixed
- `UF-P1` / `UF-F8`: `_SETFILE_RULES` now covers all 8 `\set*File` macros (cls:540-596); optional macros (copyright, dedication, abbreviations, appendix) get the P1 companion-file check when present without firing a spurious F8 "not set" when absent (#20)
- `--init`: corrected the UF IT template download URL — the old `wp-content/uploads` path 404s; now fetches from the current helpdesk media path (#61)

## [0.2.0] - 2026-05-29

### Added
- Source-layer detectors: 18 of 19 must-fix rules (`UF-D1`–`D3`, `F1`–`F11`, `F13`–`F15`, `P1`, `S3`); `S1` (PDF-only) and `S2` (no-code-path) intentionally absent
- `UF-F14`: extended from 4 to all 8 required metadata macros; `\degreeMonth` enum constraint (May / August / December, case-sensitive) (#17)
- `tests/fixtures/` snapshot harness: per-rule `input/` + `expected_findings.json` + `expected_report.txt`; `LATEX2UFD_REGEN_FIXTURES=1` regen workflow; 231 tests total (#15)
- Drift tests: catalog ↔ registry parity (ID, severity, layer)
- Determinism test: two `--dry-run --json` runs must produce byte-identical stdout
- `latex2ufdissertation/pipeline/rules.py`: `Rule` dataclass + `RULES` registry for all 29 catalog entries
- `latex2ufdissertation/pipeline/report.py`: `format_human` (grouped + sorted) and `format_json` (JSON schema v1)
- `Finding` dataclass: 8 v1 fields (`severity`, `rule_id`, `layer`, `location`, `observed`, `required`, `fix_hint`, `source_url`)
- `ConverterError` subclasses (`UnreadableInput`, `UnsupportedTemplate`, `ThesisInput`, `MissingToolchain`): per-exception `exit_reason`
- `__all__` in `latex2ufdissertation/__init__.py`: public API surface defined
- `--demo` flag: prints GitHub URL of bundled demo; local path when run from source checkout
- Exit code `3`: missing-toolchain environment failure, distinct from exit `2` (input failure)
- `examples/demo_dissertation/`: known-good dissertation satisfying every must-fix rule; `main.pdf` committed for PDF-layer tests without TeX install
- `examples/ufdissertation_samples/`: 14 UF Graduate School docx samples as rule-design reference; not wired into pytest (#14)
- `docs/spec-v1.0.md`: v1.0 product specification
- `docs/uf-rules.md`: 29-rule UF catalog (`F1`–`F16`, `S1`–`S5`, `D1`–`D3`, `P1`, `J1`–`J2`, `A1`–`A2`) with citations and severity tiers
- `docs/json-schema.md`: JSON output schema reference (#11)
- `latex2ufdissertation/pipeline/template/README.md`: provenance and re-sync procedure for the vendored UF template
- CI (`ci.yml`): pre-commit + Python 3.10–3.13 matrix on Ubuntu + macOS spot-check + coverage gate
- `.pre-commit-config.yaml`: trailing whitespace, EOF newline, merge-conflict markers, YAML/TOML syntax, 500 KB large-file blocker, `ruff` format + lint
- `.github/dependabot.yml`: weekly grouped minor/patch updates for pip and github-actions
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue templates, PR template

### Changed
- JSON output schema (breaking): old keys removed; new payload `{schema_version, input, template_version, findings: [...], summary: {must_fix_count, review_count, exit_code, exit_reason}}`
- `Issues` API (breaking): `.warn()` / `.error()` removed in favor of `.add(rule_id=...)`; `.dry_run`, `.output_path`, `.compile_result` attributes removed
- `compile_pdf()` signature: dropped unused `issues` parameter
- Stdout / stderr split: progress and diagnostics routed to stderr so `--json` stdout stays a single JSON document
- Human-readable report: findings grouped by layer + rule category, tagged with severity, `UF-*` ID, location, source URL
- `UF-D2` severity: promoted from `warn` to `must-fix`
- `docs/uf-rules.md` citations: reference the canonical vendored `ufdissertation.cls`
- README: badges (CI, license, Python version); shipping behavior distinguished from v1.0-planned features
- Coverage floor: ratcheted 60% → 70% (actual 74.65%)
- Version: bumped 0.1.0 → 0.2.0

### Fixed
- `summary.exit_code` on fatal-path JSON: exit 2/3 previously reported `exit_code: 0`
- JSON sort order: category-rank tiebreaker leaked from human report into JSON; split into `_spec_sort_key` (JSON) and `_human_sort_key` (report)
- `MissingToolchain` fatal paths: no longer emit a misleading "clean" summary line on exit 3
- `_has_command` regex: now accepts optional-bracket argument form (`\chair[Co-chair]{Chair}`) (#17)
- `UF-F3` detector: loop variable `m` shadowed outer `\documentclass` match, breaking `UF-D3` when both fired on same file; renamed to `f3m` (#27)
- `resolve()`: zip-slip detection and git-clone failures now raise `UnreadableInput` so `summary.exit_reason` correctly reports `"unreadable_input"` instead of `"compile_failure"`
- All source-layer detectors: `lstlisting`, `minted`, `Verbatim`, `alltt`, `verbatim*` environments now stripped alongside `verbatim` before scanning, eliminating false positives from code-listing blocks
- `UF-F15`: abstract word count now excludes verbatim-environment content
- `UF-S3`: labels declared in transitively `\input`'d files (second level) are now collected; `\ref` to a label two hops from `main.tex` no longer fires a false-positive
- `UF-S3`: `\citep`, `\citet`, `\citealt`, `\citealp`, `\cite*`, and other natbib variants now checked for missing bib keys
- `UF-S3`: `@string`, `@preamble`, and `@comment` entries no longer harvested as citable keys; `\cite{JMLR}` with `@string{JMLR=...}` now correctly fires
- `UF-F10`: `\chapter*{...}` (starred form) now counted toward the 3-chapter minimum; verbatim blocks in included files no longer inflate the chapter count
- `UF-F2`: `\usepackage{pkg1,pkg2}` comma-separated form now detected; same forbidden package appearing in multiple `\usepackage` calls emits exactly one finding
- `UF-F7`: `observed` field now reflects the actual unit in source (e.g. `0em`) rather than the hardcoded placeholder `0pt`

### Removed
- `docs/plans/`, `docs/design/`: internal planning artifacts stripped from history; both directories now gitignored

## [0.1.0] - 2026-05-26

Initial release. One command validates and compiles UF dissertation / thesis projects against the new UF template.

### Added
- CLI: `latex2ufdissertation INPUT [OUTPUT.pdf] [--init|--dry-run|--main|--json|--version]`
- Source-level validation: 9 `error` + 2 `warn` findings against UF format rules (severity labels rebranded in [Unreleased])
- LuaLaTeX compile driver
- `--init` flag: scaffolds project from UF IT site; falls back to bundled template on network failure
- Input modes: `.zip` archive, project directory, git URL

[Unreleased]: https://github.com/YuZh98/latex2ufdissertation/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/YuZh98/latex2ufdissertation/compare/v0.3.2...v0.4.0
[0.3.2]: https://github.com/YuZh98/latex2ufdissertation/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/YuZh98/latex2ufdissertation/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/YuZh98/latex2ufdissertation/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/YuZh98/latex2ufdissertation/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/YuZh98/latex2ufdissertation/releases/tag/v0.1.0

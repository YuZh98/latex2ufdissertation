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

### Changed
- README rewritten to honestly distinguish v0.1 (shipping) from v1.0 (planned): advisory framing prominent up front, current v0.1 input modes (directory / zip / git URL), current v0.1 severity vocabulary (`error` / `warn`) with a forward pointer to the v1.0 rebrand, current four-code exit surface, and a `--dry-run` on-ramp for users without LuaLaTeX.
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

# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · SemVer.

## [Unreleased]

## [0.1.0] - 2026-05-26

Initial release. Validate + compile UF dissertation/thesis projects with the new UF template.

### Added
- CLI: `latex2ufdissertation INPUT [OUTPUT.pdf] [--init|--dry-run|--main|--json|--version]`
- Source-level validation: 9 errors + 2 warns against UF format rules
- LuaLaTeX compile driver
- `--init` scaffolds from UF IT site, falls back to bundled template
- Accepts zip / directory / git URL inputs

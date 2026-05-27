# Vendored UF dissertation template

The files in this directory are **not authored by the latex2ufdissertation project**. They are the LaTeX dissertation template maintained by the University of Florida Information Technology Help Desk for the UF Graduate School's Thesis and Dissertation Support Center, vendored into this package so that `latex2ufdissertation --init` can scaffold a new project without requiring an external download.

## Provenance

- **Source:** <https://it.ufl.edu/helpdesk/graduate-resources/ms-word--latex-templates/>
- **Distribution archive:** `Dissertation___Thesis_Example_File.zip` (downloaded from the page above)
- **Template generation:** Fall 2025
- **Example file last updated:** 2026-04-17

## Bundled files

| File | Role | Edited by this project? |
|---|---|---|
| `ufdissertation.cls` | Document class enforcing UF formatting rules | no |
| `exampleMasterFile.tex` | Reference student-facing master file | no |
| `ufdissertation-Doc-and-Troubleshooting.tex` / `.pdf` | UF's template documentation | no |
| `Images/` | Placeholder figures referenced by the example file | no |

All files are redistributed verbatim. A copy of `ufdissertation.cls` is also vendored at `tests/fixtures/demo_dissertation/ufdissertation.cls` so that the test fixture can compile standalone; that copy carries a 22-line provenance header at the top of the file but is otherwise identical to the canonical copy here.

## Maintenance

When UF publishes an updated template:

1. Re-download the distribution archive from the source URL above.
2. Replace the files in this directory with the new versions.
3. Also re-sync `tests/fixtures/demo_dissertation/ufdissertation.cls` (preserve its 22-line provenance header).
4. Re-verify the `C1:NNN` line-range citations in `docs/uf-rules.md` against the new `ufdissertation.cls`; update any that drifted.

## Rights

All rights to the UF dissertation template remain with the University of Florida. This project redistributes the files under the implicit permission of the UF IT page, which publishes them publicly for student use. If UF objects to redistribution, the canonical copy can be removed and `--init` can be made fetch-only.

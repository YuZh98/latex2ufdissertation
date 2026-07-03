# latex2ufdissertation v1.0 — Specification

Status: **draft**, locked sections marked.

This document defines what version 1.0.0 of latex2ufdissertation is and is not. Rules are split into **hard rules** (locked design decisions) and **soft rules** (temporary decisions subject to revision). Implementation details that don't change what the tool *is* belong in code, not here.

For the rule set the validator checks against, see [`uf-rules.md`](./uf-rules.md). For the known-good demo dissertation demonstrating compliance, see [`../examples/demo_dissertation/`](../examples/demo_dissertation/).

---

## 1. Goal (locked)

> **A safety-net validator for UF doctoral dissertations using the Fall 2025+ UF LaTeX template.** Given a project archive, project directory, or compiled PDF, the tool produces a grouped, severity-tiered report citing the originating UF rule for each finding, so a graduate student approaching the ETD deadline has one more pair of eyes before clicking submit.

The tool is **advisory**. The student remains responsible for the dissertation. The validator's job is to catch what a careful human checklist would, faster and more reliably under deadline pressure.

---

## 2. Scope (locked)

### In scope

- Doctoral dissertations using `\documentclass{ufdissertation}` (Fall 2025+ UF template, and the immediately-prior UF template revision it superseded). The two revisions share an **identical student-facing macro surface** — every `\set*File`, metadata macro, and `\thesisType` the validator keys on is defined the same in both; the differences are template-maintainer formatting internals (caption `labelsep`, TOC `\titlecontents` layout, `algorithm`/`natbib` package options) that do not affect any rule the validator checks. Both revisions are therefore supported (see hard-rule 9).
- Two-layer validation: LaTeX source + compiled PDF. The PDF layer uses `pdfminer.six`, which is **lazy-imported** so `--dry-run` and source-only execution paths do not import it at runtime; it is still a required install dependency listed in `[project] dependencies`. This is a deliberate, documented departure from the prior stdlib-only constraint.
- Four input modes: project zip, project directory, git URL, compiled PDF (PDF-only input mode)
- Compilation as a means to obtain the PDF when source input is given (utility, not headline feature)
- CLI as the engine
- Machine-readable JSON output for downstream tooling
- An ETD-upload walkthrough (`--guide` flag) summarizing the student's next steps in GIMS (**planned — not yet implemented; see §8 gate status**)

### Out of scope for v1.0

- Master's theses (deferred — same template, different `\thesisType`; revisit after v1.0)
- UF templates older than the immediately-prior revision (no such template has been compared against the rule set; support is not claimed and detection is not attempted)
- Tex cleanup, file pruning, or any Overleaf-export normalization (that's what `latex2arxiv` does for a different submission target)
- External URL liveness checking (network-dependent; reserved for a future `--check-links` opt-in)
- MCP server, browser extensions, editor extensions (extensions wrap the CLI but ship as separate artifacts; not gating for v1.0)
- Hosted web service or GUI

---

## 3. Users (locked)

The primary user is a UF doctoral student near a submission deadline who has already done their own manual formatting check and wants confidence that they have not missed something. Secondary users are advisors, departmental administrators, and CI configurations on thesis repositories.

The validator is **not** a substitute for the UF Graduate Editorial Office's review. It does not promise that a clean report means UF will accept the dissertation; it promises that a clean report means none of the documented mechanical formatting rules in [`uf-rules.md`](./uf-rules.md) were violated.

Some compliance dimensions are **unverifiable by either layer**, and a clean report does not speak to them: **content correctness** (a required section file that exists but is empty or a placeholder passes its presence check — presence is not content); **accessibility tagging** (the template emits untagged PDFs by construction, so tagged-structure, alt-text, and reading-order cannot be confirmed); **co-authorship and prior-publication facts** (journal-article rules depend on knowledge external to the project); and **source–PDF consistency** (the PDF layer validates whatever PDF it is given; a bundled PDF stale relative to the source is not detected — see §4).

---

## 4. Inputs (locked)

| Input | Detection | Source layer runs? | PDF layer runs? | Compile? |
|---|---|---|---|---|
| `*.zip` (project archive) | extension | yes | yes (on bundled PDF if present; otherwise on compiled output) | only if no PDF in archive |
| directory path | `path.is_dir()` | yes | yes (on bundled `main.pdf` if present; otherwise on compiled output) | only if no PDF in directory |
| `*.pdf` | extension | **skip + note in report** | yes | no |

Compile is invoked transparently when source-only input arrives without a bundled PDF. Compile failure is a fatal error (exit 2), not a finding — if the project does not compile, there is nothing meaningful for the PDF layer to inspect.

**Source-PDF consistency is not verified.** When a zip or directory input bundles both source and a compiled PDF, the source layer runs on the source and the PDF layer runs on the bundled PDF independently. The tool does not check that the PDF was compiled from the current source. A student who edited `.tex` after compiling and then bundled the outdated `.pdf` will see PDF-layer findings from the stale PDF. A `--recompile` flag that forces a fresh compile when both are present is reserved for v1.1 or later.

---

## 5. Outputs (locked)

### Human-readable report (default)

Grouped by rule category. Each finding includes:

- Severity tier (`must-fix` or `review`)
- UF rule ID (e.g. `UF-F1`)
- Location: file and line (source-layer) or page number (PDF-layer)
- Observed vs required
- Fix hint
- URL to the originating UF rule

### Machine-readable JSON (`--json`)

A versioned schema documented in [`json-schema.md`](./json-schema.md). Stdout is JSON only; progress goes to stderr. The schema includes:

- `schema_version`
- `input`: the input string passed to the CLI
- `detected_mode`: how the input was classified (`dir` / `zip` / `git` / `pdf` / `unknown`; `pdf` reserved for v1.0 PDF input)
- `template_version`: detected UF template version, or `"unknown"`. **Status: always `"unknown"` by design. The `ufdissertation` class carries no `\ProvidesClass` version/date string to detect from, and the supported template revisions are student-equivalent, so a reliable version is neither available nor needed; see hard-rule 9. The field is retained for forward compatibility.**
- `findings`: array of `{severity, rule_id, layer, location, observed, required, fix_hint, source_url}`
- `summary`: `{must_fix_count, review_count, exit_code, exit_reason}`

### Exit codes

- `0` — zero must-fix findings (review-only state still exits 0; review findings are advisory)
- `1` — at least one must-fix finding
- `2` — fatal: compile failure, unreadable input, master's thesis input (out-of-scope). **Note: there is no "unsupported template" exit-2 path — old-template refusal was dropped (hard-rule 9); the supported revisions are student-equivalent. A wrong `\documentclass` fires UF-F13 as exit 1. The `UnsupportedTemplate` exception type and the `unsupported_template` exit_reason are retained but reserved (never raised/emitted today).**
- `3` — missing required toolchain (e.g. no LuaLaTeX on `PATH`)

Exit code `2` is overloaded across several failure modes. Downstream scripts that need to distinguish them parse the stderr message (and the `summary.exit_reason` field in JSON output). Code `3` is kept separate so wrappers can distinguish "the project is broken" (2) from "the host machine is missing tools" (3) without parsing strings. Machine consumers thus see four states: succeed (`0`), fail validation (`1`), cannot proceed on this input (`2`), or cannot proceed in this environment (`3`).

---

## 6. Behavior (locked)

### Architecture

```
input ──► normalize ──► template-version detect ──►
   ├──► source layer (checks) ──┐
   └──► pdf layer    (checks) ──┴──► findings aggregator ──► report (human or JSON)
```

Input normalization produces a workspace containing project files and (where applicable) a PDF. Template-version detection is **not performed** — the class carries no version marker and the supported revisions are student-equivalent (see hard-rule 9); `template_version` always emits `"unknown"`. A wrong `\documentclass` is caught by the UF-F13 source check (exit 1), not by a pre-check exit 2; `\thesisType{Thesis}` triggers exit 2 before any other check fires (hard-rule 8 — implemented).

### Severity tiers (locked)

- **must-fix** — documented UF rule violation that the Editorial Office is expected to require fixing before acceptance. Contributes to exit code 1. A few must-fix rules rest on heuristics or soft sources (D2 reads the `% !TEX` hint rather than confirming the actual engine; F15's 350-word cap comes from the template file, not a UF web doc; F11 flags `\paragraph` per a template comment) — see soft-rules 12, 2, and 3 in §7.2 for the revisit conditions.
- **review** — likely issue requiring human judgment; tool flags, student decides. Does not contribute to exit code.

Two tiers only. No INFO / TIP / SUGGESTION / NIT. Adding more tiers dilutes the signal.

Standing, template-wide caveats (UF-A2 — e.g. the template's known accessibility limitations) are **not per-run findings**. They are static advisory text surfaced in the report preamble and documentation, outside the two-tier findings model. They therefore do not count toward acceptance gate §8.2 (zero findings on the demo) and do not affect exit codes.

### Offline by default

No check requires network access in the default code path. Future network-dependent checks must live behind opt-in flags.

### Determinism

Same input → same output. No timestamps, randomized check ordering, or system-state leaks in JSON output. Findings sort by `(layer, rule_id, location)`. Temporary paths produced by zip extraction are normalized to the input-relative form before emission so the JSON output does not leak system-dependent directories.

---

## 7. Rules to follow

### 7.1 Hard rules (locked design decisions)

1. **Two layers only.** Source-layer and PDF-layer. No third layer (no static analysis of the cls itself, no AST-based LaTeX understanding beyond what regex + lightweight parsing can do).
2. **Source layer is primary where it checks precisely; the PDF layer is authoritative where the template can override the student.** When a rule can be checked precisely at the source layer (geometry, page order, document-class options), that's where it lives, and the PDF layer is at most defense-in-depth. But for properties the template can **neutralize or re-assert** — font family above all (the class reloads `newtx` at `\begin{document}`, defeating a student font override so the body still renders Times), and the localized-vs-body case of font size — the source layer sees only *intent*, not the rendered result, and can flag a violation the template silently corrected. For these, the **PDF layer is authoritative for the must-fix verdict** and the source-layer finding is advisory (`review`). The two layers remain independent: the PDF layer does not suppress the source finding, and source–PDF consistency is not verified (§4).
3. **Template-enforced rules are checked by override-scan, not by re-implementation.** The `ufdissertation` class already enforces margins, fonts, spacing, alignment, page numbering, paragraph indent, page order, and heading styles. The validator looks for student-introduced overrides of those defaults, not for the rules themselves.
4. **Two severity tiers: must-fix and review.** No additional tiers.
5. **Exit codes: 0 / 1 / 2 / 3.** Clean / must-fix present / fatal for this input / fatal for this environment (missing toolchain). No other codes.
6. **Offline by default.** Any check that requires network sits behind an explicit opt-in flag, defaulting off.
7. **Determinism.** Same input → byte-identical JSON output. Same input → human-readable output identical except for any ANSI color codes when stdout is a TTY. The PDF layer must **ignore volatile PDF metadata** (`/CreationDate`, `/ModDate`, `/ID`, and timestamp fields of `/Producer`) and **normalize per-compile font subset prefixes** (the random `ABCDEF+` glyph-name prefix) before emission; otherwise findings would vary per compile. The `/Producer` *engine name* is stable and may be read (e.g. for UF-D2). For source input, the determinism guarantee is over the *findings*, not the compiled PDF bytes — recompiling the same source legitimately produces a different PDF (restamped timestamps, fresh subset prefixes), but the findings extracted from it are identical.
8. **Dissertation only.** Encountering `\thesisType{Thesis}` triggers exit 2 with a "master's theses are out of scope for v1.0" message.
9. **Supported template revisions are validated, not refused.** The Fall 2025+ `ufdissertation` template and the immediately-prior UF revision it superseded are both supported: the validator runs its full rule set against either. **Rationale:** a direct diff of the two class files shows an *identical student-facing macro surface* (every `\set*File`, metadata macro, and `\thesisType` is defined the same); the only differences are template-maintainer formatting internals (caption `labelsep`/`skip`, TOC `\titlecontents` layout, `algorithm`/`natbib` package options, heading casing) that no rule the validator checks depends on. A real old-template dissertation validates cleanly (only genuine content findings, no template artifacts). The class also carries no `\ProvidesClass` version/date string, so there is nothing reliable to detect a version from, and a student who relies on an installed/Overleaf class does not bundle it at all. Refusing an old-template project with exit 2 would therefore reject work the tool checks correctly, for no safety benefit. **The earlier plan to detect and refuse older templates is dropped.** `UnsupportedTemplate` and the `unsupported_template` exit_reason are retained as reserved names (no raise site) pending a possible removal in a later API-cleanup pass. Genuinely unrelated document classes are still caught by UF-F13 (exit 1).
10. **JSON schema is versioned and stable.** Once v1.0 ships, the JSON schema does not change without a major-version bump. Schema version field is mandatory.
11. **Public API is frozen at v1.0.** A documented export list enumerates every name downstream wrappers (Chrome extension, VS Code extension, CI integrations) may depend on. Anything not on that list is internal and may change without notice.

### 7.2 Soft rules (temporary, subject to revision)

These are decisions that are committed *for now* but may change before the v1.0 lock if evidence accumulates against them. Each is annotated with the trigger that would cause re-evaluation.

1. **UF-D1 `editMode` is a `review` finding, not `must-fix`.**
   *Revisit if:* the UF Graduate Editorial Office or Help Desk confirms that submissions with `editMode` on are formally rejected.

2. **UF-F15 abstract word cap is 350.**
   *Source:* the bundled template's own `abstractFile.tex` ("It should be 350 words or less"), not a UF web doc. *Revisit if:* UF Graduate Editorial Office publishes a different threshold, or confirms the 350-word cap is not actually enforced.

3. **UF-F11 `\paragraph` usage is flagged within F11, not as a separate must-fix.**
   *Revisit if:* `\paragraph` usage proves to be a common rejection driver, in which case it gets a dedicated rule ID.

4. **External URL liveness (UF-S4) is deferred entirely.**
   *Revisit if:* user feedback indicates broken external URLs are a meaningful rejection driver and an opt-in `--check-links` flag would be used.

5. **Journal-article-specific checks (UF-J1, UF-J2) are surfaced only in `--guide` output, not auto-detected.**
   *Revisit if:* a reliable discriminator for journal-article mode emerges (e.g., a UF-published class option).

6. **Solo-subsection detection (UF-F16) is `review`, not `must-fix`.**
   *Source:* the template's `chapter1.tex` instructs this in prose, but the UF web docs do not state it as a formal rejection rule. *Revisit if:* the Editorial Office confirms it as a formal rule.

7. **Output format is plain text by default; JSON is opt-in via `--json`.**
   *Revisit if:* significant downstream usage emerges and JSON-by-default becomes the more useful default.

8. **The validator runs all applicable checks every time; there is no `--only=<rule_id>` filter in v1.0.**
   *Revisit if:* run time becomes long enough that selective re-checking is needed.

9. **UF-F2 (font family) and UF-F3 (font size) fire as `review` at the source layer and `must-fix` at the PDF layer.** The source override-scan flags intent; the PDF layer adjudicates the rendered result (per §7.1.2). On `--dry-run` / PDF-absent paths, only the source-layer `review` is available.
   *Revisit if:* a source-only signal proves sound enough to carry the must-fix verdict without the PDF, or the PDF check proves too noisy to be must-fix.

10. **UF-F5 (alignment) is a `must-fix` at the source layer.** The originally-planned PDF right-edge check was deferred; the source scan was retargeted from `\justifying` (undefined in this template — never compiles) to the compilable `\rightskip`-zero re-justification vector (guarded against stretch-glue false positives), making the source check sound. A PDF right-edge distribution check remains a possible defense-in-depth addition in v1.1.
    *Revisit if:* the source scan produces false positives in practice, or the Editorial Office identifies a re-justification vector that does not manifest as `\rightskip`-zero in source.

11. **UF-S5 (hyperlink annotations) is implemented as `review` via PDF annotation/outline presence.** A conforming project (hyperref active) always emits link annotations and an outline; their absence (e.g. `\hypersetup{draft}` left on) is the signal.
    *Revisit if:* the Editorial Office confirms non-functional hyperlinks as a formal rejection driver (would argue for `must-fix`).

12. **UF-D2 (compiler) gains a PDF backup via the `/Producer` engine name.** The source layer reads the `% !TEX program` hint; the PDF layer can confirm the *actual* engine (`LuaTeX` vs `pdfTeX`; `xdvipdfmx` is ambiguous between XeLaTeX and LuaLaTeX-via-dvi).
    *Revisit if:* `/Producer` proves unreliable across TeX distributions.

---

## 8. Acceptance criteria for v1.0.0 (locked)

A release is v1.0.0 when **all** of the following hold:

1. Every `must-fix` rule in [`uf-rules.md`](./uf-rules.md) has at least one **sound** check in the codebase — one with no known false positive that flags conforming template output, and one that does not target a pattern which cannot occur in a compilable document. A check that can reject a compliant dissertation (e.g. a source-only font-override scan defeated by the template's `newtx` re-assertion) or that scans a non-compiling vector (e.g. `\justifying`, undefined in this template) does **not** satisfy this gate; the must-fix verdict for such a rule must come from the authoritative layer (per §7.1.2).
2. The known-good demo dissertation at `examples/demo_dissertation/` produces a report with zero must-fix and zero review findings. (Standing advisory notes such as UF-A2 are not findings — see §6 — and do not count.)
3. Each `must-fix` rule has at least one synthetic broken-input fixture in `tests/fixtures/` that triggers the rule and only that rule (or a documented set if the input naturally violates multiple).
4. All four input modes (`zip`, `dir`, `git`, `pdf`) are exercised in the test suite.
5. The JSON output schema is documented in `docs/json-schema.md` and version field is mandatory.
6. The public API is documented as a stable, enumerated export list.
7. The README states clearly that the tool is advisory and the student remains responsible.
8. PyPI classifier is `Development Status :: 5 - Production/Stable`.

These are gates, not aspirations. A release that misses any of them is not v1.0.0.

**Current gate status (pre-1.0):** Gates 1, 2, 5, 6, 7 are met; the following are the remaining gaps:

- **Gate 3** ("each must-fix rule has an isolating fixture"): one gap — UF-S2 (absent rejection-driver section) has a detector but no `tests/fixtures/uf_s2_*` fixture.
- **Gate 4** ("all four input modes exercised in tests"): `dir` and `pdf` run full validate cycles; `zip` and `git` are covered only by resolve/detection and error-path tests — no happy-path clone-or-extract → checks → report cycle.
- **Gate 8** (PyPI `Production/Stable`): `pyproject.toml` classifier is currently `4 - Beta`. Will be updated to `5 - Production/Stable` at the v1.0.0 release.

Hard-rule 9 is no longer a prerequisite for gates 1–3: old-template refusal was dropped, so those gates stand on the rule set alone.

Project-engineering gates (CI matrix, coverage threshold, pre-commit hook set, deprecation-strict pytest pass) are tracked in [`CONTRIBUTING.md`](../CONTRIBUTING.md), not here. Those are how the project is built; the criteria above are what v1.0 *is*.

---

## 9. What this document does not contain

- The UF rule set — see [`uf-rules.md`](./uf-rules.md).
- Implementation details (file structure, module layout, function signatures) — those belong in code.
- A roadmap from v0.x to v1.0 — irrelevant to what the tool *is*; the rules above are the destination.
- Marketing copy — the README handles that.

If a question arises about what the tool should be, it should be answerable from this document or from `uf-rules.md`. If it isn't, that's a spec gap and this document needs an update before code does.

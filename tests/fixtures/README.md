# Synthetic broken-input fixtures

Each subdirectory is a **fixture**: a minimal LaTeX project that violates exactly one UF rule (or a small documented set), paired with the canonical validator output for that input. These fixtures back v1.0 spec acceptance criterion 3 ("each `must-fix` rule has at least one synthetic broken-input fixture that triggers the rule and only that rule"), but are written for `review`-tier rules as well so the snapshot template is uniform.

## Layout

```
tests/fixtures/
  <rule_or_group_slug>/
    input/                       # the minimal project the validator runs against
      main.tex
      ack.tex                    # companion files matching \set*File macros so
      abs.tex                    # UF-F8 / UF-P1 do not fire on bare-bones inputs
      refs.bib
      bio.tex
    expected_findings.json       # `format_json(issues)` byte-for-byte
    expected_report.txt          # `format_human(issues)` byte-for-byte
```

Slug convention: `<rule_id_lowercase>_<short_keyword>`, e.g. `uf_d1_editmode`, `uf_d3_override_options`. Group fixtures (one input naturally violating multiple rules) use the group label, e.g. `uf_f_required_metadata`.

## How the snapshot harness works

`tests/test_fixtures.py` parameterizes over every subdirectory containing an `input/` folder. For each fixture it:

1. Builds an `Issues(input_path="<INPUT>")` collector with a stable placeholder for the `input` field (so the snapshot does not encode the absolute test path).
2. Runs `run_checks(input/main.tex, input/, issues)`.
3. Compares `format_json(issues)` against `expected_findings.json` (full dict equality after a rule-id pre-check).
4. Compares `format_human(issues)` against `expected_report.txt` (byte-for-byte).

Any mismatch fails the test and prints the regeneration command.

## Adding a new fixture

1. Create the directory: `tests/fixtures/<slug>/input/`.
2. Author `main.tex` plus companion `\set*File` targets (empty files are fine — the validator only checks existence, not content).
3. Decide what the rule *should* emit. If a detector already exists, regenerate snapshots:

       LATEX2UFD_REGEN_FIXTURES=1 pytest tests/test_fixtures.py

   If the detector does **not** yet exist (TDD red-then-green workflow), hand-write `expected_findings.json` and `expected_report.txt` so the failing snapshot describes the target output. The subsequent `feat:` commit then closes the gap; the snapshot is unchanged.

4. Inspect the regenerated / hand-written snapshots and commit them alongside the input.

## Regenerating after intentional output changes

The snapshot harness is strict by design: any change to field ordering, fix-hint wording, severity, or report formatting will fail the test. When the output change is intentional (e.g. a fix-hint rewrite landed in a separate PR), regenerate every fixture in one command:

    LATEX2UFD_REGEN_FIXTURES=1 pytest tests/test_fixtures.py

Review the diff to confirm only the expected changes landed before committing.

## Why both JSON and text snapshots

The JSON snapshot pins the machine-readable contract documented in `docs/json-schema.md`. The text snapshot pins the human-readable report — the format end users see when they run the CLI without `--json`. The two formatters sort findings differently (`docs/json-schema.md` § Determinism), so neither snapshot is derivable from the other; both are load-bearing.

## What these fixtures are not

- **Not exhaustive.** One fixture per rule is the v1.0 acceptance floor, not a ceiling. Variant inputs (e.g. multiple options on one `\documentclass` line, comment-stripped edge cases) belong in `tests/test_checks.py` as inline cases, not as additional fixture dirs.
- **Not real dissertations.** The `examples/demo_dissertation/` project is the known-good, end-to-end reference. Fixtures here are deliberately minimal: a fixture exercises one rule, not a dissertation.
- **Not stable under casual edits.** Snapshot tests fail loudly on output changes. That is the point. If a fixture trips you up after a deliberate change, regenerate; if it trips you up after an accidental one, that is the regression catcher doing its job.

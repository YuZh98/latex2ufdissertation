# JSON output schema (v1.0)

Stable contract for `latex2ufdissertation --json`. This document is the authoritative reference; the code in `latex2ufdissertation/pipeline/report.py` is the executable form.

A consumer that pins `schema_version == "1.0"` can rely on every shape below remaining backwards-compatible within the 1.x series. Additive fields (new optional keys) may appear in 1.1+; renames or removals require a 2.0 bump.

## Invocation

    latex2ufdissertation --json <input>

- **stdout** — exactly one JSON document, no leading or trailing noise. `json.dumps(..., sort_keys=True)` is applied so byte-identical runs are contractual.
- **stderr** — progress lines (`validating ...`, `compiling ...`), per-finding diagnostic lines, compile-error blocks, the `Summary:` line. Safe to discard or tee.

Pipe-friendly:

    latex2ufdissertation --json my-thesis/ | jq '.summary'

## Top-level shape

```json
{
  "schema_version": "1.0",
  "input": "my-thesis/",
  "template_version": "Fall 2025",
  "findings": [ /* zero or more Finding objects */ ],
  "summary": {
    "must_fix_count": 0,
    "review_count": 0,
    "exit_code": 0,
    "exit_reason": "clean"
  }
}
```

### Field reference

| Field | Type | Nullable | Description |
|---|---|---|---|
| `schema_version` | string | no | Always `"1.0"` within the v1.x series. Bump on breaking shape change only. |
| `input` | string | yes | The exact input string passed to the CLI (path, zip filename, or git URL). `null` only on fatal paths where the input was never resolved. |
| `template_version` | string | yes | Detected UF template version (e.g. `"Fall 2025"`). `null` when undetectable. |
| `findings` | array | no | Zero or more Finding objects. Empty array on clean runs and on fatal-input runs. |
| `summary` | object | no | See `summary` below. |

## Finding object

Each finding represents one UF rule violation. The eight fields are frozen at v1.0.

```json
{
  "severity": "must-fix",
  "rule_id": "UF-F5",
  "layer": "source",
  "location": "chapters/intro.tex:42",
  "observed": "\\raggedright not set",
  "required": "ragged-right alignment per UF-F5",
  "fix_hint": "Add \\raggedright in the preamble after \\begin{document}.",
  "source_url": "https://github.com/YuZh98/latex2ufdissertation/blob/main/docs/uf-rules.md#uf-f5--text-alignment-ragged-right"
}
```

| Field | Type | Nullable | Values |
|---|---|---|---|
| `severity` | string | no | `"must-fix"` or `"review"` |
| `rule_id` | string | no | UF rule identifier matching the catalog in `docs/uf-rules.md` (e.g. `"UF-F1"`, `"UF-S3"`, `"UF-A1"`) |
| `layer` | string | no | `"source"`, `"pdf"`, or `"both"` |
| `location` | string | no | File and line for source-layer findings (`"path/to/file.tex:LINE"`), page number for PDF-layer findings (`"page N"`), or empty string when no positional anchor applies |
| `observed` | string | yes | What the validator saw. `null` when the rule has no observable value (e.g. a missing-file finding) |
| `required` | string | yes | What the rule requires. `null` when not applicable |
| `fix_hint` | string | yes | One-line remediation. May be `null`. Per-finding hint overrides the rule-level default in `RULES[rule_id]` |
| `source_url` | string | no | Anchor link into `docs/uf-rules.md` for the originating rule |

### Severity contract

- `must-fix` — documented UF rule violation; submission would be rejected. Contributes to `must_fix_count` and trips `exit_code` 1.
- `review` — likely issue requiring human judgment. Contributes to `review_count` only; never trips a non-zero exit code on its own.

### Finding sort order

Findings are sorted by `(layer, rule_id, location)` ascending. This ordering is stable across runs and contractual — downstream diffs can rely on it.

The human-readable report uses a different ordering (category-rank tiebreaker for nicer headings); the JSON ordering is what consumers depend on.

## Summary object

```json
{
  "must_fix_count": 0,
  "review_count": 0,
  "exit_code": 0,
  "exit_reason": "clean"
}
```

| Field | Type | Description |
|---|---|---|
| `must_fix_count` | integer | Count of findings where `severity == "must-fix"` |
| `review_count` | integer | Count of findings where `severity == "review"` |
| `exit_code` | integer | The process exit code. Always matches the shell exit status |
| `exit_reason` | string | Stable enum identifying *why* the process exited (see below) |

### `exit_reason` enumeration

The reason an exit code was chosen. The mapping is closed: any unknown reason indicates a schema violation.

| `exit_reason` | `exit_code` | Meaning |
|---|---|---|
| `clean` | `0` | Zero must-fix findings. Review-only findings still report `clean`. |
| `must_fix_present` | `1` | At least one must-fix finding |
| `compile_failure` | `2` | LuaLaTeX compile failed; PDF layer cannot proceed |
| `unsupported_template` | `2` | Detected template predates Fall 2025 or is not the UF dissertation class |
| `unreadable_input` | `2` | Input path, zip, or git URL could not be read |
| `thesis_input` | `2` | Input is a master's thesis (`\thesisType{thesis}`); out of scope for v1.0 |
| `missing_toolchain` | `3` | Required external tool not on `PATH` (e.g. no LuaLaTeX) |

Consumers that need to distinguish failure modes should switch on `exit_reason`, not on `exit_code` alone — code `2` is intentionally overloaded across input-side fatal modes, and `exit_code` plus `exit_reason` together form the discriminating pair.

## Determinism

Two `--dry-run --json` runs against the same input must produce byte-identical stdout. The contract rests on three guarantees, each pinned by a test in `tests/test_determinism.py`:

1. `findings` sorted by `(layer, rule_id, location)`
2. Top-level dict serialized with `json.dumps(..., sort_keys=True)`
3. No timestamps, no random IDs, no environment-dependent strings in any field

If a future check needs a timestamp or environment string, it goes to stderr or to a separate non-JSON channel — never into the schema.

## Exit-code matrix

| `exit_code` | Stream | Meaning | When to act |
|---|---|---|---|
| `0` | stdout valid JSON | Clean or review-only | Ship it (or note review findings for human attention) |
| `1` | stdout valid JSON | Must-fix violations present | Block submission; fix findings |
| `2` | stdout valid JSON | Fatal on input — input cannot be processed | Diagnose with `exit_reason` |
| `3` | stdout valid JSON | Fatal on environment — host machine missing required tools | Install the toolchain; re-run |

On every exit code, stdout remains valid JSON conforming to this schema. There is no exit code under which stdout is partial or empty.

## Versioning policy

- **1.0 → 1.x (additive)**: new optional fields on `Finding`, `summary`, or top-level. New `exit_reason` values. Existing fields keep their type and meaning. Consumers parsing 1.0 keep working.
- **1.x → 2.0 (breaking)**: rename or remove a field, change a type, narrow an enum. Consumers must update.
- **`schema_version` is the only safe pin**. Do not pin on tool version (`__version__`); a patch release may bump tool version without touching the schema.

## Related

- [`spec-v1.0.md`](./spec-v1.0.md) §5 — output contract (locked)
- [`uf-rules.md`](./uf-rules.md) — full rule catalog, with anchors that `source_url` points into
- `latex2ufdissertation/pipeline/report.py` — `format_json` implementation
- `latex2ufdissertation/pipeline/types.py` — `Finding` and `Issues` dataclasses
- `latex2ufdissertation/pipeline/rules.py` — severity, layer, and `exit_reason` constants

## Summary

What does this PR change, and why? One or two sentences; details in the body below.

## Type of change

- [ ] `feat` — new feature or check
- [ ] `fix` — bug fix
- [ ] `schema` — JSON output schema change (breaking surface — needs version bump)
- [ ] `config` — CI, packaging, or build config
- [ ] `refactor` — internal change with no observable behavior difference
- [ ] `test` — tests only
- [ ] `docs` — docs only
- [ ] `chore` — housekeeping

## Behavior change

If this PR changes anything a user observes (CLI output, exit codes, JSON schema, flag behavior, rule firings), describe the before/after here.

## Test plan

- [ ] Existing tests still pass locally (`pytest`).
- [ ] New tests added covering the change (red → green for behavior changes).
- [ ] Demo dissertation at `examples/demo_dissertation/` still produces zero must-fix / zero review findings.
- [ ] If this touches a `must-fix` rule, a synthetic broken-input fixture demonstrates the rule fires (and only that rule).

## Spec / docs

- [ ] `docs/spec-v1.0.md` updated if a hard rule, soft rule, or acceptance criterion changed.
- [ ] `docs/uf-rules.md` updated if rule semantics, severity, or citations changed.
- [ ] `CHANGELOG.md` `[Unreleased]` entry added.

## Checklist

- [ ] PR title follows Conventional Commits (`feat:` / `fix:` / etc.).
- [ ] Commits squash to a clean history.
- [ ] No new dependencies (or, if added, justified in the PR body).

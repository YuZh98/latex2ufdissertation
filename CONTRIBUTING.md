# Contributing to latex2ufdissertation

This document describes how the project is built and what is expected of contributors. It is intentionally separate from the product specification (`docs/spec-v1.0.md`), which describes what the tool *is*.

## Engineering gates

All of the following must hold before any commit lands on `main`, and are gated in CI:

- **Python matrix.** CI runs the test suite on Python 3.10, 3.11, 3.12, and 3.13.
- **Coverage.** A CI gate enforces a coverage floor (currently 70%). The floor ratchets up with every PR that raises actual coverage; the target for v1.0 release is 85%.
- **Pre-commit.** The pre-commit hook set covers formatting, trailing whitespace, end-of-file newline, merge-conflict markers, and YAML/TOML syntax validity.
- **Deprecation-strict.** `pytest -W error::DeprecationWarning` passes. Run this locally before any major dependency bump.
- **Determinism pinning test.** `tests/test_determinism.py` runs the validator twice on the demo dissertation with `--json` (validate-only, the default) and asserts byte-identical stdout. Enforces the determinism behavior promised in the spec.

## What goes in committed artifacts

Commit messages, pull-request descriptions, the README, the CHANGELOG, and any documentation in the published package describe **what the change is and why**, not the workflow that produced it. Readers care about the change; tooling, branch history, and local-development scaffolding are not part of the change description.

Internal planning files, session logs, and scratch notes stay local — gitignore them rather than committing.

## Where rules live

- **Product surface** (what v1.0 is, what it does, what it refuses): `docs/spec-v1.0.md`.
- **UF rule catalog** (what the validator checks against): `docs/uf-rules.md`.
- **Engineering hygiene** (how the project is built, tested, released): this file.

If you find yourself adding a rule and aren't sure which file it belongs in, ask whether a downstream user of the tool needs to know it. If yes, it goes in the spec. If only contributors need to know it, it goes here.

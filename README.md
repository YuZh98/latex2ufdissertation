# latex2ufdissertation

Validate and compile UF Graduate School dissertations and theses.

## Install

    pip install latex2ufdissertation

## Quickstart

    latex2ufdissertation --init my-thesis/
    cd my-thesis/
    latex2ufdissertation .

The default command validates the project and compiles to PDF using LuaLaTeX (TeX Live 2025 required).

## Flags

| Flag | What it does |
|---|---|
| (no flag) | Validate + compile → emit PDF |
| `--init DIR` | Scaffold a new project at DIR |
| `--dry-run` | Validate only, skip compile |
| `--main FILE` | Override master `.tex` auto-detect |
| `--json` | Machine-readable summary on stdout |
| `--version` | Print version and exit |

## Validation (v0.1)

Errors block submission (exit 1); warnings are advisory (exit 0).

- E1–E9: required `\documentclass{ufdissertation}`, `\title`, `\author`, `\degreeType`, `\thesisType`, and four `\set*File` commands with their target files present
- W1: `editMode` option left on
- W2: non-LuaLaTeX compiler hint detected

## Status

v0.1 — targets the new UF template (Fall 2025+). MIT license.

"""latex2ufdissertation CLI entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from latex2ufdissertation import __version__
from latex2ufdissertation.pipeline.build import compile_pdf, lualatex_available
from latex2ufdissertation.pipeline.checks import run_checks
from latex2ufdissertation.pipeline.init import init_project
from latex2ufdissertation.pipeline.main_tex import detect_main_tex
from latex2ufdissertation.pipeline.resolve import resolve, stem_for_output
from latex2ufdissertation.pipeline.types import ConverterError, Issues


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="latex2ufdissertation",
        description="Validate and compile UF Graduate School dissertations/theses.",
    )
    p.add_argument("input", nargs="?", help="Input: .zip, directory, or git URL")
    p.add_argument("output", nargs="?", help="Output PDF path (optional)")
    p.add_argument("--init", metavar="DIR", help="Scaffold a new project at DIR")
    p.add_argument("--dry-run", action="store_true", help="Validate only, skip compile")
    p.add_argument("--main", metavar="FILE", help="Override master .tex auto-detect")
    p.add_argument(
        "--demo",
        action="store_true",
        help="Print the location of the bundled demo dissertation and exit",
    )
    p.add_argument(
        "--json",
        action="store_true",
        dest="json_out",
        help="Machine-readable summary on stdout",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"latex2ufdissertation {__version__}",
    )
    return p


def _emit_json(issues: Issues) -> None:
    payload = {
        "input": issues.input_path,
        "output": issues.output_path,
        "main_tex": issues.main_tex,
        "dry_run": issues.dry_run,
        "errors": issues.errors,
        "warnings": issues.warnings,
        "compile_result": issues.compile_result,
    }
    print(json.dumps(payload, indent=2))


def _summary(issues: Issues) -> None:
    n_err = len(issues.errors)
    n_warn = len(issues.warnings)
    print(f"\nSummary: {n_err} error(s), {n_warn} warning(s)")


def _resolve_output_path(input_str: str, root: Path, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    stem = stem_for_output(input_str, root)
    input_path = Path(input_str)
    if input_path.exists() and input_path.is_dir():
        return input_path / f"{stem}_ufdissertation.pdf"
    if input_path.exists() and input_path.suffix.lower() == ".zip":
        return input_path.parent / f"{stem}_ufdissertation.pdf"
    return Path.cwd() / f"{stem}_ufdissertation.pdf"


DEMO_GITHUB_URL = (
    "https://github.com/YuZh98/latex2ufdissertation/tree/main/examples/demo_dissertation"
)


def _print_demo_location() -> int:
    print("Bundled demo dissertation — a known-good UF project that")
    print("satisfies every must-fix rule. Read it top-to-bottom as a")
    print("teaching reference, or run the validator against it to see")
    print("what a clean report looks like.")
    print()
    print(f"  Browse on GitHub: {DEMO_GITHUB_URL}")
    # If running from a source checkout, surface the local path too.
    pkg_root = Path(__file__).resolve().parent.parent
    local = pkg_root / "examples" / "demo_dissertation"
    if local.is_dir():
        print(f"  Local path:       {local}")
        print()
        print(f"  Validate:         latex2ufdissertation --dry-run {local}")
    else:
        print()
        print("  To use locally, clone the repo or download the directory")
        print("  from GitHub. A `--demo DEST` copy mode is planned for v1.0.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    issues = Issues()

    if args.demo:
        return _print_demo_location()

    if args.init:
        try:
            init_project(Path(args.init))
            return 0
        except ConverterError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2

    if not args.input:
        print(
            "Error: INPUT required (use --init to scaffold a new project)",
            file=sys.stderr,
        )
        return 2

    issues.input_path = args.input
    issues.dry_run = args.dry_run

    try:
        root, cleanup = resolve(args.input)
    except ConverterError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    try:
        master = detect_main_tex(root, hint=args.main)
        issues.main_tex = str(master.relative_to(root))

        print(f"  validating {issues.main_tex}")
        run_checks(master, root, issues)

        if args.dry_run:
            _summary(issues)
            if args.json_out:
                _emit_json(issues)
            return 1 if issues.errors else 0

        if not lualatex_available():
            issues.error("lualatex not found — install TeX Live 2025")
            _summary(issues)
            if args.json_out:
                _emit_json(issues)
            return 3

        output = _resolve_output_path(args.input, root, args.output)
        issues.output_path = str(output)
        print(f"  compiling to {output}")
        pdf = compile_pdf(master, root, output, issues)
        if pdf is None:
            _summary(issues)
            if args.json_out:
                _emit_json(issues)
            return 1

        _summary(issues)
        if args.json_out:
            _emit_json(issues)
        return 1 if issues.errors else 0
    except ConverterError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    finally:
        cleanup()


if __name__ == "__main__":
    sys.exit(main())

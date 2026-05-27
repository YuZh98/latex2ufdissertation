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
from latex2ufdissertation.pipeline.report import exit_code, format_human, format_json
from latex2ufdissertation.pipeline.resolve import resolve, stem_for_output
from latex2ufdissertation.pipeline.rules import (
    EXIT_REASON_MISSING_TOOLCHAIN,
    EXIT_REASON_UNREADABLE_INPUT,
)
from latex2ufdissertation.pipeline.types import (
    ConverterError,
    Issues,
    MissingToolchain,
    UnreadableInput,
)


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
        help="Machine-readable summary on stdout (JSON schema v1)",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"latex2ufdissertation {__version__}",
    )
    return p


def _emit_json(issues: Issues) -> None:
    # sort_keys keeps byte-identical output across runs on the same input.
    print(json.dumps(format_json(issues), indent=2, sort_keys=True))


def _emit_report(issues: Issues, json_out: bool) -> None:
    """Emit the human report (always, to stderr) and optionally the JSON
    payload (to stdout). Keeping the human report on stderr means
    `--json | jq ...` works without any extra filtering, and the user
    still sees findings as they happen via Issues.add's diagnostic line.
    """
    print(format_human(issues), file=sys.stderr)
    if json_out:
        _emit_json(issues)


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

    try:
        root, cleanup = resolve(args.input)
    except UnreadableInput as e:
        issues.set_exit_reason(EXIT_REASON_UNREADABLE_INPUT)
        print(f"Error: {e}", file=sys.stderr)
        if args.json_out:
            _emit_json(issues)
        return 2
    except ConverterError as e:
        issues.set_exit_reason(e.exit_reason)
        print(f"Error: {e}", file=sys.stderr)
        if args.json_out:
            _emit_json(issues)
        return 2

    try:
        master = detect_main_tex(root, hint=args.main)
        issues.main_tex = str(master.relative_to(root))

        print(f"  validating {issues.main_tex}", file=sys.stderr)
        run_checks(master, root, issues)

        if args.dry_run:
            _emit_report(issues, args.json_out)
            return exit_code(issues)

        if not lualatex_available():
            issues.set_exit_reason(EXIT_REASON_MISSING_TOOLCHAIN)
            print("Error: lualatex not found — install TeX Live 2025", file=sys.stderr)
            # Skip the human report on fatal toolchain paths — a "clean"
            # summary alongside a fatal error is actively misleading.
            # JSON consumers still get the structured payload.
            if args.json_out:
                _emit_json(issues)
            return 3

        output = _resolve_output_path(args.input, root, args.output)
        print(f"  compiling to {output}", file=sys.stderr)
        try:
            compile_pdf(master, root, output)
        except MissingToolchain as e:
            issues.set_exit_reason(EXIT_REASON_MISSING_TOOLCHAIN)
            print(f"Error: {e}", file=sys.stderr)
            if args.json_out:
                _emit_json(issues)
            return 3

        _emit_report(issues, args.json_out)
        return exit_code(issues)
    except ConverterError as e:
        issues.set_exit_reason(e.exit_reason)
        print(f"Error: {e}", file=sys.stderr)
        if args.json_out:
            _emit_json(issues)
        return 2
    finally:
        cleanup()


if __name__ == "__main__":
    sys.exit(main())

"""latex2ufdissertation CLI entry point."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from latex2ufdissertation import __version__
from latex2ufdissertation.pipeline.build import compile_pdf, lualatex_available
from latex2ufdissertation.pipeline.checks import run_checks
from latex2ufdissertation.pipeline.init import init_project
from latex2ufdissertation.pipeline.main_tex import detect_main_tex, first_documentclass
from latex2ufdissertation.pipeline.report import exit_code, format_human, format_json
from latex2ufdissertation.pipeline.resolve import input_mode, resolve, stem_for_output
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

# _BUNDLED_PDF_NAMES lists the filenames tried when looking for a pre-compiled
# PDF in a zip / dir project root. The stem-match fallback is applied after
# these fixed names are exhausted (see _find_bundled_pdf).
_BUNDLED_PDF_NAMES = ("main.pdf",)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="latex2ufdissertation",
        description="Validate and compile UF Graduate School dissertations/theses.",
    )
    p.add_argument("input", nargs="?", help="Input: .zip, directory, .tex, .pdf, or git URL")
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


def _err(msg: str) -> None:
    """Write *msg* followed by a newline to stderr.

    Used for all CLI progress and error messages so the implementation
    stays consistent with project conventions for stderr output.
    """
    sys.stderr.write(msg + "\n")


def _emit_json(issues: Issues) -> None:
    # sort_keys keeps byte-identical output across runs on the same input.
    print(json.dumps(format_json(issues), indent=2, sort_keys=True))


def _emit_report(issues: Issues, json_out: bool) -> None:
    """Emit the human report (always, to stderr) and optionally the JSON
    payload (to stdout). Keeping the human report on stderr means
    `--json | jq ...` works without any extra filtering. Outside `--json`,
    the user also sees findings live via Issues.add's per-finding diagnostic
    line; under `--json` that live stream is suppressed (see
    Issues.emit_progress) so it does not duplicate this report on stderr.
    """
    _err(format_human(issues))
    if json_out:
        _emit_json(issues)


def _find_bundled_pdf(root: Path, main_tex: Path | None) -> Path | None:
    """Return a pre-compiled PDF from the project if one exists, else None.

    Search order:
    1. Fixed names in _BUNDLED_PDF_NAMES next to *main_tex* (master's dir).
    2. <main_tex_stem>.pdf next to *main_tex*.
    3. Fixed names in _BUNDLED_PDF_NAMES in *root* (only when master is in a subdir).
    4. <main_tex_stem>.pdf in *root*.

    Searching master's directory first ensures a PDF placed alongside the
    master (the common bundled-submission layout) is found even when root
    and master's parent differ.
    """
    master_dir = main_tex.parent if main_tex is not None else None

    # Pass 1: master's directory (skipped when master is at root level, or when
    # main_tex is None, to avoid redundant work in the common single-dir case).
    if master_dir is not None and master_dir != root:
        for name in _BUNDLED_PDF_NAMES:
            candidate = master_dir / name
            if candidate.is_file():
                return candidate
        candidate = master_dir / f"{main_tex.stem}.pdf"  # type: ignore[union-attr]
        if candidate.is_file():
            return candidate

    # Pass 2: project root.
    for name in _BUNDLED_PDF_NAMES:
        candidate = root / name
        if candidate.is_file():
            return candidate
    if main_tex is not None:
        candidate = root / f"{main_tex.stem}.pdf"
        if candidate.is_file():
            return candidate

    return None


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


def _run_project_validation(
    root: Path,
    hint: str | None,
    args: argparse.Namespace,
    issues: Issues,
    cleanup: Callable[[], None],
) -> int:
    """Run source-layer + optional PDF-layer checks on a resolved project root.

    ``hint`` is the --main override filename (or the .tex filename when the
    input was a bare .tex file); None triggers auto-detect.  ``cleanup`` is
    called in the finally block; pass ``lambda: None`` for directory inputs
    (no temp dir to remove).
    """
    try:
        master = detect_main_tex(root, hint=hint)
        try:
            issues.main_tex = str(master.relative_to(root))
        except ValueError:
            # Symlink mismatch (e.g. /var/... vs /private/var/...): fall back
            # to the full path so the JSON payload is still informative.
            issues.main_tex = str(master)

        _err(f"  validating {issues.main_tex}")
        run_checks(master, root, issues)

        if args.dry_run:
            _emit_report(issues, args.json_out)
            return exit_code(issues)

        # Per spec §4: prefer a bundled PDF (master's dir first, then root); compile only
        # when none is present. This preserves the student's own PDF when one
        # was submitted inside the archive and avoids a LuaLaTeX dependency on
        # CI / machines without TeX Live.
        produced_pdf = _find_bundled_pdf(root, master)
        if produced_pdf is not None:
            _err(
                f"  using bundled PDF {produced_pdf.resolve()} "
                "(may not reflect source edits since it was last compiled; "
                "delete it to force recompile)"
            )
        else:
            if not lualatex_available():
                issues.set_exit_reason(EXIT_REASON_MISSING_TOOLCHAIN)
                _err("Error: lualatex not found — install TeX Live 2025")
                # Skip the human report on fatal toolchain paths — a "clean"
                # summary alongside a fatal error is actively misleading.
                # JSON consumers still get the structured payload.
                if args.json_out:
                    _emit_json(issues)
                return 3

            output = _resolve_output_path(args.input, root, args.output)
            _err(f"  compiling to {output}")
            try:
                compile_pdf(master, output)
            except MissingToolchain as e:
                issues.set_exit_reason(EXIT_REASON_MISSING_TOOLCHAIN)
                _err(f"Error: {e}")
                if args.json_out:
                    _emit_json(issues)
                return 3
            produced_pdf = output

        try:
            from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks

            run_pdf_checks(produced_pdf, issues)
        except MissingToolchain as e:
            issues.set_exit_reason(EXIT_REASON_MISSING_TOOLCHAIN)
            _err(f"Error: {e}")
            if args.json_out:
                _emit_json(issues)
            return 3
        except UnreadableInput as e:
            issues.set_exit_reason(EXIT_REASON_UNREADABLE_INPUT)
            _err(f"Error: {e}")
            if args.json_out:
                _emit_json(issues)
            return 2

        _emit_report(issues, args.json_out)
        return exit_code(issues)
    except ConverterError as e:
        issues.set_exit_reason(e.exit_reason)
        _err(f"Error: {e}")
        if args.json_out:
            _emit_json(issues)
        return 2
    finally:
        cleanup()


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
    # Under --json the final report already prints to stderr; silence the live
    # per-finding diagnostic stream so it does not duplicate (and so a 13-page
    # F2 violation does not emit 13 lines that the consolidated report shows once).
    issues.emit_progress = not args.json_out

    if args.demo:
        return _print_demo_location()

    if args.init:
        # --init is a scaffolding operation with no validation state; there is
        # no exit_reason to populate, so --json emits nothing for this path.
        # The --json contract ("always a single JSON document on stdout")
        # applies to the validation/conversion flow below (after input is
        # resolved).
        try:
            init_project(Path(args.init))
            return 0
        except ConverterError as e:
            _err(f"Error: {e}")
            return 2
        except OSError as e:
            _err(f"Error: {e}")
            return 2

    if not args.input:
        # Pre-flight: no validation state exists yet; --json emits nothing here
        # (same scoping rationale as --init above).
        _err("Error: INPUT required (use --init to scaffold a new project)")
        return 2

    issues.input_path = args.input
    issues.detected_mode = input_mode(args.input)

    # PDF-input mode: single compiled PDF supplied directly. Skip source layer
    # and compile; run the PDF layer and emit the report. Handled before
    # resolve() because resolve() cannot produce a project directory from a bare
    # PDF — its contract is "project tree + cleanup" and does not apply here.
    if issues.detected_mode == "pdf":
        pdf_path = Path(args.input)
        if not pdf_path.exists() or not pdf_path.is_file():
            issues.set_exit_reason(EXIT_REASON_UNREADABLE_INPUT)
            _err(f"Error: input not found or not a file: {args.input}")
            if args.json_out:
                _emit_json(issues)
            return 2
        if args.dry_run:
            _err(
                "Warning: --dry-run has no effect with .pdf input "
                "(no source layer); running PDF checks."
            )
        _err("  source layer skipped (PDF-only input)")
        issues.source_layer_ran = False
        try:
            from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks

            run_pdf_checks(pdf_path, issues)
        except MissingToolchain as e:
            issues.set_exit_reason(EXIT_REASON_MISSING_TOOLCHAIN)
            _err(f"Error: {e}")
            if args.json_out:
                _emit_json(issues)
            return 3
        except UnreadableInput as e:
            issues.set_exit_reason(EXIT_REASON_UNREADABLE_INPUT)
            _err(f"Error: {e}")
            if args.json_out:
                _emit_json(issues)
            return 2
        _emit_report(issues, args.json_out)
        return exit_code(issues)

    # .tex input mode: the user passed a single master .tex file directly.
    # Only accepted when the file contains \documentclass{ufdissertation}
    # (i.e. is a real master, not a chapter or \input-ed fragment).
    p = Path(args.input)
    if p.suffix.lower() == ".tex" and p.is_file():
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            issues.set_exit_reason(EXIT_REASON_UNREADABLE_INPUT)
            _err(f"Error: cannot read {args.input}: {e}")
            if args.json_out:
                _emit_json(issues)
            return 2
        if first_documentclass(text) != "ufdissertation":
            issues.set_exit_reason(EXIT_REASON_UNREADABLE_INPUT)
            _err(
                f"Error: {args.input} is not a UF dissertation master "
                r"(no \documentclass{ufdissertation}); "
                "pass the project directory instead."
            )
            if args.json_out:
                _emit_json(issues)
            return 2
        # Accepted: dispatch like a directory with the .tex filename as hint.
        issues.detected_mode = "dir"
        root = p.parent.resolve()
        return _run_project_validation(root, p.name, args, issues, lambda: None)

    try:
        root, cleanup = resolve(args.input)
    except UnreadableInput as e:
        issues.set_exit_reason(EXIT_REASON_UNREADABLE_INPUT)
        _err(f"Error: {e}")
        if args.json_out:
            _emit_json(issues)
        return 2
    except ConverterError as e:
        issues.set_exit_reason(e.exit_reason)
        _err(f"Error: {e}")
        if args.json_out:
            _emit_json(issues)
        return 2

    return _run_project_validation(root, args.main, args, issues, cleanup)


if __name__ == "__main__":
    sys.exit(main())

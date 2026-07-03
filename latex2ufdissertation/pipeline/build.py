"""LuaLaTeX compile driver."""

import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

from latex2ufdissertation.pipeline.types import ConverterError, MissingToolchain

COMPILE_TIMEOUT = 600  # seconds
MAX_ERROR_BLOCKS = 5


def lualatex_available() -> bool:
    return shutil.which("lualatex") is not None


def biber_available() -> bool:
    return shutil.which("biber") is not None


def format_errors(log: str) -> str:
    """Extract `! ...` blocks paired with the next `l.NN` line. Cap at MAX_ERROR_BLOCKS."""
    blocks: list[str] = []
    lines = log.splitlines()
    i = 0
    while i < len(lines) and len(blocks) < MAX_ERROR_BLOCKS:
        if lines[i].startswith("!"):
            chunk = [lines[i]]
            for j in range(i + 1, min(i + 6, len(lines))):
                chunk.append(lines[j])
                if lines[j].startswith("l."):
                    break
            blocks.append("\n".join(chunk))
            i += len(chunk)
        else:
            i += 1
    return "\n\n".join(blocks)


def compile_pdf(
    main_tex: Path,
    output_pdf: Path,
    open_pdf: bool = True,
) -> Path | None:
    """Run LuaLaTeX (+ biber if needed) and copy the resulting PDF to output_pdf.

    Compilation runs in the master's own directory (``main_tex.parent``), not a
    detached project root, so ``\\input``/``\\include`` and the produced PDF
    resolve correctly even when the master lives in a subdirectory. ``stdin`` is
    detached (``DEVNULL``) so a missing-file prompt cannot block on a TTY.

    Security notes:
    - Filenames starting with ``-`` are rejected before subprocess invocation
      to prevent flag injection into lualatex/biber.
    - ``-no-shell-escape`` disables ``\\write18`` (shell escape).
    - The env vars ``shell_escape=f``, ``openin_any=p``, ``openout_any=p``
      restrict file read/write to the project tree.
    - ``\\directlua`` (LuaTeX built-in) cannot be disabled via env or flags;
      only compile sources you trust.
    """
    if not lualatex_available():
        raise MissingToolchain("lualatex not found — install TeX Live 2025")

    # Belt-and-suspenders: reject filenames that start with '-' to prevent
    # flag injection into lualatex/biber argv.
    if main_tex.name.startswith("-"):
        raise ConverterError("unsafe master filename")

    work_dir = main_tex.parent

    # Restrict shell/file ops as defence-in-depth.
    # shell_escape=f  → disables \write18 (belt-and-suspenders alongside -no-shell-escape)
    # openin_any=p    → restricts \input to files under the project tree
    # openout_any=p   → restricts \output (log, aux) to the project tree
    # Note: \directlua cannot be disabled here — trusted input only.
    compile_env = {
        **os.environ,
        "shell_escape": "f",
        "openin_any": "p",
        "openout_any": "p",
    }

    cmd = [
        "lualatex",
        "-no-shell-escape",
        "-interaction=nonstopmode",
        "-halt-on-error",
        main_tex.name,
    ]
    log_text = ""
    for pass_n in (1, 2, 3):
        try:
            r = subprocess.run(
                cmd,
                cwd=work_dir,
                timeout=COMPILE_TIMEOUT,
                capture_output=True,
                stdin=subprocess.DEVNULL,
                env=compile_env,
            )
            log_text = r.stdout.decode(errors="replace") + r.stderr.decode(errors="replace")
        except subprocess.TimeoutExpired as exc:
            raise ConverterError(f"lualatex timed out after {COMPILE_TIMEOUT}s") from exc

        # -halt-on-error governs fatal stops (and the "did not produce a PDF"
        # raise below covers the no-output case). LaTeX routinely returns
        # non-zero on mere warnings, so surface it without aborting the 3-pass
        # loop — a silently-swallowed non-zero can otherwise let a stale pass-1
        # PDF from a prior run pass as a successful build.
        if r.returncode != 0:
            print(
                f"Warning: lualatex pass {pass_n} exited {r.returncode} "
                "(continuing; check the .log for details)",
                file=sys.stderr,
            )

        if pass_n == 1 and biber_available():
            stem = main_tex.stem
            bcf = work_dir / f"{stem}.bcf"
            if bcf.exists():
                try:
                    biber_r = subprocess.run(
                        ["biber", stem],
                        cwd=work_dir,
                        capture_output=True,
                        timeout=COMPILE_TIMEOUT,
                        stdin=subprocess.DEVNULL,
                        env=compile_env,
                    )
                except subprocess.TimeoutExpired as exc:
                    raise ConverterError(f"biber timed out after {COMPILE_TIMEOUT}s") from exc
                # A swallowed non-zero biber exit ships a PDF with unresolved
                # [?]/[0] citation placeholders and no signal to the user.
                if biber_r.returncode != 0:
                    print(
                        f"Warning: biber exited {biber_r.returncode}; "
                        "citations may render as [?]/[0] placeholders in the PDF",
                        file=sys.stderr,
                    )

    produced = work_dir / f"{main_tex.stem}.pdf"
    if not produced.exists():
        formatted = format_errors(log_text)
        if formatted:
            print("\n--- last compile errors ---", file=sys.stderr)
            print(formatted, file=sys.stderr)
        raise ConverterError("lualatex did not produce a PDF")

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(produced, output_pdf)

    if open_pdf:
        try:
            webbrowser.open(output_pdf.as_uri())
        except Exception:
            pass

    return output_pdf

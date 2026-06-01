"""LuaLaTeX compile driver."""

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
    """
    if not lualatex_available():
        raise MissingToolchain("lualatex not found — install TeX Live 2025")

    work_dir = main_tex.parent
    cmd = ["lualatex", "-interaction=nonstopmode", "-halt-on-error", main_tex.name]
    log_text = ""
    for pass_n in (1, 2, 3):
        try:
            r = subprocess.run(
                cmd,
                cwd=work_dir,
                timeout=COMPILE_TIMEOUT,
                capture_output=True,
                stdin=subprocess.DEVNULL,
            )
            log_text = r.stdout.decode(errors="replace") + r.stderr.decode(errors="replace")
        except subprocess.TimeoutExpired as exc:
            raise ConverterError(f"lualatex timed out after {COMPILE_TIMEOUT}s") from exc

        if pass_n == 1 and biber_available():
            stem = main_tex.stem
            bcf = work_dir / f"{stem}.bcf"
            if bcf.exists():
                subprocess.run(
                    ["biber", stem],
                    cwd=work_dir,
                    capture_output=True,
                    timeout=COMPILE_TIMEOUT,
                    stdin=subprocess.DEVNULL,
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

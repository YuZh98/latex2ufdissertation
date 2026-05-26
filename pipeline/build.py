"""LuaLaTeX compile driver."""

import shutil
import subprocess
import webbrowser
from pathlib import Path

from pipeline.types import Issues

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
    root: Path,
    output_pdf: Path,
    issues: Issues,
    open_pdf: bool = True,
) -> Path | None:
    """Run LuaLaTeX (+ biber if needed) and copy the resulting PDF to output_pdf."""
    if not lualatex_available():
        issues.error("lualatex not found — install TeX Live 2025")
        return None

    cmd = ["lualatex", "-interaction=nonstopmode", "-halt-on-error", main_tex.name]
    log_text = ""
    for pass_n in (1, 2, 3):
        try:
            r = subprocess.run(cmd, cwd=root, timeout=COMPILE_TIMEOUT, capture_output=True)
            log_text = r.stdout.decode(errors="replace") + r.stderr.decode(errors="replace")
        except subprocess.TimeoutExpired:
            issues.error(f"lualatex timed out after {COMPILE_TIMEOUT}s")
            return None

        if pass_n == 1 and biber_available():
            stem = main_tex.stem
            bcf = root / f"{stem}.bcf"
            if bcf.exists():
                subprocess.run(
                    ["biber", stem],
                    cwd=root,
                    capture_output=True,
                    timeout=COMPILE_TIMEOUT,
                )

    produced = root / f"{main_tex.stem}.pdf"
    if not produced.exists():
        issues.error("lualatex did not produce a PDF")
        formatted = format_errors(log_text)
        if formatted:
            print("\n--- last compile errors ---")
            print(formatted)
        return None

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(produced, output_pdf)
    issues.compile_result = {"pdf": str(output_pdf), "passes": 3}

    if open_pdf:
        try:
            webbrowser.open(output_pdf.as_uri())
        except Exception:
            pass

    return output_pdf

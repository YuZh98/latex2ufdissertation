"""v0.1 validation rules for UF dissertations/theses."""

import re
from pathlib import Path

from pipeline.types import Issues

_DOCCLASS_RE = re.compile(r"\\documentclass(\[([^\]]*)\])?\{([^}]+)\}")
_REQUIRED_TOPLEVEL = (
    (r"\title", r"\title is required"),
    (r"\author", r"\author is required"),
    (r"\degreeType", r'\degreeType is required (e.g. "Doctor of Philosophy")'),
    (r"\thesisType", r"\thesisType is required (Dissertation or Thesis)"),
)
_SETFILE_RULES = (
    (r"\setAcknowledgementsFile", (".tex",), "Acknowledgements"),
    (r"\setAbstractFile", (".tex",), "Abstract"),
    (r"\setReferenceFile", (".bib",), "Reference"),
    (r"\setBiographicalFile", (".tex",), "Biographical"),
)


def _strip_comments(text: str) -> str:
    return re.sub(r"(?m)(?<!\\)%[^\n]*", "", text)


def _has_command(nc: str, cmd: str) -> bool:
    pat = re.escape(cmd) + r"\s*\{[^}]*\S[^}]*\}"
    return re.search(pat, nc) is not None


def _setfile_arg(nc: str, cmd: str) -> str | None:
    pat = re.escape(cmd) + r"\s*\{([^}]+)\}"
    m = re.search(pat, nc)
    return m.group(1) if m else None


def run_checks(main_tex: Path, root: Path, issues: Issues) -> None:
    raw = main_tex.read_text(encoding="utf-8", errors="replace")
    nc = _strip_comments(raw)

    # E1: documentclass must be ufdissertation
    m = _DOCCLASS_RE.search(nc)
    if not m or m.group(3) != "ufdissertation":
        issues.error(r"wrong document class — UF requires \documentclass{ufdissertation}")

    # E2–E5: required top-level commands
    for cmd, msg in _REQUIRED_TOPLEVEL:
        if not _has_command(nc, cmd):
            issues.error(msg)

    # E6–E9: \set*File commands + target file existence
    for cmd, suffixes, label in _SETFILE_RULES:
        arg = _setfile_arg(nc, cmd)
        if arg is None:
            issues.error(f"{label} file required ({cmd} not set)")
            continue
        candidates = [root / arg] + [root / f"{arg}{s}" for s in suffixes]
        if not any(c.exists() for c in candidates):
            issues.error(
                f"{label} file required ({cmd}: {arg!r} not found in project root)"
            )

    # W1: editMode option
    if m and m.group(2) and "editMode" in m.group(2):
        issues.warn("editMode option set — remove before final submission")

    # W2: non-LuaLaTeX compiler hint
    if re.search(r"%\s*!TEX\s+program\s*=\s*(pdflatex|xelatex)", raw):
        issues.warn("UF requires LuaLaTeX — pdflatex/xelatex hint detected")

"""Source-layer validation checks for UF dissertations.

Each emit site calls `issues.add(rule_id="UF-XYZ", ...)`. Severity,
layer, source_url, and default fix_hint come from the rule registry
(rules.py). This module never decides "must-fix vs review"; that's the
registry's job.
"""

from __future__ import annotations

import re
from pathlib import Path

from latex2ufdissertation.pipeline.types import Issues

_DOCCLASS_RE = re.compile(r"\\documentclass(\[([^\]]*)\])?\{([^}]+)\}")
_REQUIRED_TOPLEVEL = (
    (r"\title", r"\title"),
    (r"\author", r"\author"),
    (r"\degreeType", r"\degreeType"),
    (r"\thesisType", r"\thesisType"),
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
    rel = str(main_tex.relative_to(root)) if main_tex.is_relative_to(root) else main_tex.name

    # UF-F13: documentclass must be ufdissertation
    m = _DOCCLASS_RE.search(nc)
    if not m or m.group(3) != "ufdissertation":
        observed = m.group(3) if m else "(no \\documentclass found)"
        issues.add(
            "UF-F13",
            location=rel,
            observed=f"\\documentclass{{{observed}}}",
            required="\\documentclass{ufdissertation}",
        )

    # UF-F14: required metadata macros (\title, \author, \degreeType, \thesisType)
    for cmd, label in _REQUIRED_TOPLEVEL:
        if not _has_command(nc, cmd):
            issues.add(
                "UF-F14",
                location=rel,
                observed=f"{label} missing or empty",
                required=f"{label}{{...}} with a non-empty argument",
            )

    # UF-F8 / UF-P1: \set*File macros + filesystem companions
    for cmd, suffixes, label in _SETFILE_RULES:
        arg = _setfile_arg(nc, cmd)
        if arg is None:
            issues.add(
                "UF-F8",
                location=rel,
                observed=f"{cmd} not set",
                required=f"{cmd}{{<{label.lower()}-file-stem>}}",
            )
            continue
        candidates = [root / arg] + [root / f"{arg}{s}" for s in suffixes]
        if not any(c.exists() for c in candidates):
            issues.add(
                "UF-P1",
                location=rel,
                observed=f"{cmd}{{{arg!r}}} but no file found in project root",
                required=f"{arg} (or {arg}{suffixes[0]}) exists in project root",
            )

    # UF-D1: editMode option (review tier — submission should not ship with it)
    if m and m.group(2) and "editMode" in m.group(2):
        issues.add(
            "UF-D1",
            location=rel,
            observed="editMode option present in \\documentclass",
            required="editMode removed before submission",
        )

    # UF-D2: non-LuaLaTeX compiler hint
    hint = re.search(r"%\s*!TEX\s+program\s*=\s*(pdflatex|xelatex)", raw)
    if hint:
        issues.add(
            "UF-D2",
            location=rel,
            observed=f"% !TEX program = {hint.group(1)}",
            required="% !TEX program = lualatex (or omit the directive)",
        )

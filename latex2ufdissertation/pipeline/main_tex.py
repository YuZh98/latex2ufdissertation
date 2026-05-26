"""Auto-detect the master .tex of a UF dissertation project."""

import re
from pathlib import Path

from latex2ufdissertation.pipeline.types import ConverterError

_FIRST_DOCCLASS = re.compile(r"(?m)^\s*\\documentclass(\[[^\]]*\])?\{([^}]+)\}")
_SETFILE_RE = re.compile(r"\\set[A-Z][A-Za-z]*File\b")


def _strip_comments(text: str) -> str:
    return re.sub(r"(?m)(?<!\\)%[^\n]*", "", text)


def _score(path: Path) -> int | None:
    """Return a master-score for `path` or None if no real \\documentclass present.

    Only the FIRST \\documentclass line counts — later occurrences are typically
    in \\verb / verbatim blocks inside documentation files.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    nc = _strip_comments(text)
    m = _FIRST_DOCCLASS.search(nc)
    if not m:
        return None
    score = len(_SETFILE_RE.findall(nc))
    if m.group(2).strip() == "ufdissertation":
        score += 100
    return score


def detect_main_tex(root: Path, hint: str | None = None) -> Path:
    if hint:
        p = root / hint
        if not p.exists():
            raise ConverterError(f"--main file not found: {hint}")
        return p

    candidates: list[tuple[Path, int]] = []
    for p in root.rglob("*.tex"):
        s = _score(p)
        if s is not None:
            candidates.append((p, s))

    if not candidates:
        raise ConverterError(r"no .tex file with \documentclass{...} found")

    candidates.sort(key=lambda x: (-x[1], len(str(x[0]))))
    return candidates[0][0]

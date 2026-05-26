"""Auto-detect the master .tex of a UF dissertation project."""

import re
from pathlib import Path

from pipeline.types import ConverterError

_DOCCLASS_UFD = re.compile(r"(?m)^\s*\\documentclass(\[[^\]]*\])?\{ufdissertation\}")
_SETFILE_RE = re.compile(r"\\set[A-Z][A-Za-z]*File\b")


def _strip_comments(text: str) -> str:
    return re.sub(r"(?m)(?<!\\)%[^\n]*", "", text)


def _is_ufd_master(path: Path) -> tuple[bool, int]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False, 0
    nc = _strip_comments(text)
    if not _DOCCLASS_UFD.search(nc):
        return False, 0
    return True, len(_SETFILE_RE.findall(nc))


def detect_main_tex(root: Path, hint: str | None = None) -> Path:
    if hint:
        p = root / hint
        if not p.exists():
            raise ConverterError(f"--main file not found: {hint}")
        return p

    candidates: list[tuple[Path, int]] = []
    for p in root.rglob("*.tex"):
        ok, score = _is_ufd_master(p)
        if ok:
            candidates.append((p, score))

    if not candidates:
        raise ConverterError(
            r"no master .tex with \documentclass{ufdissertation} found"
        )

    candidates.sort(key=lambda x: (-x[1], len(str(x[0]))))
    return candidates[0][0]

"""Auto-detect the master .tex of a UF dissertation project."""

import re
from pathlib import Path

from latex2ufdissertation.pipeline.types import UnreadableInput

_FIRST_DOCCLASS = re.compile(r"(?m)^\s*\\documentclass(\[[^\]]*\])?\{([^}]+)\}")
_SETFILE_RE = re.compile(r"\\set[A-Z][A-Za-z]*File\b")


def _strip_comments(text: str) -> str:
    return re.sub(r"(?m)(?<!\\)%[^\n]*", "", text)


def first_documentclass(text: str) -> str | None:
    """Return the class name of the FIRST (line-start, non-commented)
    ``\\documentclass`` in *text*, stripped of surrounding whitespace, or
    None if there is none. Optional ``[options]`` are ignored. This is the
    single source of truth for "what document class does this file declare";
    both master auto-detection (_score) and the bare-.tex input gate in
    cli.main use it so the two never drift.
    """
    m = _FIRST_DOCCLASS.search(_strip_comments(text))
    return m.group(2).strip() if m else None


def _score(path: Path) -> int | None:
    """Return a master-score for `path` or None if no real \\documentclass present.

    Only the FIRST \\documentclass line counts — later occurrences are typically
    in \\verb / verbatim blocks inside documentation files.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    cls = first_documentclass(text)
    if cls is None:
        return None
    score = len(_SETFILE_RE.findall(_strip_comments(text)))
    if cls == "ufdissertation":
        score += 100
    return score


def _reject_dash_name(p: Path, label: str) -> None:
    """Raise UnreadableInput when *p*'s filename starts with '-'.

    A leading dash is a subprocess-flag-injection vector: any tool that
    passes the path to an external command without '--' separation could
    treat it as a flag.  We reject early with a clear message.
    """
    if p.name.startswith("-"):
        raise UnreadableInput(f"master .tex filename must not start with '-': {label!r}")


def detect_main_tex(root: Path, hint: str | None = None) -> Path:
    if hint:
        p = root / hint

        # Path-escape guard: resolve both sides so symlinks don't deceive the
        # check, but return the unresolved path so callers get a stable value
        # relative to root (mirrors what rglob would return).
        if not p.resolve().is_relative_to(root.resolve()):
            raise UnreadableInput(f"--main path is outside the project root: {hint!r}")
        if not p.is_file():
            raise UnreadableInput(f"--main file not found or is not a file: {hint!r}")
        _reject_dash_name(p, hint)
        return p

    candidates: list[tuple[Path, int]] = []
    for p in root.rglob("*.tex"):
        # Skip files whose names start with '-' to avoid flag-injection in
        # downstream subprocess calls.
        if p.name.startswith("-"):
            continue
        s = _score(p)
        if s is not None:
            candidates.append((p, s))

    if not candidates:
        raise UnreadableInput(r"no .tex file with \documentclass{...} found")

    candidates.sort(key=lambda x: (-x[1], len(str(x[0]))))
    return candidates[0][0]

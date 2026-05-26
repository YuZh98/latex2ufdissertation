# latex2ufdissertation v0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a working CLI `latex2ufdissertation` that scaffolds, validates, and compiles UF dissertations/theses to PDF.

**Architecture:** Single Python package with one CLI entry (`converter.py`) and a `pipeline/` subpackage holding focused modules: `types`, `resolve`, `main_tex`, `checks`, `init`, `build`. Stdlib-only runtime; pytest for tests. Mirrors latex2arxiv's shape where it transfers; fresh code where the UF problem differs.

**Tech Stack:** Python 3.10+, stdlib only at runtime, `pytest` + `ruff` for dev. LuaLaTeX (TeX Live 2025) called via `subprocess`.

---

## File structure

```
latex2ufdissertation/
├── converter.py
├── pipeline/
│   ├── __init__.py
│   ├── types.py
│   ├── resolve.py
│   ├── main_tex.py
│   ├── checks.py
│   ├── init.py
│   ├── build.py
│   └── template/                       # bundled fallback template
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_types.py
│   ├── test_resolve.py
│   ├── test_main_tex.py
│   ├── test_checks.py
│   ├── test_init.py
│   ├── test_build.py
│   ├── test_converter.py
│   └── fixtures/
│       ├── 01-minimal-valid/
│       ├── 02-missing-required/
│       └── 03-editmode-still-on/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── LICENSE
└── .gitignore                          # already exists
```

Each module has one responsibility. `converter.py` orchestrates only — no business logic.

---

## Task 1: Package scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `LICENSE`
- Create: `README.md`
- Create: `CHANGELOG.md`
- Create: `latex2ufdissertation/__init__.py` — wait, package layout decision below.

**Package layout decision:** single-package, top-level (matches latex2arxiv shape):
- `converter.py` at repo root (entry point)
- `pipeline/` at repo root (package)
- No outer `latex2ufdissertation/` directory.
- pyproject `[project.scripts]` maps `latex2ufdissertation = "converter:main"`.

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "latex2ufdissertation"
version = "0.1.0"
description = "Validate and compile UF Graduate School dissertations and theses"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [{name = "Yu (Hugh) Zheng", email = "hugh.stats@gmail.com"}]
keywords = ["latex", "dissertation", "thesis", "uf", "university-of-florida", "lualatex"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Scientific/Engineering",
    "Topic :: Text Processing :: Markup :: LaTeX",
]
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=7", "ruff>=0.6", "pytest-cov"]

[project.scripts]
latex2ufdissertation = "converter:main"

[project.urls]
Homepage = "https://github.com/YuZh98/latex2ufdissertation"
Issues = "https://github.com/YuZh98/latex2ufdissertation/issues"

[tool.setuptools]
py-modules = ["converter"]

[tool.setuptools.packages.find]
include = ["pipeline*"]

[tool.setuptools.package-data]
"pipeline" = ["template/**/*"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP"]
```

- [ ] **Step 2: Write `LICENSE`** (MIT, year 2026, author "Yu (Hugh) Zheng")

- [ ] **Step 3: Write `README.md` stub**

```markdown
# latex2ufdissertation

Validate and compile UF Graduate School dissertations and theses.

## Install

    pip install latex2ufdissertation

## Quickstart

    latex2ufdissertation --init my-thesis/
    cd my-thesis/
    latex2ufdissertation .

The default command validates the project and compiles to PDF using LuaLaTeX (TeX Live 2025 required).

## Status

v0.1 — works on the new UF template (Fall 2025+). MIT license.
```

- [ ] **Step 4: Write `CHANGELOG.md` stub**

```markdown
# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · SemVer.

## [Unreleased]

## [0.1.0] - 2026-05-26

Initial release. Validate + compile UF dissertation/thesis projects with the new UF template.

### Added
- CLI: `latex2ufdissertation INPUT [OUTPUT.pdf] [--init|--dry-run|--main|--json|--version]`
- Source-level validation: 9 errors + 2 warns against UF format rules
- LuaLaTeX compile driver
- `--init` scaffolds from UF IT site, falls back to bundled template
- Accepts zip / directory / git URL inputs
```

- [ ] **Step 5: Create empty package files**

```bash
touch pipeline/__init__.py
mkdir -p pipeline/template
mkdir -p tests/fixtures
touch tests/__init__.py
```

- [ ] **Step 6: Bundle the template into `pipeline/template/`**

```bash
cp -R Dissertation___Thesis_Example_File/* pipeline/template/
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml LICENSE README.md CHANGELOG.md pipeline/ tests/
git commit -m "chore: scaffold v0.1 package layout"
```

---

## Task 2: `pipeline/types.py` — Issues collector

**Files:**
- Create: `pipeline/types.py`
- Create: `tests/test_types.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_types.py
from pipeline.types import Issues, ConverterError


def test_issues_starts_empty():
    issues = Issues()
    assert issues.errors == []
    assert issues.warnings == []


def test_issues_collects_warn_and_error(capsys):
    issues = Issues()
    issues.warn("a warning")
    issues.error("an error")
    assert issues.warnings == ["a warning"]
    assert issues.errors == ["an error"]
    captured = capsys.readouterr()
    assert "[warn] a warning" in captured.out
    assert "[error] an error" in captured.out


def test_converter_error_is_exception():
    assert issubclass(ConverterError, Exception)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_types.py -v
```

Expected: ModuleNotFoundError on `pipeline.types`.

- [ ] **Step 3: Write `pipeline/types.py`**

```python
"""Shared types for the latex2ufdissertation pipeline."""

from pathlib import Path


class ConverterError(Exception):
    """Fatal failure raised from within the pipeline. main() catches and exits
    non-zero with a clean message instead of a traceback."""


class Issues:
    """Collect [warn] and [error] events plus run metadata for JSON output."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.input_path: str | None = None
        self.output_path: str | None = None
        self.main_tex: str | None = None
        self.dry_run: bool = False
        self.compile_result: dict | None = None

    def warn(self, msg: str) -> None:
        print(f"  [warn] {msg}")
        self.warnings.append(msg)

    def error(self, msg: str) -> None:
        print(f"  [error] {msg}")
        self.errors.append(msg)
```

- [ ] **Step 4: Run tests; verify pass**

```bash
pytest tests/test_types.py -v
```

- [ ] **Step 5: Commit**

```bash
git add pipeline/types.py tests/test_types.py
git commit -m "feat: add Issues collector and ConverterError"
```

---

## Task 3: `pipeline/resolve.py` — input resolution

Resolve `.zip`, directory, or git URL → a working directory containing the project.

**Files:**
- Create: `pipeline/resolve.py`
- Create: `tests/test_resolve.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_resolve.py
import subprocess
import zipfile
from pathlib import Path

import pytest

from pipeline.resolve import resolve, RESOLVE_GIT_TIMEOUT
from pipeline.types import ConverterError


def test_resolve_directory(tmp_path):
    src = tmp_path / "proj"
    src.mkdir()
    (src / "main.tex").write_text(r"\documentclass{ufdissertation}")
    root, cleanup = resolve(str(src))
    assert root == src
    cleanup()


def test_resolve_zip(tmp_path):
    src_zip = tmp_path / "proj.zip"
    with zipfile.ZipFile(src_zip, "w") as zf:
        zf.writestr("main.tex", r"\documentclass{ufdissertation}")
    root, cleanup = resolve(str(src_zip))
    assert (root / "main.tex").exists()
    cleanup()


def test_resolve_zip_with_single_top_dir(tmp_path):
    src_zip = tmp_path / "proj.zip"
    with zipfile.ZipFile(src_zip, "w") as zf:
        zf.writestr("wrapper/main.tex", r"\documentclass{ufdissertation}")
        zf.writestr("wrapper/sub/file.tex", "content")
    root, cleanup = resolve(str(src_zip))
    assert (root / "main.tex").exists()  # wrapper auto-unwrapped
    cleanup()


def test_resolve_missing_input_raises(tmp_path):
    with pytest.raises(ConverterError):
        resolve(str(tmp_path / "nope"))


def test_resolve_git_url_format_detection():
    from pipeline.resolve import _looks_like_git_url
    assert _looks_like_git_url("https://github.com/u/r.git")
    assert _looks_like_git_url("git@github.com:u/r.git")
    assert not _looks_like_git_url("/local/path")
    assert not _looks_like_git_url("./relative")


def test_resolve_constants():
    assert RESOLVE_GIT_TIMEOUT == 300  # 5 minutes, matches latex2arxiv convention
```

- [ ] **Step 2: Run tests; verify fail (ModuleNotFoundError)**

- [ ] **Step 3: Write `pipeline/resolve.py`**

```python
"""Resolve an input (.zip / directory / git URL) to a working directory."""

import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Callable

from pipeline.types import ConverterError

RESOLVE_GIT_TIMEOUT = 300  # seconds


def _looks_like_git_url(s: str) -> bool:
    if s.startswith(("http://", "https://", "git@", "ssh://")):
        return s.endswith(".git") or "github.com" in s or "gitlab.com" in s
    return False


def _zip_extract_unwrapping(zip_path: Path, dest: Path) -> Path:
    """Extract zip into dest. If the zip has a single top-level directory,
    return that directory (auto-unwrap). Otherwise return dest."""
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            # zip-slip guard
            target = (dest / member).resolve()
            if not str(target).startswith(str(dest.resolve())):
                raise ConverterError(f"zip-slip: {member}")
            if member.startswith("__MACOSX/") or member.endswith("/.DS_Store"):
                continue
        zf.extractall(dest)
    entries = [p for p in dest.iterdir() if p.name not in ("__MACOSX",)]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return dest


def _clone_git(url: str, dest: Path) -> Path:
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(dest)],
            check=True,
            timeout=RESOLVE_GIT_TIMEOUT,
            capture_output=True,
        )
    except subprocess.TimeoutExpired:
        raise ConverterError(f"git clone timed out after {RESOLVE_GIT_TIMEOUT}s: {url}")
    except subprocess.CalledProcessError as e:
        raise ConverterError(f"git clone failed: {e.stderr.decode(errors='replace')}")
    except FileNotFoundError:
        raise ConverterError("git is not installed")
    return dest


def resolve(input_str: str) -> tuple[Path, Callable[[], None]]:
    """Resolve the input to a working directory.

    Returns (root_dir, cleanup_callable). The caller MUST call cleanup() when
    done. For directory inputs cleanup is a no-op; for zip/git inputs it
    removes the temporary extraction directory.
    """
    if _looks_like_git_url(input_str):
        tmp = Path(tempfile.mkdtemp(prefix="l2ufd_git_"))
        root = _clone_git(input_str, tmp)
        return root, lambda: shutil.rmtree(tmp, ignore_errors=True)

    p = Path(input_str)
    if not p.exists():
        raise ConverterError(f"input not found: {input_str}")

    if p.is_dir():
        return p, lambda: None

    if p.suffix.lower() == ".zip":
        tmp = Path(tempfile.mkdtemp(prefix="l2ufd_zip_"))
        root = _zip_extract_unwrapping(p, tmp)
        return root, lambda: shutil.rmtree(tmp, ignore_errors=True)

    raise ConverterError(f"unsupported input type: {input_str}")


def stem_for_output(input_str: str, root: Path) -> str:
    """Derive the output PDF stem from the input."""
    if _looks_like_git_url(input_str):
        # repo-name from URL (strip .git)
        name = re.split(r"[/:]", input_str.rstrip("/"))[-1]
        return name[:-4] if name.endswith(".git") else name
    p = Path(input_str)
    if p.is_dir():
        return p.name
    return p.stem
```

- [ ] **Step 4: Run tests; verify pass**

```bash
pytest tests/test_resolve.py -v
```

- [ ] **Step 5: Commit**

```bash
git add pipeline/resolve.py tests/test_resolve.py
git commit -m "feat: resolve input (zip/dir/git URL) to working directory"
```

---

## Task 4: `pipeline/main_tex.py` — detect master `.tex`

Detect the master file via `\documentclass{ufdissertation}`. If multiple, prefer the one with the most `\set*File` calls.

**Files:**
- Create: `pipeline/main_tex.py`
- Create: `tests/test_main_tex.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_main_tex.py
import pytest

from pipeline.main_tex import detect_main_tex
from pipeline.types import ConverterError


def _write(d, name, content):
    p = d / name
    p.write_text(content, encoding="utf-8")
    return p


def test_detect_single_master(tmp_path):
    _write(tmp_path, "master.tex",
           r"\documentclass{ufdissertation}" + "\n\\setAbstractFile{a}")
    _write(tmp_path, "chapter1.tex", "content")
    assert detect_main_tex(tmp_path) == tmp_path / "master.tex"


def test_detect_prefers_setfile_count(tmp_path):
    _write(tmp_path, "draft.tex", r"\documentclass{ufdissertation}")
    _write(tmp_path, "real.tex",
           r"\documentclass{ufdissertation}" + "\n" +
           r"\setAbstractFile{a}" + "\n" + r"\setBiographicalFile{b}")
    assert detect_main_tex(tmp_path) == tmp_path / "real.tex"


def test_detect_with_explicit_hint(tmp_path):
    _write(tmp_path, "a.tex", r"\documentclass{ufdissertation}")
    _write(tmp_path, "b.tex", r"\documentclass{ufdissertation}")
    assert detect_main_tex(tmp_path, hint="b.tex") == tmp_path / "b.tex"


def test_detect_explicit_hint_missing_raises(tmp_path):
    with pytest.raises(ConverterError):
        detect_main_tex(tmp_path, hint="nope.tex")


def test_detect_no_master_raises(tmp_path):
    _write(tmp_path, "only.tex", r"\documentclass{article}")
    with pytest.raises(ConverterError):
        detect_main_tex(tmp_path)


def test_detect_skips_commented_documentclass(tmp_path):
    _write(tmp_path, "real.tex", r"\documentclass{ufdissertation}")
    _write(tmp_path, "fake.tex", "% \\documentclass{ufdissertation}")
    assert detect_main_tex(tmp_path) == tmp_path / "real.tex"
```

- [ ] **Step 2: Run tests; verify fail**

- [ ] **Step 3: Write `pipeline/main_tex.py`**

```python
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

    # Highest setfile count wins; ties broken by shortest path.
    candidates.sort(key=lambda x: (-x[1], len(str(x[0]))))
    return candidates[0][0]
```

- [ ] **Step 4: Run tests; verify pass**

- [ ] **Step 5: Commit**

```bash
git add pipeline/main_tex.py tests/test_main_tex.py
git commit -m "feat: auto-detect ufdissertation master .tex"
```

---

## Task 5: `pipeline/checks.py` — v0.1 validation rules

Source-level + class-config checks. 9 errors, 2 warns.

**Files:**
- Create: `pipeline/checks.py`
- Create: `tests/test_checks.py`

- [ ] **Step 1: Write the failing tests (cover all 11 rules)**

```python
# tests/test_checks.py
from pathlib import Path

import pytest

from pipeline.checks import run_checks
from pipeline.types import Issues


def _project(tmp_path: Path, master: str, extra: dict[str, str] | None = None) -> Path:
    (tmp_path / "master.tex").write_text(master, encoding="utf-8")
    for name, body in (extra or {}).items():
        (tmp_path / name).write_text(body, encoding="utf-8")
    return tmp_path / "master.tex"


_VALID = r"""\documentclass{ufdissertation}
\title{X}
\author{Y}
\degreeType{Doctor of Philosophy}
\thesisType{Dissertation}
\setAcknowledgementsFile{ack}
\setAbstractFile{abs}
\setReferenceFile{refs}{agsm}
\setBiographicalFile{bio}
\begin{document}\end{document}
"""

_VALID_FILES = {
    "ack.tex": "",
    "abs.tex": "",
    "refs.bib": "",
    "bio.tex": "",
}


def test_valid_project_no_errors(tmp_path):
    master = _project(tmp_path, _VALID, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert issues.errors == []
    assert issues.warnings == []


# E1: wrong document class
def test_e1_wrong_class(tmp_path):
    master = _project(tmp_path, r"\documentclass{article}" + "\n" + _VALID.split("\n", 1)[1],
                      _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert any("wrong document class" in e for e in issues.errors)


# Parametrized E2–E5 (missing top-level commands)
@pytest.mark.parametrize("cmd,msg_fragment", [
    (r"\title{X}", r"\title"),
    (r"\author{Y}", r"\author"),
    (r"\degreeType{Doctor of Philosophy}", r"\degreeType"),
    (r"\thesisType{Dissertation}", r"\thesisType"),
])
def test_missing_required_command(tmp_path, cmd, msg_fragment):
    src = _VALID.replace(cmd, "")
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert any(msg_fragment in e for e in issues.errors), f"no error mentioning {msg_fragment}"


# E6–E9: missing setFile or missing file
@pytest.mark.parametrize("set_cmd,file_name,msg_fragment", [
    (r"\setAcknowledgementsFile{ack}", "ack.tex", "Acknowledgements"),
    (r"\setAbstractFile{abs}",         "abs.tex", "Abstract"),
    (r"\setReferenceFile{refs}{agsm}", "refs.bib", "Reference"),
    (r"\setBiographicalFile{bio}",     "bio.tex", "Biographical"),
])
def test_missing_setfile_command(tmp_path, set_cmd, file_name, msg_fragment):
    src = _VALID.replace(set_cmd, "")
    files = dict(_VALID_FILES)
    files.pop(file_name, None)
    master = _project(tmp_path, src, files)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert any(msg_fragment in e for e in issues.errors)


@pytest.mark.parametrize("file_name,msg_fragment", [
    ("ack.tex", "Acknowledgements"),
    ("abs.tex", "Abstract"),
    ("refs.bib", "Reference"),
    ("bio.tex", "Biographical"),
])
def test_missing_setfile_target_file(tmp_path, file_name, msg_fragment):
    files = {k: v for k, v in _VALID_FILES.items() if k != file_name}
    master = _project(tmp_path, _VALID, files)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert any(msg_fragment in e for e in issues.errors)


# W1: editMode warn
def test_w1_editmode_warn(tmp_path):
    src = _VALID.replace(
        r"\documentclass{ufdissertation}",
        r"\documentclass[editMode]{ufdissertation}",
    )
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert any("editMode" in w for w in issues.warnings)


# W2: pdflatex hint warn
def test_w2_pdflatex_magic_comment(tmp_path):
    src = "% !TEX program = pdflatex\n" + _VALID
    master = _project(tmp_path, src, _VALID_FILES)
    issues = Issues()
    run_checks(master, tmp_path, issues)
    assert any("LuaLaTeX" in w for w in issues.warnings)
```

- [ ] **Step 2: Run tests; verify fail**

- [ ] **Step 3: Write `pipeline/checks.py`**

```python
"""v0.1 validation rules for UF dissertations/theses."""

import re
from pathlib import Path

from pipeline.types import Issues

_DOCCLASS_RE = re.compile(r"\\documentclass(\[([^\]]*)\])?\{([^}]+)\}")
_REQUIRED_TOPLEVEL = (
    (r"\title",      r"\title is required"),
    (r"\author",     r"\author is required"),
    (r"\degreeType", r'\degreeType is required (e.g. "Doctor of Philosophy")'),
    (r"\thesisType", r"\thesisType is required (Dissertation or Thesis)"),
)
_SETFILE_RULES = (
    # (command, expected suffix list, label)
    (r"\setAcknowledgementsFile", (".tex",), "Acknowledgements"),
    (r"\setAbstractFile",         (".tex",), "Abstract"),
    (r"\setReferenceFile",        (".bib",), "Reference"),
    (r"\setBiographicalFile",     (".tex",), "Biographical"),
)


def _strip_comments(text: str) -> str:
    return re.sub(r"(?m)(?<!\\)%[^\n]*", "", text)


def _has_command(nc: str, cmd: str) -> bool:
    # Match `\cmd{...}` with non-empty content
    pat = re.escape(cmd) + r"\s*\{[^}]*\S[^}]*\}"
    return re.search(pat, nc) is not None


def _setfile_arg(nc: str, cmd: str) -> str | None:
    """Return the first argument of \\setXxxFile{ARG}{...} if present."""
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
        # Try the bare arg + each candidate suffix
        candidates = [root / arg] + [root / f"{arg}{s}" for s in suffixes]
        if not any(c.exists() for c in candidates):
            issues.error(f"{label} file required ({cmd}: {arg!r} not found in project root)")

    # W1: editMode option
    if m and m.group(2) and "editMode" in m.group(2):
        issues.warn("editMode option set — remove before final submission")

    # W2: non-LuaLaTeX compiler hint
    if re.search(r"%\s*!TEX\s+program\s*=\s*(pdflatex|xelatex)", raw):
        issues.warn("UF requires LuaLaTeX — pdflatex/xelatex hint detected")
```

- [ ] **Step 4: Run tests; verify pass**

```bash
pytest tests/test_checks.py -v
```

- [ ] **Step 5: Commit**

```bash
git add pipeline/checks.py tests/test_checks.py
git commit -m "feat: add v0.1 validation rules (9 errors + 2 warns)"
```

---

## Task 6: `pipeline/init.py` — scaffold

Fetch UF IT template URL; fall back to bundled.

**Files:**
- Create: `pipeline/init.py`
- Create: `tests/test_init.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_init.py
from pathlib import Path
from unittest.mock import patch

import pytest

from pipeline.init import init_project, BUNDLED_TEMPLATE_DIR
from pipeline.types import ConverterError


def test_bundled_template_exists():
    assert BUNDLED_TEMPLATE_DIR.exists()
    assert (BUNDLED_TEMPLATE_DIR / "exampleMasterFile.tex").exists()


def test_init_uses_bundled_when_fetch_fails(tmp_path):
    target = tmp_path / "out"
    with patch("pipeline.init._fetch_remote", side_effect=ConnectionError("offline")):
        init_project(target)
    assert (target / "exampleMasterFile.tex").exists()
    assert (target / "ufdissertation.cls").exists()


def test_init_refuses_nonempty_target(tmp_path):
    target = tmp_path / "out"
    target.mkdir()
    (target / "existing").write_text("x")
    with pytest.raises(ConverterError):
        init_project(target)


def test_init_creates_parent_dirs(tmp_path):
    target = tmp_path / "deep" / "nested" / "out"
    with patch("pipeline.init._fetch_remote", side_effect=ConnectionError):
        init_project(target)
    assert target.exists()
```

- [ ] **Step 2: Run tests; verify fail**

- [ ] **Step 3: Write `pipeline/init.py`**

```python
"""--init: scaffold a new UF dissertation project."""

import shutil
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path

from pipeline.types import ConverterError

BUNDLED_TEMPLATE_DIR = Path(__file__).parent / "template"
UF_IT_TEMPLATE_URL = (
    "https://it.ufl.edu/wp-content/uploads/2025/11/"
    "Dissertation___Thesis_Example_File.zip"
)
FETCH_TIMEOUT = 30  # seconds


def _fetch_remote(dest: Path) -> None:
    """Fetch the latest UF IT template zip and extract into dest."""
    req = urllib.request.Request(UF_IT_TEMPLATE_URL, headers={"User-Agent": "latex2ufdissertation"})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
        data = resp.read()
    with zipfile.ZipFile(BytesIO(data)) as zf:
        zf.extractall(dest)
    # If zip wraps everything in one top-level dir, unwrap.
    entries = [p for p in dest.iterdir() if p.name not in ("__MACOSX",)]
    if len(entries) == 1 and entries[0].is_dir():
        inner = entries[0]
        for item in inner.iterdir():
            shutil.move(str(item), str(dest / item.name))
        inner.rmdir()


def _copy_bundled(dest: Path) -> None:
    for item in BUNDLED_TEMPLATE_DIR.iterdir():
        if item.is_dir():
            shutil.copytree(item, dest / item.name)
        else:
            shutil.copy2(item, dest / item.name)


def init_project(target: Path) -> None:
    """Scaffold a new UF dissertation project at `target`.

    Tries to fetch the latest UF IT template first; falls back to bundled.
    Refuses non-empty targets.
    """
    if target.exists() and any(target.iterdir()):
        raise ConverterError(f"target is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)

    try:
        _fetch_remote(target)
        print("  fetched latest template from UF IT")
    except Exception as e:
        print(f"  [warn] couldn't reach UF IT site ({type(e).__name__}); using bundled template")
        _copy_bundled(target)

    print(f"  scaffold ready at {target}/")
    print(f"  edit exampleMasterFile.tex to start writing.")
```

- [ ] **Step 4: Run tests; verify pass**

- [ ] **Step 5: Commit**

```bash
git add pipeline/init.py tests/test_init.py
git commit -m "feat: --init scaffolds from UF IT site with bundled fallback"
```

---

## Task 7: `pipeline/build.py` — LuaLaTeX compile

**Files:**
- Create: `pipeline/build.py`
- Create: `tests/test_build.py`

- [ ] **Step 1: Write the failing tests** (skip live-compile; test error parsing + missing-tool detection)

```python
# tests/test_build.py
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from pipeline.build import format_errors, lualatex_available
from pipeline.types import Issues


def test_format_errors_extracts_bang_blocks():
    log = """
Some preamble noise
! Undefined control sequence.
l.42 \\nosuchcmd
                  next line of context
! Missing $ inserted.
l.99 $1+1
        end
"""
    formatted = format_errors(log)
    assert "! Undefined control sequence." in formatted
    assert "l.42" in formatted
    assert "! Missing $ inserted." in formatted


def test_format_errors_caps_at_5_blocks():
    log = "\n".join([f"! Error {i}.\nl.{i} bad" for i in range(10)])
    formatted = format_errors(log)
    blocks = formatted.count("! Error ")
    assert blocks == 5


def test_format_errors_empty():
    assert format_errors("") == ""
    assert format_errors("no errors here") == ""


def test_lualatex_available_when_installed():
    with patch("shutil.which", return_value="/usr/bin/lualatex"):
        assert lualatex_available()


def test_lualatex_unavailable_when_missing():
    with patch("shutil.which", return_value=None):
        assert not lualatex_available()
```

- [ ] **Step 2: Run tests; verify fail**

- [ ] **Step 3: Write `pipeline/build.py`**

```python
"""LuaLaTeX compile driver."""

import re
import shutil
import subprocess
import webbrowser
from pathlib import Path

from pipeline.types import Issues

COMPILE_TIMEOUT = 600  # seconds
MAX_ERROR_BLOCKS = 5

_BANG_RE = re.compile(r"^!.*", re.MULTILINE)
_LINE_RE = re.compile(r"^l\.\d+.*", re.MULTILINE)


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
            i = i + len(chunk)
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
    # Three passes: 1st for aux, biber for bibliography, 2nd + 3rd for cross-refs.
    log_text = ""
    for pass_n in (1, 2, 3):
        try:
            r = subprocess.run(
                cmd, cwd=root, timeout=COMPILE_TIMEOUT, capture_output=True
            )
            log_text = r.stdout.decode(errors="replace") + r.stderr.decode(errors="replace")
        except subprocess.TimeoutExpired:
            issues.error(f"lualatex timed out after {COMPILE_TIMEOUT}s")
            return None

        if pass_n == 1 and biber_available():
            stem = main_tex.stem
            bcf = root / f"{stem}.bcf"
            if bcf.exists():
                subprocess.run(["biber", stem], cwd=root, capture_output=True, timeout=COMPILE_TIMEOUT)

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
```

- [ ] **Step 4: Run tests; verify pass**

- [ ] **Step 5: Commit**

```bash
git add pipeline/build.py tests/test_build.py
git commit -m "feat: LuaLaTeX compile driver with error parsing"
```

---

## Task 8: `converter.py` — CLI orchestration

**Files:**
- Create: `converter.py`
- Create: `tests/test_converter.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_converter.py
import json
import subprocess
import sys
from pathlib import Path

import pytest


def _run(*args, cwd=None):
    return subprocess.run(
        [sys.executable, "-m", "converter", *args],
        cwd=cwd, capture_output=True, text=True
    )


def test_version():
    r = _run("--version")
    assert r.returncode == 0
    assert "0.1.0" in r.stdout


def test_missing_input_returns_2(tmp_path):
    r = _run(str(tmp_path / "nope"))
    assert r.returncode == 2


def test_dry_run_on_valid_fixture(tmp_path):
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "master.tex").write_text(_MIN_VALID, encoding="utf-8")
    for f in ("ack.tex", "abs.tex", "bio.tex"):
        (proj / f).write_text("", encoding="utf-8")
    (proj / "refs.bib").write_text("", encoding="utf-8")
    r = _run(str(proj), "--dry-run")
    assert r.returncode == 0, r.stderr + r.stdout


def test_dry_run_errors_exit_1(tmp_path):
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "master.tex").write_text(r"\documentclass{article}", encoding="utf-8")
    r = _run(str(proj), "--dry-run")
    assert r.returncode == 1


def test_json_output_summary(tmp_path):
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "master.tex").write_text(_MIN_VALID, encoding="utf-8")
    for f in ("ack.tex", "abs.tex", "bio.tex"):
        (proj / f).write_text("", encoding="utf-8")
    (proj / "refs.bib").write_text("", encoding="utf-8")
    r = _run(str(proj), "--dry-run", "--json")
    payload = json.loads(r.stdout)
    assert payload["errors"] == []
    assert payload["dry_run"] is True


def test_init_creates_target(tmp_path):
    target = tmp_path / "new-thesis"
    r = _run("--init", str(target))
    assert r.returncode == 0
    assert (target / "exampleMasterFile.tex").exists()


_MIN_VALID = r"""\documentclass{ufdissertation}
\title{X}
\author{Y}
\degreeType{Doctor of Philosophy}
\thesisType{Dissertation}
\setAcknowledgementsFile{ack}
\setAbstractFile{abs}
\setReferenceFile{refs}{agsm}
\setBiographicalFile{bio}
\begin{document}\end{document}
"""
```

- [ ] **Step 2: Run tests; verify fail**

- [ ] **Step 3: Write `converter.py`**

```python
"""latex2ufdissertation CLI entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pipeline.build import compile_pdf, lualatex_available
from pipeline.checks import run_checks
from pipeline.init import init_project
from pipeline.main_tex import detect_main_tex
from pipeline.resolve import resolve, stem_for_output
from pipeline.types import ConverterError, Issues

__version__ = "0.1.0"


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
    p.add_argument("--json", action="store_true", dest="json_out",
                   help="Machine-readable summary on stdout")
    p.add_argument("--version", action="version", version=f"latex2ufdissertation {__version__}")
    return p


def _emit_json(issues: Issues) -> None:
    payload = {
        "input": issues.input_path,
        "output": issues.output_path,
        "main_tex": issues.main_tex,
        "dry_run": issues.dry_run,
        "errors": issues.errors,
        "warnings": issues.warnings,
        "compile_result": issues.compile_result,
    }
    print(json.dumps(payload, indent=2))


def _summary(issues: Issues) -> None:
    n_err = len(issues.errors)
    n_warn = len(issues.warnings)
    print(f"\nSummary: {n_err} error(s), {n_warn} warning(s)")


def _resolve_output_path(input_str: str, root: Path, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    stem = stem_for_output(input_str, root)
    input_path = Path(input_str)
    if input_path.is_dir():
        return input_path / f"{stem}_ufdissertation.pdf"
    if input_path.suffix.lower() == ".zip":
        return input_path.parent / f"{stem}_ufdissertation.pdf"
    # git URL: land in cwd
    return Path.cwd() / f"{stem}_ufdissertation.pdf"


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    issues = Issues()

    # --init path
    if args.init:
        try:
            init_project(Path(args.init))
            return 0
        except ConverterError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2

    if not args.input:
        print("Error: INPUT required (use --init to scaffold a new project)", file=sys.stderr)
        return 2

    issues.input_path = args.input
    issues.dry_run = args.dry_run

    # Resolve input
    try:
        root, cleanup = resolve(args.input)
    except ConverterError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    try:
        master = detect_main_tex(root, hint=args.main)
        issues.main_tex = str(master.relative_to(root))

        print(f"  validating {issues.main_tex}")
        run_checks(master, root, issues)

        exit_code = 0

        if args.dry_run:
            _summary(issues)
            if args.json_out:
                _emit_json(issues)
            return 1 if issues.errors else 0

        # Default path: compile too
        if not lualatex_available():
            issues.error("lualatex not found — install TeX Live 2025")
            _summary(issues)
            if args.json_out:
                _emit_json(issues)
            return 3

        output = _resolve_output_path(args.input, root, args.output)
        issues.output_path = str(output)
        print(f"  compiling to {output}")
        pdf = compile_pdf(master, root, output, issues)
        if pdf is None:
            _summary(issues)
            if args.json_out:
                _emit_json(issues)
            return 1

        _summary(issues)
        if args.json_out:
            _emit_json(issues)
        return 1 if issues.errors else 0
    except ConverterError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    finally:
        cleanup()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests; verify pass**

```bash
pytest tests/test_converter.py -v
```

- [ ] **Step 5: Commit**

```bash
git add converter.py tests/test_converter.py
git commit -m "feat: CLI orchestration (validate + compile + init)"
```

---

## Task 9: Full-suite green + version smoke test

- [ ] **Step 1: Run full test suite**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 2: Ruff check + format**

```bash
ruff check .
ruff format .
```

If ruff reports issues, fix them and re-run.

- [ ] **Step 3: Install locally and smoke-test the CLI**

```bash
pip install -e .
latex2ufdissertation --version
latex2ufdissertation --init /tmp/l2ufd-smoke
ls /tmp/l2ufd-smoke/
latex2ufdissertation /tmp/l2ufd-smoke/ --dry-run
```

Expected: version prints `0.1.0`; init creates a populated dir; dry-run on the bundled template exits 0 (the template already passes the 11 v0.1 checks).

- [ ] **Step 4: If any smoke step fails**, fix the cause; do NOT amend prior commits — make a new `fix:` commit.

- [ ] **Step 5: Commit any smoke-fix changes** (if needed)

```bash
git add -A
git commit -m "fix: smoke-test discoveries"
```

---

## Task 10: Tag v0.1.0

- [ ] **Step 1: Verify CHANGELOG is current**

`[Unreleased]` should be empty; `[0.1.0]` section should describe what shipped.

- [ ] **Step 2: Tag the release**

```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git log --oneline | head -5
git tag --list
```

- [ ] **Step 3: Verify package builds cleanly**

```bash
python -m pip install --upgrade build
python -m build
ls dist/
```

Expected: `latex2ufdissertation-0.1.0.tar.gz` and `latex2ufdissertation-0.1.0-py3-none-any.whl`.

- [ ] **Step 4 (optional, manual):** PyPI upload + GitHub remote setup are user actions (need credentials). Note in the user-facing summary that v0.1.0 is tagged and built locally; publishing is a follow-up.

---

## Self-review checklist

After completing all tasks:

- [ ] Each E1–E9 rule has a positive test (rule fires when expected) **and** the valid-project test passes (rule doesn't fire on good input).
- [ ] Each W1–W2 rule has a positive test.
- [ ] `pipeline/template/` is populated; `--init` falls back to it.
- [ ] Exit codes: 0 (clean), 1 (validation/compile error), 2 (bad input), 3 (no LuaLaTeX).
- [ ] `--json` payload includes input/output/main_tex/dry_run/errors/warnings/compile_result.
- [ ] `--version` prints `0.1.0`.
- [ ] Full `pytest -v` is green.
- [ ] `ruff check .` is clean.
- [ ] `pip install -e .` succeeds.
- [ ] `python -m build` produces both sdist and wheel.
- [ ] Tag `v0.1.0` exists.

"""Resolve an input (.zip / directory / git URL) to a working directory."""

import re
import shutil
import subprocess
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path

from latex2ufdissertation.pipeline.types import ConverterError, UnreadableInput

RESOLVE_GIT_TIMEOUT = 300  # seconds


def _looks_like_git_url(s: str) -> bool:
    if s.startswith(("http://", "https://", "git@", "ssh://")):
        return s.endswith(".git") or "github.com" in s or "gitlab.com" in s
    return False


def _zip_extract_unwrapping(zip_path: Path, dest: Path) -> Path:
    """Extract zip into dest. If the zip has a single top-level directory,
    return that directory (auto-unwrap). Otherwise return dest."""
    with zipfile.ZipFile(zip_path) as zf:
        dest_resolved = str(dest.resolve())
        for member in zf.namelist():
            target = (dest / member).resolve()
            if not str(target).startswith(dest_resolved):
                raise UnreadableInput(f"zip-slip: {member}")
        for member in zf.namelist():
            if member.startswith("__MACOSX/") or member.endswith("/.DS_Store"):
                continue
            zf.extract(member, dest)

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
    except subprocess.TimeoutExpired as e:
        raise UnreadableInput(f"git clone timed out after {RESOLVE_GIT_TIMEOUT}s: {url}") from e
    except subprocess.CalledProcessError as e:
        raise UnreadableInput(f"git clone failed: {e.stderr.decode(errors='replace')}") from e
    except FileNotFoundError as e:
        raise ConverterError("git is not installed") from e
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
        raise UnreadableInput(f"input not found: {input_str}")

    if p.is_dir():
        return p, lambda: None

    if p.suffix.lower() == ".zip":
        tmp = Path(tempfile.mkdtemp(prefix="l2ufd_zip_"))
        root = _zip_extract_unwrapping(p, tmp)
        return root, lambda: shutil.rmtree(tmp, ignore_errors=True)

    raise UnreadableInput(f"unsupported input type: {input_str}")


def stem_for_output(input_str: str, root: Path) -> str:
    """Derive the output PDF stem from the input."""
    if _looks_like_git_url(input_str):
        name = re.split(r"[/:]", input_str.rstrip("/"))[-1]
        return name[:-4] if name.endswith(".git") else name
    p = Path(input_str)
    if p.is_dir():
        return p.name
    return p.stem

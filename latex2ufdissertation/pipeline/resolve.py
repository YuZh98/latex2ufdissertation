"""Resolve an input (.zip / directory / git URL) to a working directory."""

import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

from latex2ufdissertation.pipeline.types import ConverterError, UnreadableInput

RESOLVE_GIT_TIMEOUT = 300  # seconds

# Zip-bomb caps enforced before extraction (single source of truth; the --init
# template extraction in init.py inherits these via _safe_extract). The 200 MB
# uncompressed ceiling is 4x the 50 MB download cap in init.py — generous
# headroom for any real dissertation, which is a few MB, while stopping a small
# archive from expanding without bound.
MAX_TOTAL_UNCOMPRESSED = 200 * 1024 * 1024  # 200 MB total declared uncompressed size
MAX_MEMBER_COUNT = 10_000

# Hosts allowed for git clone via https:// URLs.
_HTTPS_ALLOWED_HOSTS: frozenset[str] = frozenset({"github.com", "www.github.com", "gitlab.com"})

# Hosts allowed in the scp-style "git@host:..." form.
_SCP_ALLOWED_HOSTS: frozenset[str] = frozenset({"github.com", "gitlab.com"})


def _looks_like_git_url(s: str) -> bool:
    """Return True only for git URLs with an allow-listed host.

    Accepted forms:
      - https://<allowed-host>/...   (any path; .git suffix optional)
      - ssh://<allowed-host>/...     (SSH clone URL form)
      - git@<allowed-host>:...       (scp-style; any path)

    Rejected:
      - http:// (cleartext)
      - Any host not in the allowlists above (blocks SSRF / IMDS)
      - IP-literal hosts (caught by hostname not being in allowlist)
      - Subdomain-prefix bypass (e.g. github.com.evil.com) — caught by
        exact-match against urlparse().hostname rather than substring.
    """
    # scp form: git@host:path — urlparse cannot handle this reliably.
    if s.startswith("git@"):
        rest = s[len("git@") :]
        colon = rest.find(":")
        if colon == -1:
            return False
        host = rest[:colon].lower()
        return host in _SCP_ALLOWED_HOSTS

    # https:// and ssh:// are accepted; http:// and anything else is not.
    try:
        parsed = urlparse(s)
    except ValueError:
        return False

    if parsed.scheme not in {"https", "ssh"}:
        return False

    # Reject embedded userinfo (e.g. https://evil.com@github.com/...): the host
    # is allow-listed, but arbitrary credentials would be forwarded to git clone.
    if parsed.username or parsed.password:
        return False

    # parsed.hostname strips port, userinfo, and lowercases; None for malformed.
    host = parsed.hostname
    if not host:
        return False
    return host in _HTTPS_ALLOWED_HOSTS


def _safe_extract(zf: zipfile.ZipFile, dest: Path) -> None:
    """Extract all members of *zf* into *dest* under two guards, both applied
    before any byte is written:

    - Zip-slip: reject any member whose resolved path escapes *dest*, using
      ``Path.is_relative_to`` (Python 3.9+). The old ``startswith(str(dest))``
      missed sibling-prefix paths such as ``../destextra/evil``.
    - Zip-bomb: reject archives declaring more than ``MAX_MEMBER_COUNT``
      members or a total uncompressed size above ``MAX_TOTAL_UNCOMPRESSED``.
      The cap reads ``ZipInfo.file_size`` from the central directory, so the
      breach trips on inspection rather than after a 50 MB expansion.
    """
    infos = zf.infolist()
    if len(infos) > MAX_MEMBER_COUNT:
        raise UnreadableInput(f"zip has too many members ({len(infos)} > {MAX_MEMBER_COUNT})")
    total = sum(info.file_size for info in infos)
    if total > MAX_TOTAL_UNCOMPRESSED:
        raise UnreadableInput(
            f"zip uncompressed size exceeds cap ({total} > {MAX_TOTAL_UNCOMPRESSED} bytes)"
        )

    dest_resolved = dest.resolve()
    for member in zf.namelist():
        target = (dest / member).resolve()
        if not target.is_relative_to(dest_resolved):
            raise UnreadableInput(f"zip-slip: {member}")
    for member in zf.namelist():
        if member.startswith("__MACOSX/") or member.endswith("/.DS_Store"):
            continue
        zf.extract(member, dest)


def _zip_extract_unwrapping(zip_path: Path, dest: Path) -> Path:
    """Extract zip into dest. If the zip has a single top-level directory,
    return that directory (auto-unwrap). Otherwise return dest."""
    with zipfile.ZipFile(zip_path) as zf:
        _safe_extract(zf, dest)

    entries = [p for p in dest.iterdir() if p.name not in ("__MACOSX",)]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return dest


def _clone_git(url: str, dest: Path) -> Path:
    # Close stdin and disable git's terminal credential prompt so a private or
    # typo'd URL fails fast instead of blocking on a password prompt up to the
    # timeout. Merge into os.environ so PATH (git discovery) is preserved.
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(dest)],
            check=True,
            timeout=RESOLVE_GIT_TIMEOUT,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            env=env,
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
        try:
            root = _clone_git(input_str, tmp)
        except BaseException:
            shutil.rmtree(tmp, ignore_errors=True)
            raise
        return root, lambda: shutil.rmtree(tmp, ignore_errors=True)

    p = Path(input_str)
    if not p.exists():
        raise UnreadableInput(f"input not found: {input_str}")

    if p.is_dir():
        return p, lambda: None

    if p.suffix.lower() == ".zip":
        tmp = Path(tempfile.mkdtemp(prefix="l2ufd_zip_"))
        try:
            root = _zip_extract_unwrapping(p, tmp)
        except (zipfile.BadZipFile, OSError) as e:
            shutil.rmtree(tmp, ignore_errors=True)
            raise UnreadableInput(f"not a valid zip: {e}") from e
        except BaseException:
            shutil.rmtree(tmp, ignore_errors=True)
            raise
        return root, lambda: shutil.rmtree(tmp, ignore_errors=True)

    raise UnreadableInput(f"unsupported input type: {input_str}")


def input_mode(input_str: str) -> str:
    """Classify the input source as one of the JSON schema's detected modes.

    Returns "git", "zip", "pdf", "dir", or "unknown". Pure string/path
    classification (no extraction).

    Branch order MUST mirror `resolve()`'s dispatch: git URL, then
    directory, then `.zip`. A directory whose name ends in `.zip` is a
    directory to `resolve()`, so it must read as "dir" here too. ("pdf" is
    reserved for v1.0 PDF input; `resolve()` does not accept it yet.)
    """
    if _looks_like_git_url(input_str):
        return "git"
    p = Path(input_str)
    if p.is_dir():
        return "dir"
    suffix = p.suffix.lower()
    if suffix == ".zip":
        return "zip"
    if suffix == ".pdf":
        return "pdf"
    return "unknown"


def stem_for_output(input_str: str, root: Path) -> str:
    """Derive the output PDF stem from the input."""
    if _looks_like_git_url(input_str):
        name = re.split(r"[/:]", input_str.rstrip("/"))[-1]
        return name[:-4] if name.endswith(".git") else name
    p = Path(input_str)
    if p.is_dir():
        return p.name
    return p.stem

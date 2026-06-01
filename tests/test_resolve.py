import io
import subprocess
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from latex2ufdissertation.pipeline.resolve import (
    RESOLVE_GIT_TIMEOUT,
    _looks_like_git_url,
    _safe_extract,
    input_mode,
    resolve,
)
from latex2ufdissertation.pipeline.types import ConverterError, UnreadableInput


def test_input_mode_classifies_git_zip_pdf():
    assert input_mode("https://github.com/u/repo.git") == "git"
    assert input_mode("git@github.com:u/repo.git") == "git"
    assert input_mode("thesis.zip") == "zip"
    assert input_mode("THESIS.ZIP") == "zip"
    assert input_mode("paper.pdf") == "pdf"


def test_input_mode_classifies_directory(tmp_path):
    d = tmp_path / "proj"
    d.mkdir()
    assert input_mode(str(d)) == "dir"


def test_input_mode_unknown_for_unclassifiable(tmp_path):
    assert input_mode(str(tmp_path / "nonexistent.tex")) == "unknown"


def test_input_mode_directory_named_zip_is_dir(tmp_path):
    # A directory whose name ends in .zip is a directory to resolve()
    # (is_dir checked before suffix); input_mode must agree, not say "zip".
    d = tmp_path / "archive.zip"
    d.mkdir()
    assert input_mode(str(d)) == "dir"
    root, cleanup = resolve(str(d))
    assert root == d  # resolve() treats it as a directory
    cleanup()


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
    assert (root / "main.tex").exists()
    cleanup()


def test_resolve_missing_input_raises(tmp_path):
    with pytest.raises(ConverterError):
        resolve(str(tmp_path / "nope"))


def test_resolve_constants():
    assert RESOLVE_GIT_TIMEOUT == 300


def test_zip_slip_raises_unreadable_input(tmp_path):
    src_zip = tmp_path / "evil.zip"
    with zipfile.ZipFile(src_zip, "w") as zf:
        zf.writestr("../escape.tex", "bad content")
    with pytest.raises(UnreadableInput):
        resolve(str(src_zip))


def test_git_clone_timeout_raises_unreadable_input():
    with patch(
        "latex2ufdissertation.pipeline.resolve.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="git", timeout=300),
    ):
        with pytest.raises(UnreadableInput):
            resolve("https://github.com/fake/repo.git")


def test_git_clone_failure_raises_unreadable_input():
    with patch(
        "latex2ufdissertation.pipeline.resolve.subprocess.run",
        side_effect=subprocess.CalledProcessError(
            returncode=128, cmd="git", stderr=b"fatal: not found"
        ),
    ):
        with pytest.raises(UnreadableInput):
            resolve("https://github.com/fake/repo.git")


# ---------------------------------------------------------------------------
# Security: zip-slip sibling-prefix bypass (item 1)
# ---------------------------------------------------------------------------


def test_zip_slip_sibling_prefix_rejected(tmp_path):
    """A member whose resolved path starts with the dest prefix but escapes via
    sibling directory must be rejected — the old `startswith(dest_str)` check
    without a trailing separator would pass 'l2ufd_zip_XXXextra/evil'."""
    src_zip = tmp_path / "sibling.zip"
    dest_sibling_name = tmp_path.name + "extra"  # shares prefix with tmp_path
    evil_member = f"../{dest_sibling_name}/evil.tex"
    with zipfile.ZipFile(src_zip, "w") as zf:
        zf.writestr(evil_member, "bad")
    with pytest.raises(UnreadableInput, match="zip-slip"):
        resolve(str(src_zip))


def test_zip_slip_absolute_path_rejected(tmp_path):
    """Absolute paths in zip members must be rejected."""
    src_zip = tmp_path / "abs.zip"
    with zipfile.ZipFile(src_zip, "w") as zf:
        zf.writestr("/etc/evil.tex", "bad")
    with pytest.raises(UnreadableInput, match="zip-slip"):
        resolve(str(src_zip))


def test_zip_slip_valid_zip_still_extracts(tmp_path):
    """A legitimate zip must still extract correctly after the hardening."""
    src_zip = tmp_path / "legit.zip"
    with zipfile.ZipFile(src_zip, "w") as zf:
        zf.writestr("proj/main.tex", r"\documentclass{ufdissertation}")
        zf.writestr("proj/chapters/intro.tex", "intro")
    root, cleanup = resolve(str(src_zip))
    assert (root / "main.tex").exists()
    assert (root / "chapters" / "intro.tex").exists()
    cleanup()


# ---------------------------------------------------------------------------
# Security: BadZipFile raises UnreadableInput and cleans up temp dir (item 2)
# ---------------------------------------------------------------------------


def test_bad_zip_raises_unreadable_input(tmp_path):
    """A corrupt (non-zip) .zip file must raise UnreadableInput, not a raw traceback."""
    src_zip = tmp_path / "corrupt.zip"
    src_zip.write_bytes(b"this is not a zip file at all")
    with pytest.raises(UnreadableInput, match="not a valid zip"):
        resolve(str(src_zip))


def test_bad_zip_temp_dir_cleaned(tmp_path):
    """The temp extraction dir must not be orphaned when zip is corrupt."""
    src_zip = tmp_path / "corrupt2.zip"
    src_zip.write_bytes(b"garbage")
    # Track dirs before and after — the tmp dir must be cleaned on failure.
    import tempfile as _tempfile

    created_dirs: list[str] = []
    real_mkdtemp = _tempfile.mkdtemp

    def spy_mkdtemp(**kwargs):
        d = real_mkdtemp(**kwargs)
        created_dirs.append(d)
        return d

    with patch("latex2ufdissertation.pipeline.resolve.tempfile.mkdtemp", side_effect=spy_mkdtemp):
        with pytest.raises(UnreadableInput):
            resolve(str(src_zip))

    # All tmp dirs the spy recorded must have been removed.
    for d in created_dirs:
        assert not Path(d).exists(), f"temp dir leaked: {d}"


# ---------------------------------------------------------------------------
# Security: git URL allowlist (item 3)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/user/repo.git",
        "https://github.com/user/repo",
        "https://www.github.com/user/repo.git",
        "https://gitlab.com/user/repo.git",
        "git@github.com:user/repo.git",
        "git@gitlab.com:user/repo.git",
        "ssh://github.com/user/repo.git",  # ssh:// clone form is accepted
        "ssh://gitlab.com/user/repo.git",
    ],
)
def test_git_url_accepted(url):
    assert _looks_like_git_url(url), f"expected accepted: {url}"


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com.evil.com/x/r.git",  # subdomain bypass
        "https://169.254.169.254/x.git",  # IMDS IP literal
        "http://github.com/x/r.git",  # http not https
        "https://evil.com/x/r.git",  # arbitrary host
        "git@evil.com:user/repo.git",  # scp form with non-allowlist host
        "ssh://evil.com/x.git",  # ssh:// to non-allowlisted host
        "https://evil.com@github.com/x/r.git",  # userinfo bypass — creds forwarded to git
        "https://user:pass@github.com/x/r.git",  # embedded credentials
        "/local/path",  # local path
        "./relative",  # relative path
        "github.com/user/repo",  # no scheme
    ],
)
def test_git_url_rejected(url):
    assert not _looks_like_git_url(url), f"expected rejected: {url}"


def test_stem_for_output_git_dotgit(tmp_path):
    """stem_for_output must still work for accepted git URLs."""
    from latex2ufdissertation.pipeline.resolve import stem_for_output

    root = tmp_path
    assert stem_for_output("https://github.com/user/myrepo.git", root) == "myrepo"
    assert stem_for_output("git@github.com:user/myrepo.git", root) == "myrepo"
    assert stem_for_output("https://github.com/user/myrepo", root) == "myrepo"


# ---------------------------------------------------------------------------
# Security: _safe_extract helper (item 7 shared helper)
# ---------------------------------------------------------------------------


def test_safe_extract_rejects_traversal(tmp_path):
    """_safe_extract must reject zip members that escape dest."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil.tex", "bad")
    buf.seek(0)
    with zipfile.ZipFile(buf) as zf:
        with pytest.raises(UnreadableInput, match="zip-slip"):
            _safe_extract(zf, tmp_path)


def test_safe_extract_allows_valid_members(tmp_path):
    """_safe_extract must extract legitimate members without error."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("subdir/file.tex", "content")
    buf.seek(0)
    with zipfile.ZipFile(buf) as zf:
        _safe_extract(zf, tmp_path)
    assert (tmp_path / "subdir" / "file.tex").read_text() == "content"

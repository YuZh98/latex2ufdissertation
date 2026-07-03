import io
import subprocess
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from latex2ufdissertation.pipeline.resolve import (
    MAX_MEMBER_COUNT,
    MAX_TOTAL_UNCOMPRESSED,
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


# ---------------------------------------------------------------------------
# Mutant killers — GROUP 1 (resolve.py)
# ---------------------------------------------------------------------------


def test_git_url_scp_form_no_colon_is_false():
    """G1a: 'git@hostname-only' (scp form, no colon) must be False.

    Kills mutant: `if colon == -1: return False` -> `return True`.
    The allowlist check never executes when the colon is absent — so a
    SSRF-style bare hostname would pass straight through with the mutant.
    """
    assert _looks_like_git_url("git@hostname-only") is False
    # Extra: a valid scp host without the repo path separator must also fail.
    assert _looks_like_git_url("git@github.com") is False


def test_git_url_empty_host_https_is_false():
    """G1b: https:///path and https:// (empty host) must be False.

    Kills mutant: `if not host: return False` -> `return True`.
    urlparse("https:///path").hostname is None; without the None-check
    the code would fall through to the allowlist membership test and
    `None in _HTTPS_ALLOWED_HOSTS` evaluates to False by accident — but
    the mutant (`return True`) bypasses the allowlist entirely.
    """
    assert _looks_like_git_url("https:///path") is False
    assert _looks_like_git_url("https://") is False


def test_git_url_valueerror_input_is_false():
    """G1c: A URL that makes urlparse() raise ValueError must return False.

    'https://[::1' (unterminated IPv6 bracket) raises ValueError in urlparse.
    Kills mutant: `except ValueError: return False` -> `return True`.
    Verified empirically: urlparse('https://[::1') raises ValueError.
    """
    assert _looks_like_git_url("https://[::1") is False


def test_safe_extract_skips_macosx_but_still_extracts_later_members(tmp_path):
    """G1d: A zip whose FIRST member is __MACOSX/foo must still extract main.tex.

    Kills two mutants:
    - `continue` -> `break` (ID?): break on __MACOSX drops all subsequent members.
    - `or` -> `and` in the filter predicate: __MACOSX member would NOT be skipped.

    Assertion 1 (continue->break killer): main.tex is extracted.
    Assertion 2 (or->and killer): __MACOSX directory is NOT extracted.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # __MACOSX member FIRST, then a legitimate member.
        zf.writestr("__MACOSX/foo", "mac metadata")
        zf.writestr("main.tex", r"\documentclass{ufdissertation}")
    buf.seek(0)
    dest = tmp_path / "out"
    dest.mkdir()
    with zipfile.ZipFile(buf) as zf:
        _safe_extract(zf, dest)

    # continue->break killer: the member after the skip must still be extracted.
    assert (dest / "main.tex").exists(), "main.tex was not extracted after __MACOSX skip"
    # or->and killer: the __MACOSX directory must NOT be present in the output.
    assert not (dest / "__MACOSX").exists(), "__MACOSX was incorrectly extracted"


def test_safe_extract_skips_ds_store_but_still_extracts(tmp_path):
    """G1d (extra): a zip with a .DS_Store member followed by main.tex
    must still extract main.tex and must NOT produce a .DS_Store file.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("subdir/.DS_Store", "mac store")
        zf.writestr("main.tex", r"\documentclass{ufdissertation}")
    buf.seek(0)
    dest = tmp_path / "out2"
    dest.mkdir()
    with zipfile.ZipFile(buf) as zf:
        _safe_extract(zf, dest)

    assert (dest / "main.tex").exists()
    assert not (dest / "subdir" / ".DS_Store").exists()


def test_clone_git_check_false_mutant_raises_unreadable_input():
    """G1e: _clone_git must raise UnreadableInput when git exits non-zero.

    The existing test patches with side_effect=CalledProcessError (always raises)
    which does NOT distinguish check=True vs check=False — it kills nothing.

    This test uses a side_effect function that ONLY raises CalledProcessError
    when `check=True` is passed, exactly mirroring the real subprocess.run
    contract.  On real code (check=True), it raises → UnreadableInput.
    Under the mutant (check=False), it returns CompletedProcess(128) → no
    UnreadableInput → the assertion fails.
    """

    def fake_run(cmd, *args, check=False, **kwargs):
        if check:
            raise subprocess.CalledProcessError(returncode=128, cmd=cmd, stderr=b"fatal")
        return subprocess.CompletedProcess(args=cmd, returncode=128)

    with patch(
        "latex2ufdissertation.pipeline.resolve.subprocess.run",
        side_effect=fake_run,
    ):
        with pytest.raises(UnreadableInput):
            resolve("https://github.com/fake/repo.git")


# ---------------------------------------------------------------------------
# Security: zip-bomb caps (uncompressed size + member count)
# ---------------------------------------------------------------------------


class _StubZip:
    """Duck-typed stand-in for zipfile.ZipFile exposing only the surface
    _safe_extract touches. `extract` asserts it is never called so a test can
    prove the cap trips on INSPECTION, before any member is written."""

    def __init__(self, infos: list[zipfile.ZipInfo]):
        self._infos = infos

    def infolist(self) -> list[zipfile.ZipInfo]:
        return self._infos

    def namelist(self) -> list[str]:
        return [i.filename for i in self._infos]

    def extract(self, member, path=None):  # pragma: no cover - must not run
        raise AssertionError("extract() called despite cap breach")


def test_safe_extract_rejects_oversized_uncompressed(tmp_path):
    """A zip whose declared total uncompressed size exceeds the cap must be
    refused on inspection — no 50 MB payload is written to disk."""
    info = zipfile.ZipInfo("bomb.tex")
    info.file_size = MAX_TOTAL_UNCOMPRESSED + 1
    with pytest.raises(UnreadableInput, match="uncompressed"):
        _safe_extract(_StubZip([info]), tmp_path)


def test_safe_extract_rejects_too_many_members(tmp_path):
    """A zip declaring more than MAX_MEMBER_COUNT members must be refused."""
    infos = [zipfile.ZipInfo(f"f{i}.tex") for i in range(MAX_MEMBER_COUNT + 1)]
    with pytest.raises(UnreadableInput, match="member"):
        _safe_extract(_StubZip(infos), tmp_path)


def test_safe_extract_oversized_maps_to_exit_code_2(tmp_path):
    """The breach must surface as unreadable_input (fatal-input exit code 2),
    not a crash/traceback."""
    info = zipfile.ZipInfo("bomb.tex")
    info.file_size = MAX_TOTAL_UNCOMPRESSED + 1
    with pytest.raises(UnreadableInput) as exc:
        _safe_extract(_StubZip([info]), tmp_path)
    assert exc.value.exit_reason == "unreadable_input"


def test_safe_extract_allows_at_cap_boundary(tmp_path):
    """A zip exactly at the caps must still extract — the guard must not be
    off-by-one and reject legitimate dissertations."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("proj/main.tex", r"\documentclass{ufdissertation}")
    buf.seek(0)
    dest = tmp_path / "out"
    dest.mkdir()
    with zipfile.ZipFile(buf) as zf:
        _safe_extract(zf, dest)
    assert (dest / "proj" / "main.tex").exists()


def test_zip_bomb_caps_are_named_constants():
    """Caps must be named constants in the config layer, not magic numbers."""
    assert MAX_TOTAL_UNCOMPRESSED == 200 * 1024 * 1024
    assert MAX_MEMBER_COUNT == 10_000


def test_resolve_zip_bomb_refused_end_to_end(tmp_path):
    """resolve() must refuse a many-member zip via the shared cap and not
    leave the extraction dir populated with the payload."""
    import tempfile as _tempfile

    src_zip = tmp_path / "bomb.zip"
    with zipfile.ZipFile(src_zip, "w") as zf:
        for i in range(MAX_MEMBER_COUNT + 1):
            zf.writestr(f"f{i}", "")

    created_dirs: list[str] = []
    real_mkdtemp = _tempfile.mkdtemp

    def spy_mkdtemp(**kwargs):
        d = real_mkdtemp(**kwargs)
        created_dirs.append(d)
        return d

    with patch("latex2ufdissertation.pipeline.resolve.tempfile.mkdtemp", side_effect=spy_mkdtemp):
        with pytest.raises(UnreadableInput, match="member"):
            resolve(str(src_zip))

    for d in created_dirs:
        assert not Path(d).exists(), f"temp dir leaked after cap breach: {d}"


# ---------------------------------------------------------------------------
# Security: git clone credential-prompt hang (Finding 44)
# ---------------------------------------------------------------------------


def test_clone_git_disables_credential_prompt(tmp_path):
    """_clone_git must close stdin and export GIT_TERMINAL_PROMPT=0 so a
    private/typo'd URL fails fast instead of blocking on a credential prompt.
    PATH must be preserved (env merged, not clobbered)."""
    captured: dict = {}

    def fake_run(cmd, *args, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    with patch("latex2ufdissertation.pipeline.resolve.subprocess.run", side_effect=fake_run):
        resolve("https://github.com/fake/repo.git")

    assert captured.get("stdin") is subprocess.DEVNULL
    env = captured.get("env")
    assert env is not None, "clone must pass an explicit env"
    assert env.get("GIT_TERMINAL_PROMPT") == "0"
    assert "PATH" in env, "PATH must be preserved, not clobbered"


def test_resolve_zip_cleanup_removes_temp_dir(tmp_path):
    """G1f: resolve() cleanup() must actually remove the temp extraction dir.

    Kills mutant: cleanup lambda -> `lambda: None` (leaks the temp dir).
    We spy on mkdtemp to record the created temp dir, then call cleanup()
    and assert the dir is gone.
    """
    import tempfile as _tempfile

    src_zip = tmp_path / "legit.zip"
    with zipfile.ZipFile(src_zip, "w") as zf:
        # Flat zip (no single top wrapper dir) so root IS the temp dir.
        zf.writestr("main.tex", r"\documentclass{ufdissertation}")

    created_dirs: list[str] = []
    real_mkdtemp = _tempfile.mkdtemp

    def spy_mkdtemp(**kwargs):
        d = real_mkdtemp(**kwargs)
        created_dirs.append(d)
        return d

    with patch("latex2ufdissertation.pipeline.resolve.tempfile.mkdtemp", side_effect=spy_mkdtemp):
        root, cleanup = resolve(str(src_zip))

    assert len(created_dirs) == 1, "expected exactly one temp dir to be created"
    temp_dir = Path(created_dirs[0])
    assert temp_dir.exists(), "temp dir must exist before cleanup()"

    cleanup()

    assert not temp_dir.exists(), (
        f"cleanup() did not remove temp dir: {temp_dir} — likely lambda: None mutant"
    )

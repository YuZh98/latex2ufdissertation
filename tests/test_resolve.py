import subprocess
import zipfile
from unittest.mock import patch

import pytest

from latex2ufdissertation.pipeline.resolve import RESOLVE_GIT_TIMEOUT, _looks_like_git_url, resolve
from latex2ufdissertation.pipeline.types import ConverterError, UnreadableInput


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


def test_resolve_git_url_format_detection():
    assert _looks_like_git_url("https://github.com/u/r.git")
    assert _looks_like_git_url("git@github.com:u/r.git")
    assert not _looks_like_git_url("/local/path")
    assert not _looks_like_git_url("./relative")


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

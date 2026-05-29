import subprocess
import zipfile
from unittest.mock import patch

import pytest

from latex2ufdissertation.pipeline.resolve import (
    RESOLVE_GIT_TIMEOUT,
    _looks_like_git_url,
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

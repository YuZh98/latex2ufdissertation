import io
import zipfile
from unittest.mock import patch

import pytest

from latex2ufdissertation.pipeline.init import (
    BUNDLED_TEMPLATE_DIR,
    FETCH_MAX_BYTES,
    _fetch_remote,
    init_project,
)
from latex2ufdissertation.pipeline.types import ConverterError, UnreadableInput


def test_bundled_template_exists():
    assert BUNDLED_TEMPLATE_DIR.exists()
    assert (BUNDLED_TEMPLATE_DIR / "exampleMasterFile.tex").exists()


def test_init_uses_bundled_when_fetch_fails(tmp_path):
    target = tmp_path / "out"
    with patch(
        "latex2ufdissertation.pipeline.init._fetch_remote", side_effect=ConnectionError("offline")
    ):
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
    with patch("latex2ufdissertation.pipeline.init._fetch_remote", side_effect=ConnectionError):
        init_project(target)
    assert target.exists()


# ---------------------------------------------------------------------------
# Security: zip-slip in remote fetch (item 7)
# ---------------------------------------------------------------------------


def _make_zip_bytes(members: dict) -> bytes:
    """Build an in-memory zip with the given {member_name: content} dict."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in members.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_fetch_remote_zip_slip_rejected(tmp_path):
    """_fetch_remote must reject a zip with traversal members (zip-slip)."""
    evil_zip = _make_zip_bytes({"../evil.tex": "bad"})

    def fake_urlopen(req, timeout=None):
        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def read(self, n=-1):
                return evil_zip

        return _Resp()

    with patch("latex2ufdissertation.pipeline.init.urllib.request.urlopen", fake_urlopen):
        with pytest.raises(UnreadableInput, match="zip-slip"):
            _fetch_remote(tmp_path)


# ---------------------------------------------------------------------------
# Security: unbounded read cap (item 8)
# ---------------------------------------------------------------------------


def test_fetch_remote_rejects_oversized_response(tmp_path):
    """Downloads exceeding FETCH_MAX_BYTES must raise ConverterError."""

    def fake_urlopen(req, timeout=None):
        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def read(self, n=-1):
                # Return FETCH_MAX_BYTES + 1 bytes to trigger the cap.
                return b"x" * (FETCH_MAX_BYTES + 1)

        return _Resp()

    with patch("latex2ufdissertation.pipeline.init.urllib.request.urlopen", fake_urlopen):
        with pytest.raises(ConverterError, match="too large"):
            _fetch_remote(tmp_path)


def test_fetch_remote_constant_defined():
    """FETCH_MAX_BYTES must be a named constant (no magic numbers)."""
    assert isinstance(FETCH_MAX_BYTES, int)
    assert FETCH_MAX_BYTES == 50 * 1024 * 1024  # 50 MB


# ---------------------------------------------------------------------------
# Security: zip-bomb cap on --init template extraction (Finding 41)
# ---------------------------------------------------------------------------


def test_fetch_remote_rejects_zip_bomb_member_count(tmp_path):
    """The --init template extraction must inherit the shared extraction cap:
    a template zip declaring more than MAX_MEMBER_COUNT members is refused."""
    from latex2ufdissertation.pipeline.resolve import MAX_MEMBER_COUNT

    bomb_zip = _make_zip_bytes({f"f{i}": "" for i in range(MAX_MEMBER_COUNT + 1)})

    def fake_urlopen(req, timeout=None):
        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def read(self, n=-1):
                return bomb_zip

        return _Resp()

    with patch("latex2ufdissertation.pipeline.init.urllib.request.urlopen", fake_urlopen):
        with pytest.raises(UnreadableInput, match="member"):
            _fetch_remote(tmp_path)

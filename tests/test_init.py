from unittest.mock import patch

import pytest

from pipeline.init import BUNDLED_TEMPLATE_DIR, init_project
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

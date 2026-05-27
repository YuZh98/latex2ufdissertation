"""Smoke tests for the CLI argument-parsing layer."""

from __future__ import annotations

import pytest

from latex2ufdissertation.cli import (
    DEMO_GITHUB_URL,
    _build_parser,
    _print_demo_location,
    main,
)


def test_parser_accepts_demo_flag() -> None:
    args = _build_parser().parse_args(["--demo"])
    assert args.demo is True
    assert args.input is None


def test_print_demo_location_returns_zero(capsys: pytest.CaptureFixture[str]) -> None:
    rc = _print_demo_location()
    assert rc == 0
    out = capsys.readouterr().out
    assert DEMO_GITHUB_URL in out
    assert "demo dissertation" in out.lower()


def test_main_demo_flag_short_circuits(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["--demo"])
    assert rc == 0
    assert DEMO_GITHUB_URL in capsys.readouterr().out


def test_main_without_input_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main([])
    assert rc == 2
    assert "INPUT required" in capsys.readouterr().err


def test_version_flag_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0

"""Determinism pinning test.

CONTRIBUTING.md and docs/spec-v1.0.md promise byte-identical JSON
output across two consecutive runs on the same input. This test
exercises the contract on the demo dissertation via --json (validate-only,
the default), captures stdout twice, asserts equality.
"""

from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from latex2ufdissertation.cli import main

DEMO = Path(__file__).resolve().parent.parent / "examples" / "demo_dissertation"


def _run_dry_json() -> tuple[int, str]:
    """Run the CLI in validate-only + JSON mode, return (exit_code, stdout)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main(["--json", str(DEMO)])
    return rc, out.getvalue()


@pytest.mark.skipif(not DEMO.is_dir(), reason="demo dissertation not present in this checkout")
def test_json_output_is_byte_identical_across_consecutive_runs():
    rc1, out1 = _run_dry_json()
    rc2, out2 = _run_dry_json()
    assert rc1 == rc2
    assert out1 == out2, "two consecutive --json runs produced divergent stdout"
    # Sanity: the payload must be non-trivial JSON, not an empty string.
    assert out1.strip().startswith("{")
    assert "schema_version" in out1

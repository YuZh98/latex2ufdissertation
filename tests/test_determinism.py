"""Determinism pinning test (placeholder).

CONTRIBUTING.md promises a regression test asserting byte-identical JSON
output across two consecutive runs on the same input. The v1.0 spec
elevates this to a behavior contract (see docs/spec-v1.0.md, Behavior /
Determinism). This file is the placeholder gate so the promise is not
policy fiction; it will be replaced with a real assertion once the
JSON-output surface and the demo fixture are wired together end-to-end.
"""

from __future__ import annotations

import pytest


@pytest.mark.xfail(
    strict=False,
    reason=(
        "Determinism pinning not yet wired. Once `latex2ufdissertation "
        "--json tests/fixtures/demo_dissertation/` produces a stable JSON "
        "shape, this test should run it twice and assert byte equality."
    ),
)
def test_json_output_is_byte_identical_across_consecutive_runs() -> None:
    raise NotImplementedError

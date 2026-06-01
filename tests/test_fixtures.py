"""Snapshot tests for synthetic broken-input fixtures.

Each fixture under tests/fixtures/<rule_id>/ contains:
- input/         a minimal project that violates exactly one UF-* rule
- expected_findings.json   the canonical JSON payload (format_json)
- expected_report.txt      the canonical human-readable report (format_human)

The test runs the validator's source-layer checks against input/main.tex,
then compares the live emitter output to the snapshots. Mismatches fail
the test with a hint at the regeneration command.

To regenerate snapshots after an intentional output change:

    LATEX2UFD_REGEN_FIXTURES=1 pytest tests/test_fixtures.py
"""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

import pytest

from latex2ufdissertation.pipeline.checks import run_checks
from latex2ufdissertation.pipeline.report import format_human, format_json
from latex2ufdissertation.pipeline.types import Issues

FIXTURES_DIR = Path(__file__).parent / "fixtures"
REGEN = os.environ.get("LATEX2UFD_REGEN_FIXTURES") == "1"


def _fixture_dirs() -> list[Path]:
    if not FIXTURES_DIR.is_dir():
        return []
    # Only include fixtures that have a main.tex entry point for the source-layer
    # checks. PDF-only fixtures (e.g. uf_f2_pdf_font_violation) have no main.tex
    # and are tested directly in test_pdf_checks.py.
    return sorted(
        d for d in FIXTURES_DIR.iterdir() if d.is_dir() and (d / "input" / "main.tex").is_file()
    )


def _run_fixture(fixture: Path) -> tuple[dict, str]:
    input_dir = fixture / "input"
    main_tex = input_dir / "main.tex"
    issues = Issues(input_path="<INPUT>")
    run_checks(main_tex, input_dir, issues)
    return format_json(issues), format_human(issues)


@pytest.mark.parametrize("fixture", _fixture_dirs(), ids=lambda p: p.name)
def test_fixture_snapshots(fixture: Path):
    actual_json, actual_human = _run_fixture(fixture)
    expected_json_path = fixture / "expected_findings.json"
    expected_report_path = fixture / "expected_report.txt"

    if REGEN:
        expected_json_path.write_text(
            json.dumps(actual_json, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        expected_report_path.write_text(actual_human, encoding="utf-8")
        pytest.skip(f"regenerated snapshots for {fixture.name}")

    expected_json = json.loads(expected_json_path.read_text(encoding="utf-8"))
    expected_report = expected_report_path.read_text(encoding="utf-8")

    # Pre-check by rule_id multiset (not set), so a regression where two
    # findings for the same rule collapse into one fails this gate with a
    # clear message before the full-dict equality below. The full-dict
    # assertion is the stronger gate; this is the hint a human reads first.
    assert Counter(f["rule_id"] for f in actual_json["findings"]) == Counter(
        f["rule_id"] for f in expected_json["findings"]
    ), f"{fixture.name}: rule_id multiset diverged from snapshot"

    assert actual_json == expected_json, (
        f"{fixture.name}: JSON snapshot mismatch. "
        f"To regenerate: LATEX2UFD_REGEN_FIXTURES=1 pytest tests/test_fixtures.py"
    )
    assert actual_human == expected_report, (
        f"{fixture.name}: human report mismatch. "
        f"To regenerate: LATEX2UFD_REGEN_FIXTURES=1 pytest tests/test_fixtures.py"
    )


def test_fixtures_dir_is_populated():
    """Gate that the fixtures directory is non-empty so an accidental rm -rf
    doesn't silently turn the parameterized test into a no-op pass.
    """
    assert _fixture_dirs(), (
        "tests/fixtures/ is empty — the parameterized snapshot test would "
        "report 0 cases and exit clean. Add at least one fixture."
    )

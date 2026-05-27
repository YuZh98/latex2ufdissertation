"""Drift tests: the rule registry and the catalog in docs/uf-rules.md
must enumerate exactly the same set of UF-* identifiers."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from latex2ufdissertation.pipeline.rules import (
    BOTH,
    EXIT_REASONS,
    MUST_FIX,
    PDF,
    REVIEW,
    RULES,
    SOURCE,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG = REPO_ROOT / "docs" / "uf-rules.md"


def _catalog_rule_ids() -> set[str]:
    text = CATALOG.read_text(encoding="utf-8")
    # Each rule heading reads "### UF-XYZ — Title". Match the ID.
    return set(re.findall(r"^###\s+(UF-[A-Z]\d+)\b", text, re.MULTILINE))


def test_catalog_and_registry_enumerate_the_same_rules():
    cat = _catalog_rule_ids()
    reg = set(RULES.keys())
    missing_from_registry = cat - reg
    missing_from_catalog = reg - cat
    assert not missing_from_registry, (
        f"rule IDs in docs/uf-rules.md but not in rules.RULES: {sorted(missing_from_registry)}"
    )
    assert not missing_from_catalog, (
        f"rule IDs in rules.RULES but not in docs/uf-rules.md: {sorted(missing_from_catalog)}"
    )


@pytest.mark.parametrize("rule_id", sorted(RULES.keys()))
def test_every_rule_has_consistent_metadata(rule_id):
    rule = RULES[rule_id]
    assert rule.id == rule_id
    assert rule.severity in (MUST_FIX, REVIEW)
    assert rule.layer in (SOURCE, PDF, BOTH)
    assert rule.title and rule.title.strip()
    assert rule.source_url.startswith("https://")


def test_exit_reason_enum_is_non_empty_and_finite():
    assert "clean" in EXIT_REASONS
    assert "must_fix_present" in EXIT_REASONS
    assert "missing_toolchain" in EXIT_REASONS
    # Sanity bound: we don't want the enum sprawling.
    assert 5 <= len(EXIT_REASONS) <= 12

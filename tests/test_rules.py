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

# Catalog uses freeform layer wording ("source primary, pdf backup",
# "source+pdf", "source", "pdf", ...). Canonicalize to the registry's
# layer literals (SOURCE / PDF / BOTH).
_LAYER_CANON = {
    "source": SOURCE,
    "pdf": PDF,
    "both": BOTH,
    "source primary": SOURCE,
    "source primary, pdf backup": BOTH,
    "source content check": SOURCE,
    "source content check, pdf backup": BOTH,
    "content check, low-confidence": SOURCE,
    "content check": SOURCE,
    "pdf, network-dependent": PDF,
    "pdf only": PDF,
}


def _parse_catalog() -> dict[str, dict[str, str]]:
    """Walk docs/uf-rules.md and extract per-rule metadata blocks.

    Returns {rule_id: {severity: ..., layer: ...}}. Each rule heading is
    `### UF-XYZ — Title`; the fields live in the bulleted list directly
    below the heading.
    """
    text = CATALOG.read_text(encoding="utf-8")
    blocks: dict[str, dict[str, str]] = {}
    # Split on rule headings; each chunk is heading + body up to next heading.
    parts = re.split(r"^###\s+(UF-[A-Z]\d+)\b[^\n]*\n", text, flags=re.MULTILINE)
    # First element is the preamble; pairs follow.
    for i in range(1, len(parts), 2):
        rule_id = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        meta: dict[str, str] = {}
        sev = re.search(r"-\s*\*\*Severity:\*\*\s*([^\n]+)", body)
        lay = re.search(r"-\s*\*\*Layer:\*\*\s*([^\n]+)", body)
        if sev:
            meta["severity"] = sev.group(1).strip().split()[0].lower()
        if lay:
            meta["layer"] = lay.group(1).strip().lower()
        blocks[rule_id] = meta
    return blocks


def test_catalog_and_registry_enumerate_the_same_rules():
    cat = set(_parse_catalog().keys())
    reg = set(RULES.keys())
    missing_from_registry = cat - reg
    missing_from_catalog = reg - cat
    assert not missing_from_registry, (
        f"rule IDs in docs/uf-rules.md but not in rules.RULES: {sorted(missing_from_registry)}"
    )
    assert not missing_from_catalog, (
        f"rule IDs in rules.RULES but not in docs/uf-rules.md: {sorted(missing_from_catalog)}"
    )


def test_catalog_severity_matches_registry():
    parsed = _parse_catalog()
    mismatches: list[str] = []
    for rule_id, meta in parsed.items():
        if "severity" not in meta:
            continue  # tolerated: a few rules may use shorthand in the catalog
        # Catalog wording variants → canonical severity literals.
        cat_sev = "must-fix" if meta["severity"].startswith("must") else "review"
        if RULES[rule_id].severity != cat_sev:
            mismatches.append(f"{rule_id}: catalog={cat_sev}, registry={RULES[rule_id].severity}")
    assert not mismatches, "severity drift between catalog and registry: " + "; ".join(mismatches)


def test_catalog_layer_matches_registry():
    parsed = _parse_catalog()
    mismatches: list[str] = []
    for rule_id, meta in parsed.items():
        if "layer" not in meta:
            continue
        canon = _LAYER_CANON.get(meta["layer"])
        if canon is None:
            # Unknown wording — flag so we extend _LAYER_CANON rather than silently pass.
            mismatches.append(f"{rule_id}: unrecognized catalog layer wording {meta['layer']!r}")
            continue
        if RULES[rule_id].layer != canon:
            mismatches.append(
                f"{rule_id}: catalog={meta['layer']!r} (canonical {canon}), "
                f"registry={RULES[rule_id].layer}"
            )
    assert not mismatches, "layer drift between catalog and registry: " + "; ".join(mismatches)


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

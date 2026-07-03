"""Pin the frozen public API surface and the fatal exit-reason enum.

The public API is enumerated in ``latex2ufdissertation.__all__`` (spec §7.1
hard-rule 11). ``UnsupportedTemplate`` / ``unsupported_template`` were removed
when old-template refusal was dropped (spec hard-rule 9); these tests pin that
they stay gone so the reserved names cannot silently creep back before the
v1.0 freeze.
"""

from __future__ import annotations

import latex2ufdissertation
from latex2ufdissertation.pipeline.rules import EXIT_REASONS

_EXPECTED_PUBLIC_API = {
    "ConverterError",
    "Finding",
    "Issues",
    "MissingToolchain",
    "RULES",
    "Rule",
    "ThesisInput",
    "UnreadableInput",
    "__version__",
    "run_checks",
    "run_pdf_checks",
}


def test_public_api_export_list_is_frozen() -> None:
    assert set(latex2ufdissertation.__all__) == _EXPECTED_PUBLIC_API


def test_unsupported_template_is_not_exported() -> None:
    assert "UnsupportedTemplate" not in latex2ufdissertation.__all__
    assert not hasattr(latex2ufdissertation, "UnsupportedTemplate")


def test_unsupported_template_exit_reason_is_removed() -> None:
    assert "unsupported_template" not in EXIT_REASONS

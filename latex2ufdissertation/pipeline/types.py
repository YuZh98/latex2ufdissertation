"""Shared types for the latex2ufdissertation pipeline."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

from latex2ufdissertation.pipeline.rules import (
    EXIT_REASON_CLEAN,
    EXIT_REASONS,
    MUST_FIX,
    REVIEW,
    RULES,
)


class ConverterError(Exception):
    """Fatal failure raised from within the pipeline. cli.main() catches and
    exits non-zero with a clean message instead of a traceback. Subclasses
    carry the exit_reason that the JSON `summary.exit_reason` field reports.
    """

    exit_reason: str = "compile_failure"


class UnreadableInput(ConverterError):
    exit_reason = "unreadable_input"


class UnsupportedTemplate(ConverterError):
    exit_reason = "unsupported_template"


class ThesisInput(ConverterError):
    exit_reason = "thesis_input"


class MissingToolchain(ConverterError):
    exit_reason = "missing_toolchain"


@dataclass(frozen=True)
class Finding:
    """One rule violation, as emitted by a check and consumed by the
    report formatter. Shape is frozen at v1.0 per docs/spec-v1.0.md §5.
    """

    severity: str
    rule_id: str
    layer: str
    location: str
    observed: str | None
    required: str | None
    fix_hint: str | None
    source_url: str


@dataclass
class Issues:
    """Run-state collector: every check appends a Finding via `add(...)`.
    `cli.main` reads `findings`, `input_path`, etc. when emitting the
    human-readable or JSON report at the end of the run.
    """

    findings: list[Finding] = field(default_factory=list)
    input_path: str | None = None
    main_tex: str | None = None
    template_version: str | None = None
    exit_reason: str = EXIT_REASON_CLEAN

    def add(
        self,
        rule_id: str,
        *,
        location: str = "",
        observed: str | None = None,
        required: str | None = None,
        fix_hint: str | None = None,
    ) -> None:
        """Resolve severity, layer, source_url, and default fix_hint from
        RULES[rule_id]. Per-finding `fix_hint` (when provided) overrides
        the rule-level default. Diagnostic line goes to stderr so --json
        stdout stays a single JSON document.
        """
        rule = RULES[rule_id]  # KeyError on unknown ID is the right failure mode
        finding = Finding(
            severity=rule.severity,
            rule_id=rule.id,
            layer=rule.layer,
            location=location,
            observed=observed,
            required=required,
            fix_hint=fix_hint if fix_hint is not None else rule.fix_hint,
            source_url=rule.source_url,
        )
        self.findings.append(finding)
        loc = f" {location}" if location else ""
        print(f"  [{rule.severity}] {rule.id}{loc} — {observed or rule.title}", file=sys.stderr)

    def must_fix_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == MUST_FIX)

    def review_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == REVIEW)

    def set_exit_reason(self, reason: str) -> None:
        if reason not in EXIT_REASONS:
            raise ValueError(f"unknown exit_reason: {reason!r}")
        self.exit_reason = reason

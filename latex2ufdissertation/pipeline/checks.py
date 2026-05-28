"""Source-layer validation checks for UF dissertations.

Each emit site calls `issues.add(rule_id="UF-XYZ", ...)`. Severity,
layer, source_url, and default fix_hint come from the rule registry
(rules.py). This module never decides "must-fix vs review"; that's the
registry's job.
"""

from __future__ import annotations

import re
from pathlib import Path

from latex2ufdissertation.pipeline.types import Issues

_DOCCLASS_RE = re.compile(r"\\documentclass(\[([^\]]*)\])?\{([^}]+)\}")
_REQUIRED_TOPLEVEL = (
    (r"\title", r"\title"),
    (r"\author", r"\author"),
    (r"\degreeType", r"\degreeType"),
    (r"\thesisType", r"\thesisType"),
    (r"\degreeYear", r"\degreeYear"),
    (r"\degreeMonth", r"\degreeMonth"),
    (r"\major", r"\major"),
    (r"\chair", r"\chair"),
)

# Catalog § UF-F14: \degreeMonth value must be one of these (per C2:41).
# Case-sensitive: UF writes the month with title-case capitalization on
# the abstract page.
_VALID_DEGREE_MONTHS = ("May", "August", "December")
_SETFILE_RULES = (
    (r"\setAcknowledgementsFile", (".tex",), "Acknowledgements"),
    (r"\setAbstractFile", (".tex",), "Abstract"),
    (r"\setReferenceFile", (".bib",), "Reference"),
    (r"\setBiographicalFile", (".tex",), "Biographical"),
)


def _strip_comments(text: str) -> str:
    return re.sub(r"(?m)(?<!\\)%[^\n]*", "", text)


def _has_command(nc: str, cmd: str) -> bool:
    # Allow LaTeX's optional bracketed argument between the command name and
    # the required braces (e.g. `\chair[Co-chair]{Chair}` per the UF
    # template), in addition to the bare `\cmd{...}` form.
    pat = re.escape(cmd) + r"\s*(?:\[[^\]]*\])?\s*\{[^}]*\S[^}]*\}"
    return re.search(pat, nc) is not None


def _setfile_arg(nc: str, cmd: str) -> str | None:
    pat = re.escape(cmd) + r"\s*\{([^}]+)\}"
    m = re.search(pat, nc)
    return m.group(1) if m else None


def run_checks(main_tex: Path, root: Path, issues: Issues) -> None:
    raw = main_tex.read_text(encoding="utf-8", errors="replace")
    nc = _strip_comments(raw)
    rel = str(main_tex.relative_to(root)) if main_tex.is_relative_to(root) else main_tex.name

    # UF-F13: documentclass must be ufdissertation
    m = _DOCCLASS_RE.search(nc)
    if not m or m.group(3) != "ufdissertation":
        observed = m.group(3) if m else "(no \\documentclass found)"
        issues.add(
            "UF-F13",
            location=rel,
            observed=f"\\documentclass{{{observed}}}",
            required="\\documentclass{ufdissertation}",
        )

    # UF-F14: required metadata macros (presence + non-empty argument).
    for cmd, label in _REQUIRED_TOPLEVEL:
        if not _has_command(nc, cmd):
            issues.add(
                "UF-F14",
                location=rel,
                observed=f"{label} missing or empty",
                required=f"{label}{{...}} with a non-empty argument",
            )

    # UF-F14: \degreeMonth value must be in the catalog enum (C2:41).
    month_match = re.search(
        r"\\degreeMonth\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}",
        nc,
    )
    if month_match:
        value = month_match.group(1).strip()
        if value and value not in _VALID_DEGREE_MONTHS:
            issues.add(
                "UF-F14",
                location=rel,
                observed=f"\\degreeMonth{{{value}}}",
                required=f"\\degreeMonth must be one of: {', '.join(_VALID_DEGREE_MONTHS)}",
            )

    # UF-F8 / UF-P1: \set*File macros + filesystem companions
    for cmd, suffixes, label in _SETFILE_RULES:
        arg = _setfile_arg(nc, cmd)
        if arg is None:
            issues.add(
                "UF-F8",
                location=rel,
                observed=f"{cmd} not set",
                required=f"{cmd}{{<{label.lower()}-file-stem>}}",
            )
            continue
        candidates = [root / arg] + [root / f"{arg}{s}" for s in suffixes]
        if not any(c.exists() for c in candidates):
            issues.add(
                "UF-P1",
                location=rel,
                observed=f"{cmd}{{{arg!r}}} but no file found in project root",
                required=f"{arg} (or {arg}{suffixes[0]}) exists in project root",
            )

    # UF-D1: editMode option (review tier — submission should not ship with it)
    if m and m.group(2) and "editMode" in m.group(2):
        issues.add(
            "UF-D1",
            location=rel,
            observed="editMode option present in \\documentclass",
            required="editMode removed before submission",
        )

    # UF-F3: explicit \fontsize{}{}\selectfont overrides. Template's \LoadClass[12pt]
    # (cls:1) sets the required 12-point default. Catalog also lists relative-size
    # commands (\small, \large, ...) as overrides but their legitimate use in
    # captions/headings makes naive scanning false-positive-prone — v0.1 detector
    # skips them (a separate follow-up will need body-vs-context analysis).
    # Loop variable named `f3m` to avoid shadowing the outer documentclass
    # match `m` which D3 reads later in this function.
    for f3m in re.finditer(r"\\fontsize\s*\{([^}]*)\}\s*\{([^}]*)\}\s*\\selectfont", nc):
        observed = f"\\fontsize{{{f3m.group(1)}}}{{{f3m.group(2)}}}\\selectfont"
        issues.add(
            "UF-F3",
            location=rel,
            observed=f"{observed} overrides template's 12pt default",
            required=(
                "no \\fontsize{...}{...}\\selectfont override in source (template's 12pt applies)"
            ),
        )

    # UF-F7: paragraph-indentation overrides. Template's \indentfirst (cls:203)
    # + \parindent=1cm (cls:1010) require first-line indent. Setting parindent
    # to zero (any unit) overrides this. Two LaTeX syntaxes covered separately:
    # \setlength{\parindent}{0...} and \parindent=0... assignment form.
    # Zero-detection guard: trailing `0` must be followed by either end-of-arg,
    # whitespace, or a known unit suffix — NOT a decimal point. This prevents
    # false-positives on `0.5em` (which starts with a `0` but is nonzero).
    _ZERO_UNIT = r"0(?:pt|in|em|ex|mm|cm|pc|sp)?\s*"
    _F7_REQUIRED = "no zero-\\parindent override in source (template's \\parindent=1cm applies)"
    for _ in re.finditer(
        r"\\setlength\s*\{?\s*\\parindent\s*\}?\s*\{\s*" + _ZERO_UNIT + r"\}",
        nc,
    ):
        issues.add(
            "UF-F7",
            location=rel,
            observed="\\setlength{\\parindent}{0pt} overrides template's 1cm parindent",
            required=_F7_REQUIRED,
        )
    for _ in re.finditer(
        r"\\parindent\s*=\s*" + _ZERO_UNIT + r"(?![.\d])",
        nc,
    ):
        issues.add(
            "UF-F7",
            location=rel,
            observed="\\parindent=0pt overrides template's 1cm parindent",
            required=_F7_REQUIRED,
        )

    # UF-F10: chapter scaffold. Catalog § F10 requires >=3 chapters per UF
    # S1 + S3 (introductory + main body + closing summary). Count \chapter{...}
    # calls in main.tex AND in any \include / \input target one level deep.
    # Deeper nesting deferred.
    _chapter_pat = re.compile(r"\\chapter\s*\{[^}]+\}")
    chapter_count = len(_chapter_pat.findall(nc))
    for included in re.findall(r"\\(?:include|input)\s*\{([^}]+)\}", nc):
        for candidate in (root / included, root / f"{included}.tex"):
            if candidate.exists() and candidate.is_file():
                included_nc = _strip_comments(
                    candidate.read_text(encoding="utf-8", errors="replace")
                )
                chapter_count += len(_chapter_pat.findall(included_nc))
                break
    if chapter_count < 3:
        chapters_word = "chapter" if chapter_count == 1 else "chapters"
        issues.add(
            "UF-F10",
            location=rel,
            observed=(
                f"{chapter_count} {chapters_word} "
                "(counted across main.tex + \\include / \\input files)"
            ),
            required="at least 3 chapters",
        )

    # UF-F9: singleton structure. UF requires exactly one each of: abstract,
    # ToC, reference list. Detector counts duplicate \set*File / \tableofcontents
    # / \bibliography calls and flags manual \chapter{ABSTRACT|REFERENCES} which
    # duplicate template-auto sections.
    _F9_SINGLETONS = (
        r"\setAbstractFile",
        r"\setReferenceFile",
        r"\tableofcontents",
        r"\bibliography",
    )
    for singleton in _F9_SINGLETONS:
        # Trailing (?![a-zA-Z]) prevents \tableofcontents from matching e.g.
        # a hypothetical \tableofcontentsFoo command.
        pat = re.escape(singleton) + r"(?![a-zA-Z])"
        count = len(re.findall(pat, nc))
        if count > 1:
            issues.add(
                "UF-F9",
                location=rel,
                observed=f"{singleton} called {count} times (must be singleton)",
                required=f"exactly one {singleton} call",
            )
    for manual_chapter in ("ABSTRACT", "REFERENCES"):
        pat = r"\\chapter\s*\{" + manual_chapter + r"\}"
        if re.search(pat, nc):
            issues.add(
                "UF-F9",
                location=rel,
                observed=(
                    f"\\chapter{{{manual_chapter}}} duplicates template's auto-generated section"
                ),
                required=(
                    f"remove \\chapter{{{manual_chapter}}}; "
                    "template handles this section automatically"
                ),
            )

    # UF-F11: heading-style overrides. Template enforces the 5-tier hierarchy
    # by construction via titlesec (cls:304-362, cls:797-806). Two override
    # patterns flagged in source:
    # 1. \titleformat{\chapter/section/subsection/subsubsection/paragraph}
    #    redefining the template-owned tier styles.
    # 2. \paragraph usage (discouraged per C4).
    # Manual heading impersonation (\textbf{\Large ...}) is subjective; v0.1
    # defers it. \section / \subsection / \subsubsection direct usage is the
    # template-conformant happy path (catalog explicit) and is NOT scanned.
    _F11_TIERS = (
        r"\chapter",
        r"\section",
        r"\subsection",
        r"\subsubsection",
        r"\paragraph",
    )
    for tier in _F11_TIERS:
        # Accept both \titleformat and the starred one-shot form \titleformat*.
        pat = r"\\titleformat\*?\s*\{" + re.escape(tier) + r"\}"
        if re.search(pat, nc):
            issues.add(
                "UF-F11",
                location=rel,
                observed=f"\\titleformat{{{tier}}} redefines template's heading style",
                required=(
                    "no \\titleformat redefinition of \\chapter / \\section / "
                    "\\subsection / \\subsubsection / \\paragraph "
                    "(template handles these)"
                ),
            )
    if re.search(r"\\paragraph\s*\{[^}]+\}", nc):
        issues.add(
            "UF-F11",
            location=rel,
            observed="\\paragraph{...} usage discouraged per C4",
            required="omit \\paragraph; use \\subsubsection or restructure",
        )

    # UF-F5: text-alignment overrides. Template's \raggedright (cls:171) is the
    # ragged-right behavior UF requires. \justifying and \justify both override
    # it. Allowlist: \sloppy and \sloppypar (per catalog § UF-F5 explicit note)
    # are line-breaking helpers, not alignment overrides — they aren't in this
    # scan, so they're silently ignored regardless of position. \raggedright
    # itself is also silent because we only look for the override commands.
    # Trailing (?![a-zA-Z]) ensures \justify does not match the \justify prefix
    # inside \justifying (which has its own match) or any \justifyFoo variant.
    for cmd in (r"\justifying", r"\justify"):
        for _ in re.finditer(re.escape(cmd) + r"(?![a-zA-Z])", nc):
            issues.add(
                "UF-F5",
                location=rel,
                observed=f"{cmd} overrides template's \\raggedright",
                required=(
                    "no \\justifying / \\justify override in source "
                    "(template's \\raggedright produces ragged-right)"
                ),
            )

    # UF-D2: non-LuaLaTeX compiler hint
    hint = re.search(r"%\s*!TEX\s+program\s*=\s*(pdflatex|xelatex)", raw)
    if hint:
        issues.add(
            "UF-D2",
            location=rel,
            observed=f"% !TEX program = {hint.group(1)}",
            required="% !TEX program = lualatex (or omit the directive)",
        )

    # UF-D3: overrideTitles / overrideChapters options. Template warns on use;
    # one finding per option found so a project that ships both gets both flags
    # (each option is independently a candidate for removal at submission time).
    if m and m.group(2):
        opts = [o.strip() for o in m.group(2).split(",")]
        for opt in ("overrideTitles", "overrideChapters"):
            if opt in opts:
                issues.add(
                    "UF-D3",
                    location=rel,
                    observed=f"{opt} option present in \\documentclass",
                    required=f"{opt} removed before submission",
                )

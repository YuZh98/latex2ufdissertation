"""Source-layer validation checks for UF dissertations.

Each emit site calls `issues.add(rule_id="UF-XYZ", ...)`. Severity,
layer, source_url, and default fix_hint come from the rule registry
(rules.py). This module never decides "must-fix vs review"; that's the
registry's job.
"""

from __future__ import annotations

import re
from pathlib import Path

from latex2ufdissertation.pipeline.rules import REVIEW, SOURCE
from latex2ufdissertation.pipeline.types import Issues, ThesisInput

# Cap on the number of \input / \include files walked when building the
# transitive override-scan set, as a guard against pathological / cyclic
# include graphs. A real dissertation is well under this.
_MAX_INCLUDE_FILES = 100

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
# All 8 \set*File macros defined in the UF class (cls:540-596), as
# (macro, companion-suffixes, label, required). `required` macros fire
# UF-F8 "not set" when absent; optional macros do not. UF-P1 (companion
# file must exist) applies to any macro present in source, required or not.
_SETFILE_RULES = (
    (r"\setAcknowledgementsFile", (".tex",), "Acknowledgements", True),
    (r"\setAbstractFile", (".tex",), "Abstract", True),
    (r"\setReferenceFile", (".bib",), "Reference", True),
    (r"\setBiographicalFile", (".tex",), "Biographical", True),
    (r"\setCopyrightFile", (".tex",), "Copyright", False),
    (r"\setDedicationFile", (".tex",), "Dedication", False),
    (r"\setAbbreviationsFile", (".tex",), "Abbreviations", False),
    (r"\setAppendixFile", (".tex",), "Appendix", False),
)


# Catalog § UF-F5: \rightskip zero-assignment patterns (re-justify vector).
# setlength form: value starts with 0 and contains no "fil" stretch component.
# {0pt} and {0pt plus 0pt} match; {0pt plus 1fil} does not (ragged reinforcement).
_F5_RIGHTSKIP_SETLENGTH = re.compile(r"\\setlength\s*\{\s*\\rightskip\s*\}\s*\{\s*0(?![^\\}]*fil)")
# Direct TeX assignment: \rightskip=0pt, \rightskip=\z@
# The (?![^\\}]*fil) guard excludes ragged-right glue (\rightskip=0pt plus 1fil
# and \rightskip=\z@ plus 1fil). Both the 0-value and \z@ branches carry the
# guard so that ragged-right reinforcement forms do not false-fire.
_F5_RIGHTSKIP_DIRECT = re.compile(r"\\rightskip\s*=\s*(?:0(?![^\\}]*fil)|\\z@(?![^\\}]*fil))")
# Space-separated assignment: \rightskip 0pt  (no equals sign)
# The (?!.*fil) guard excludes ragged-right glue (\rightskip 0pt plus 1fil).
_F5_RIGHTSKIP_SPACE = re.compile(r"\\rightskip\s+0(?![^\\}]*fil)")


_F2_SOURCE_FIX_HINT = (
    "Font override present; the UF template's newtx reload at "
    "\\begin{document} may neutralize it. The PDF layer confirms "
    "whether the rendered body is actually non-Times."
)

_F3_SOURCE_FIX_HINT = (
    "A \\fontsize{...}{...}\\selectfont may be legal localized sizing "
    "(e.g. on a title page or caption). The PDF layer confirms the "
    "rendered body-mode size."
)


def _resolve_within(base: Path, root: Path, arg: str) -> Path | None:
    """Resolve a macro-supplied path under *base*, returning it only if it stays
    inside the project *root*. Absolute paths and ``..``-traversals that escape
    the root return ``None`` (treated as not-found; the file is never read).
    The returned path is the unresolved ``base / arg`` so callers' existing
    ``relative_to`` / visited-set logic is unchanged; the containment check
    is performed on fully-resolved paths to handle symlinks correctly.
    """
    candidate = base / arg
    try:
        if not candidate.resolve().is_relative_to(root.resolve()):
            return None
    except Exception:
        return None
    return candidate


def _strip_comments(text: str) -> str:
    return re.sub(r"(?m)(?<!\\)%[^\n]*", "", text)


def _strip_verbatim(text: str) -> str:
    return re.sub(
        r"\\begin\{(verbatim\*?|Verbatim\*?|lstlisting|alltt|minted)\}.*?\\end\{\1\}",
        "",
        text,
        flags=re.DOTALL,
    )


def _clean(raw: str) -> str:
    # Strip verbatim BEFORE comments: a `%` inside a verbatim block must not
    # eat the block's \end{verbatim} (comment-first stripping corrupts the
    # block boundary). Single source of truth for the strip order.
    return _strip_comments(_strip_verbatim(raw))


# UF-F4 allowed scopes (catalog § UF-F4): line-spacing changes inside these
# environments are documented exceptions and must not trip the must-fix scan.
# Stripped (like verbatim) before the F4 override scan so a \singlespacing
# inside them is invisible to the detector.
_F4_ALLOWED_ENVS = (
    "longtable",
    "itemize",
    "table",
    "tabular",
    "caption",
    "figure",
    "thebibliography",
)
_F4_SCOPE_RE = re.compile(
    r"\\begin\{(" + "|".join(_F4_ALLOWED_ENVS) + r")\*?\}.*?\\end\{\1\*?\}",
    flags=re.DOTALL,
)


def _strip_f4_allowed_scopes(text: str) -> str:
    return _F4_SCOPE_RE.sub("", text)


def _collect_include_texts(nc: str, base: Path, root: Path, master: Path) -> list[tuple[str, str]]:
    """Transitively resolve \\input / \\include targets reachable from *nc*.

    Returns a list of (location, cleaned_text) for each distinct included file,
    where *location* is the path relative to *root* (mirroring the master's own
    display-relative `rel`). Files are resolved relative to *base* (the master's
    directory, LaTeX semantics); a visited-set keyed on the resolved path
    prevents cycles (seeded with the master so an include that loops back to
    the master is not re-scanned), and a hard cap guards pathological graphs.
    Include targets that escape the project root (absolute paths or
    ``..``-traversals) are silently skipped and never read.

    The master's own text is NOT included here — callers scan the master via
    `nc` directly so its location stays the display-relative master name.
    \\set*File companion targets are intentionally excluded (they are content
    files, not override-scan territory).
    """
    results: list[tuple[str, str]] = []
    visited: set[Path] = {master.resolve()}
    frontier = [nc]
    while frontier and len(visited) < _MAX_INCLUDE_FILES:
        current = frontier.pop()
        for included in re.findall(r"\\(?:include|input)\s*\{([^}]+)\}", current):
            for raw_arg in (included, f"{included}.tex"):
                candidate = _resolve_within(base, root, raw_arg)
                if candidate is None or not (candidate.exists() and candidate.is_file()):
                    continue
                resolved = candidate.resolve()
                if resolved in visited:
                    break
                visited.add(resolved)
                cleaned = _clean(candidate.read_text(encoding="utf-8", errors="replace"))
                loc = (
                    str(candidate.relative_to(root))
                    if candidate.is_relative_to(root)
                    else candidate.name
                )
                results.append((loc, cleaned))
                frontier.append(cleaned)
                break
    return results


def _has_command(nc: str, cmd: str) -> bool:
    # Allow LaTeX's optional bracketed argument between the command name and
    # the required braces (e.g. `\chair[Co-chair]{Chair}` per the UF
    # template), in addition to the bare `\cmd{...}` form.
    pat = re.escape(cmd) + r"\s*(?:\[[^\]]*\])?\s*\{[^}]*\S[^}]*\}"
    return re.search(pat, nc) is not None


def _setfile_arg(nc: str, cmd: str) -> str | None:
    # \set*File macros accept an optional [ext] bracket (cls:540-596),
    # e.g. \setAbstractFile[txt]{abs}; allow it before the {name} group
    # so the bracket form is not misread as "macro not set".
    pat = re.escape(cmd) + r"\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}"
    m = re.search(pat, nc)
    return m.group(1) if m else None


def run_checks(main_tex: Path, root: Path, issues: Issues) -> None:
    raw = main_tex.read_text(encoding="utf-8", errors="replace")
    nc = _clean(raw)
    rel = str(main_tex.relative_to(root)) if main_tex.is_relative_to(root) else main_tex.name
    # Companion / \input / bib / abstract files resolve relative to the master's
    # own directory (LaTeX semantics), not the workspace root — so a master in a
    # subdirectory finds its siblings. `root` is kept only for the display-relative
    # `rel`. When the master sits at the project root, `base == root`.
    base = main_tex.parent

    # Hard rule 8 (spec §6): master's theses are out of scope for v1.0. Parse
    # \thesisType{...} and refuse a thesis BEFORE any other check fires.
    thesis_match = re.search(r"\\thesisType\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}", nc)
    if thesis_match and thesis_match.group(1).strip().lower() == "thesis":
        raise ThesisInput(
            "master's theses are out of scope for v1.0; "
            "this tool validates UF dissertations (\\thesisType{Dissertation}) only"
        )

    # Override-scan corpus: the master (location = rel) plus every transitively
    # \input / \include'd file (location = its own path). Source-formatting
    # overrides (F1, F2, F3, F4, F5, F6, F7, F11) are scanned over ALL of these,
    # since students normally place them in preamble / chapter files. Preamble /
    # metadata checks (F13, F14, F8/P1, F9, D1/D2/D3) scan the master only.
    override_files: list[tuple[str, str]] = [(rel, nc)] + _collect_include_texts(
        nc, base, root, main_tex
    )

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
    for cmd, suffixes, label, required in _SETFILE_RULES:
        arg = _setfile_arg(nc, cmd)
        if arg is None:
            if required:
                issues.add(
                    "UF-F8",
                    location=rel,
                    observed=f"{cmd} not set",
                    required=f"{cmd}{{<{label.lower()}-file-stem>}}",
                )
                issues.add(
                    "UF-S2",
                    location=rel,
                    observed=f"{label} section absent",
                    required=f"{cmd}{{<{label.lower()}-file-stem>}} must be set",
                    fix_hint=(
                        f"{label} section absent — missing required sections "
                        "(Acknowledgements/Abstract/References/Biographical) "
                        "is among the most common UF rejection reasons."
                    ),
                )
            continue
        candidates = [
            c
            for raw in ([arg] + [f"{arg}{s}" for s in suffixes])
            if (c := _resolve_within(base, root, raw)) is not None
        ]
        existing = next((c for c in candidates if c.exists() and c.is_file()), None)
        if existing is None:
            issues.add(
                "UF-P1",
                location=rel,
                observed=f"{cmd}{{{arg!r}}} but no matching file found next to the master .tex",
                required=f"{arg} (or {arg}{suffixes[0]}) exists alongside the master .tex",
            )
        elif required:
            # Presence != content: a required companion that exists but holds no
            # non-whitespace content (after comments are stripped) is almost
            # certainly an unfilled stub. Advisory only (review) — the file is
            # present, so this is not a must-fix structural failure.
            content = _strip_comments(existing.read_text(encoding="utf-8", errors="replace"))
            if not content.strip():
                issues.add(
                    "UF-P1",
                    severity=REVIEW,
                    location=rel,
                    observed=f"{cmd}{{{arg!r}}} companion file exists but is empty",
                    required=f"fill {existing.name} with content before submitting",
                    fix_hint=(
                        "The companion file exists but contains no content — "
                        "fill it before submitting (an empty required section is "
                        "a likely rejection driver)."
                    ),
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
    # Scanned over the master AND every \input / \include'd file.
    for loc, text in override_files:
        for f3m in re.finditer(r"\\fontsize\s*\{([^}]*)\}\s*\{([^}]*)\}\s*\\selectfont", text):
            observed = f"\\fontsize{{{f3m.group(1)}}}{{{f3m.group(2)}}}\\selectfont"
            issues.add(
                "UF-F3",
                severity=REVIEW,
                layer=SOURCE,
                location=loc,
                observed=f"{observed} overrides template's 12pt default",
                required=(
                    "no \\fontsize{...}{...}\\selectfont override in source "
                    "(template's 12pt applies)"
                ),
                fix_hint=_F3_SOURCE_FIX_HINT,
            )

    # UF-F7: paragraph-indentation overrides. Template's \indentfirst (cls:203)
    # + \parindent=1cm (cls:1010) require first-line indent. Setting parindent
    # to zero (any unit) overrides this. Two LaTeX syntaxes covered separately:
    # \setlength{\parindent}{0...} and \parindent=0... assignment form.
    # Zero-detection guard: trailing `0` must be followed by either end-of-arg,
    # whitespace, or a known unit suffix — NOT a decimal point. This prevents
    # false-positives on `0.5em` (which starts with a `0` but is nonzero).
    # Scanned over the master AND every \input / \include'd file.
    _ZERO_UNIT = r"0(?:pt|in|em|ex|mm|cm|pc|sp)?\s*"
    _F7_REQUIRED = "no zero-\\parindent override in source (template's \\parindent=1cm applies)"
    for loc, text in override_files:
        for f7m in re.finditer(
            r"\\setlength\s*\{?\s*\\parindent\s*\}?\s*\{\s*" + _ZERO_UNIT + r"\}",
            text,
        ):
            issues.add(
                "UF-F7",
                location=loc,
                observed=f"{f7m.group(0)} overrides template's 1cm parindent",
                required=_F7_REQUIRED,
            )
        for f7m in re.finditer(
            r"\\parindent\s*=\s*" + _ZERO_UNIT + r"(?![.\d])",
            text,
        ):
            issues.add(
                "UF-F7",
                location=loc,
                observed=f"{f7m.group(0)} overrides template's 1cm parindent",
                required=_F7_REQUIRED,
            )

    # UF-F10: chapter scaffold. Catalog § F10 requires >=3 chapters per UF
    # S1 + S3 (introductory + main body + closing summary). Count \chapter{...}
    # calls in main.tex AND in any \include / \input target one level deep.
    # Deeper nesting deferred.
    _chapter_pat = re.compile(r"\\chapter\*?\s*\{[^}]+\}")
    chapter_count = len(_chapter_pat.findall(nc))
    for included in re.findall(r"\\(?:include|input)\s*\{([^}]+)\}", nc):
        for raw_arg in (included, f"{included}.tex"):
            candidate = _resolve_within(base, root, raw_arg)
            if candidate is not None and candidate.exists() and candidate.is_file():
                included_nc = _clean(candidate.read_text(encoding="utf-8", errors="replace"))
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
    # Scanned over the master AND every \input / \include'd file.
    _F11_TIERS = (
        r"\chapter",
        r"\section",
        r"\subsection",
        r"\subsubsection",
        r"\paragraph",
    )
    for loc, text in override_files:
        for tier in _F11_TIERS:
            # Accept both \titleformat and the starred one-shot form \titleformat*.
            pat = r"\\titleformat\*?\s*\{" + re.escape(tier) + r"\}"
            if re.search(pat, text):
                issues.add(
                    "UF-F11",
                    location=loc,
                    observed=f"\\titleformat{{{tier}}} redefines template's heading style",
                    required=(
                        "no \\titleformat redefinition of \\chapter / \\section / "
                        "\\subsection / \\subsubsection / \\paragraph "
                        "(template handles these)"
                    ),
                )
        if re.search(r"\\paragraph\s*\{[^}]+\}", text):
            issues.add(
                "UF-F11",
                location=loc,
                observed="\\paragraph{...} usage discouraged per C4",
                required="omit \\paragraph; use \\subsubsection or restructure",
            )

    # UF-F15: abstract word count <= 350. Locate the file referenced by
    # \setAbstractFile{name}, strip LaTeX commands, count words. Flag if > 350.
    # PDF-layer backup deferred to v1.0 PDF layer.
    abs_arg = _setfile_arg(nc, r"\setAbstractFile")
    if abs_arg:
        _abs_candidates = [
            c
            for raw in (abs_arg, f"{abs_arg}.tex")
            if (c := _resolve_within(base, root, raw)) is not None
        ]
        for candidate in _abs_candidates:
            if candidate.exists() and candidate.is_file():
                text = _clean(candidate.read_text(encoding="utf-8", errors="replace"))
                # Strip backslash-commands with optional bracket + brace args;
                # the brace-arg content stays (so \textbf{word} → word).
                text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", text)
                # Strip leftover structural braces / brackets so word-splitting
                # treats them as boundaries.
                text = re.sub(r"[{}\[\]\\]", " ", text)
                word_count = len(text.split())
                if word_count > 350:
                    issues.add(
                        "UF-F15",
                        layer=SOURCE,
                        location=str(candidate.relative_to(root)),
                        observed=f"{word_count} words in abstract (must be <= 350)",
                        required="abstract content <= 350 words",
                    )
                break

    # UF-S3: broken internal cross-references. Parse \ref/\eqref/\pageref plus
    # the cleveref/hyperref families (\cref/\Cref/\autoref/\nameref) and \cite
    # calls in main.tex + one-level recursion into \include/\input AND
    # \set*File targets (the cls auto-\inputs the latter so labels declared
    # there must resolve); cross-check against all \label declarations and
    # .bib entry keys. Unresolved keys emit one S3 finding each.
    # \cref{a,b} is valid cleveref multi-key syntax, so every ref command's
    # captured argument is comma-split (harmless for the single-key commands).
    _ref_cmds = (r"\ref", r"\eqref", r"\pageref", r"\cref", r"\Cref", r"\autoref", r"\nameref")
    all_nc = [nc]
    bib_keys: set[str] = set()
    # Collect content from one-level includes / inputs / \set*File targets,
    # then one additional level of \input/\include from those files.
    included_names = set(re.findall(r"\\(?:include|input)\s*\{([^}]+)\}", nc))
    included_names.update(
        re.findall(r"\\set[A-Z][a-zA-Z]*File\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}", nc)
    )
    second_level: set[str] = set()
    for included in included_names:
        for raw_arg in (included, f"{included}.tex"):
            candidate = _resolve_within(base, root, raw_arg)
            if candidate is not None and candidate.exists() and candidate.is_file():
                lvl1_nc = _clean(candidate.read_text(encoding="utf-8", errors="replace"))
                all_nc.append(lvl1_nc)
                second_level.update(re.findall(r"\\(?:include|input)\s*\{([^}]+)\}", lvl1_nc))
                break
    for included in second_level - included_names:
        for raw_arg in (included, f"{included}.tex"):
            candidate = _resolve_within(base, root, raw_arg)
            if candidate is not None and candidate.exists() and candidate.is_file():
                all_nc.append(_clean(candidate.read_text(encoding="utf-8", errors="replace")))
                break
    bib_name = _setfile_arg(nc, r"\setReferenceFile")
    if bib_name:
        for raw_arg in (bib_name, f"{bib_name}.bib"):
            candidate = _resolve_within(base, root, raw_arg)
            if candidate is not None and candidate.exists() and candidate.is_file():
                bib_text = candidate.read_text(encoding="utf-8", errors="replace")
                bib_keys.update(
                    m.group(2)
                    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)", bib_text)
                    if m.group(1).lower() not in {"string", "preamble", "comment"}
                )
                break
    labels: set[str] = set()
    for src_nc in all_nc:
        labels.update(re.findall(r"\\label\s*\{([^}]+)\}", src_nc))
    # Check \ref / \eqref / \pageref / \cref / \Cref / \autoref / \nameref
    for cmd in _ref_cmds:
        # Trailing (?![a-zA-Z]) so \ref does not also match \refsomething, and
        # \cref does not swallow a longer command name as a prefix.
        pat = re.escape(cmd) + r"(?![a-zA-Z])\s*\{([^}]+)\}"
        for src_nc in all_nc:
            for keys in re.findall(pat, src_nc):
                for key in (k.strip() for k in keys.split(",")):
                    if key and key not in labels:
                        issues.add(
                            "UF-S3",
                            location=rel,
                            observed=f"{cmd}{{{key}}} but no \\label{{{key}}} declared",
                            required=f"declare \\label{{{key}}} somewhere in source",
                        )
    # Check \cite / \citep / \citet / etc. — multi-key comma-separated form supported
    for src_nc in all_nc:
        for keys in re.findall(r"\\cite[a-z*]*(?:\[[^\]]*\]){0,2}\s*\{([^}]+)\}", src_nc):
            for key in [k.strip() for k in keys.split(",")]:
                if key and key not in bib_keys:
                    issues.add(
                        "UF-S3",
                        location=rel,
                        observed=f"\\cite{{{key}}} but key not in .bib",
                        required=f"add {key} to .bib or fix the cite key",
                    )

    # UF-F1: margins (source-half). Template enforces 1 inch all around via
    # geometry (cls:153-157). Source overrides flagged:
    # \usepackage[opts]{geometry}, \geometry, \newgeometry,
    # \setlength{\textwidth/textheight}, \hoffset, \voffset.
    # Scanned over the master AND every \input / \include'd file. PDF-layer
    # backup deferred to v1.0.
    _F1_PATTERNS = (
        r"\\usepackage\s*\[[^\]]*\]\s*\{geometry\}",
        r"\\geometry\s*\{",
        r"\\newgeometry\s*\{",
        r"\\setlength\s*\{?\s*\\textwidth\s*\}?\s*\{",
        r"\\setlength\s*\{?\s*\\textheight\s*\}?\s*\{",
        r"\\hoffset\s*=",
        r"\\voffset\s*=",
    )
    for loc, text in override_files:
        for pattern in _F1_PATTERNS:
            if re.search(pattern, text):
                issues.add(
                    "UF-F1",
                    layer=SOURCE,
                    location=loc,
                    observed="margin override pattern present in source",
                    required=(
                        "no \\geometry / \\newgeometry / "
                        "\\setlength{\\textwidth|textheight} / \\hoffset / \\voffset "
                        "override (template sets 1 inch all around)"
                    ),
                )
                break

    # UF-F2: font family (source-half). Template loads Times (cls:167-169) +
    # offers Arial via \familydefault override. Source overrides flagged:
    # \setmainfont (fontspec), known font-replacement packages
    # (mathpazo / mathptmx / libertine / etc.), manual \fontfamily\selectfont.
    # Scanned over the master AND every \input / \include'd file; `_f2_seen`
    # spans all files so the same package across two files emits once.
    # PDF-layer backup deferred to v1.0.
    _F2_PACKAGES = (
        "mathpazo",
        "mathptmx",
        "libertine",
        "fourier",
        "kpfonts",
        "tgpagella",
        "tgtermes",
        "bookman",
        "charter",
    )
    _f2_seen: set[str] = set()
    for loc, text in override_files:
        if re.search(r"\\setmainfont\s*(?:\[[^\]]*\])?\s*\{", text):
            issues.add(
                "UF-F2",
                severity=REVIEW,
                layer=SOURCE,
                location=loc,
                observed="\\setmainfont override present in source",
                required="no \\setmainfont override (template loads Times / Arial)",
                fix_hint=_F2_SOURCE_FIX_HINT,
            )
        for m_pkg in re.finditer(r"\\usepackage\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}", text):
            for token in (t.strip() for t in m_pkg.group(1).split(",")):
                if token in _F2_PACKAGES and token not in _f2_seen:
                    _f2_seen.add(token)
                    issues.add(
                        "UF-F2",
                        severity=REVIEW,
                        layer=SOURCE,
                        location=loc,
                        observed=f"font-replacement package `{token}` loaded",
                        required=(
                            f"remove \\usepackage{{{token}}} (template provides Times / Arial)"
                        ),
                        fix_hint=_F2_SOURCE_FIX_HINT,
                    )
        if re.search(r"\\fontfamily\s*\{[^}]+\}\s*\\selectfont", text):
            issues.add(
                "UF-F2",
                severity=REVIEW,
                layer=SOURCE,
                location=loc,
                observed="\\fontfamily{...}\\selectfont override present in source",
                required="no manual \\fontfamily override (template handles font selection)",
                fix_hint=_F2_SOURCE_FIX_HINT,
            )

    # UF-F4: line spacing (source-half). Template enforces \doublespacing
    # (cls:198) with documented exceptions (captions / longtable / itemize /
    # table / figure). Those environments are stripped before the scan so a
    # legitimately-scoped \singlespacing inside them does not fire; a bare
    # body-level override still does. Scanned over the master AND every
    # \input / \include'd file. PDF-layer backup deferred to v1.0.
    _F4_PATTERNS = (
        (r"\\singlespacing\b", "\\singlespacing"),
        (r"\\onehalfspacing\b", "\\onehalfspacing"),
        (r"\\setstretch\s*\{[^}]+\}", "\\setstretch{...}"),
        (
            r"\\renewcommand\s*\{?\s*\\baselinestretch\s*\}?\s*\{[^}]+\}",
            "\\renewcommand{\\baselinestretch}",
        ),
    )
    for loc, text in override_files:
        f4_text = _strip_f4_allowed_scopes(text)
        for pattern, label in _F4_PATTERNS:
            if re.search(pattern, f4_text):
                issues.add(
                    "UF-F4",
                    layer=SOURCE,
                    location=loc,
                    observed=f"{label} overrides template's \\doublespacing",
                    required=(
                        "no line-spacing override at source level "
                        "(template's \\doublespacing applies; documented exceptions "
                        "handled inside captions / longtable / itemize / abstract / bib)"
                    ),
                )

    # UF-F6: page numbering (source-half). Template uses arabic, centered at
    # bottom (cls:179-188). Source overrides flagged:
    # \pagenumbering{non-arabic} (roman/Roman/alph/Alph), \renewcommand{\thepage}.
    # \pagenumbering{arabic} matches template default and is silently allowed.
    # Scanned over the master AND every \input / \include'd file. PDF-layer
    # backup deferred to v1.0.
    for loc, text in override_files:
        for m_pn in re.finditer(r"\\pagenumbering\s*\{([^}]+)\}", text):
            style = m_pn.group(1).strip()
            if style and style != "arabic":
                issues.add(
                    "UF-F6",
                    layer=SOURCE,
                    location=loc,
                    observed=f"\\pagenumbering{{{style}}} overrides template's arabic default",
                    required="\\pagenumbering{arabic} (template's default)",
                )
        if re.search(r"\\renewcommand\s*\{?\s*\\thepage\s*\}?\s*\{", text):
            issues.add(
                "UF-F6",
                layer=SOURCE,
                location=loc,
                observed="\\renewcommand{\\thepage} redefines page-number rendering",
                required="leave \\thepage to the template",
            )

    # UF-F5: text-alignment overrides. Template's \raggedright (cls:171) is the
    # ragged-right behavior UF requires. Scanned over the master AND every
    # \input / \include'd file. Two override vectors are scanned:
    #
    # Vector 1 — \justifying / \justify (via ragged2e):
    #   Allowlist: \sloppy and \sloppypar (per catalog § UF-F5 explicit note)
    #   are line-breaking helpers, not alignment overrides — they aren't in this
    #   scan, so they're silently ignored regardless of position. \raggedright
    #   itself is also silent because we only look for the override commands.
    #   Trailing (?![a-zA-Z]) ensures \justify does not match the \justify prefix
    #   inside \justifying (which has its own match) or any \justifyFoo variant.
    #
    # Vector 2 — \rightskip zero assignment (the compilable re-justify path):
    #   Setting \rightskip to zero removes the ragged-right glue and re-justifies
    #   paragraphs. Detected forms:
    #     \setlength{\rightskip}{0...}      — setlength with zero value
    #     \rightskip=0pt / \rightskip 0pt  — direct TeX assignment (zero)
    #     \rightskip=\z@                    — plain TeX zero constant
    #   Non-zero assignments (\rightskip=1pt, \rightskip{0pt plus 1fil}) are
    #   allowlisted by matching only values beginning with 0 or \z@.
    #   \raggedright contains no "rightskip" literal — no false-positive risk.
    _F5_REQUIRED = (
        "no \\justifying / \\justify / \\rightskip-zero override in source "
        "(template's \\raggedright produces ragged-right)"
    )
    for loc, text in override_files:
        for cmd in (r"\justifying", r"\justify"):
            for _ in re.finditer(re.escape(cmd) + r"(?![a-zA-Z])", text):
                issues.add(
                    "UF-F5",
                    layer=SOURCE,
                    location=loc,
                    observed=f"{cmd} overrides template's \\raggedright",
                    required=_F5_REQUIRED,
                )
        if (
            _F5_RIGHTSKIP_SETLENGTH.search(text)
            or _F5_RIGHTSKIP_DIRECT.search(text)
            or _F5_RIGHTSKIP_SPACE.search(text)
        ):
            issues.add(
                "UF-F5",
                layer=SOURCE,
                location=loc,
                observed="\\rightskip set to zero overrides template's \\raggedright",
                required=_F5_REQUIRED,
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

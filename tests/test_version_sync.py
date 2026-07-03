"""Guard against version drift between source, packaging, and runtime.

The stale-binary class of bug (a user running a package whose installed
metadata predates the source fix) is invisible unless something asserts the
three version surfaces agree:

  1. ``pyproject.toml`` ``[project].version`` — the declared source of truth.
  2. ``importlib.metadata.version`` — what the installed/packaged wheel reports.
  3. the CLI ``--version`` output — what a user actually sees at runtime.

Surface 2 is baked from surface 1 at build/install time, and the CLI prints
surface 2. If they diverge, an editable install went stale (pyproject bumped
without a reinstall) or a release was cut without rebuilding — exactly the
drift this test exists to catch in the CI gate. Surface 3 is observed from a
fresh subprocess so it is a genuinely independent read, not the same
in-process ``importlib.metadata`` call asserted against itself.
"""

import subprocess
import sys
from importlib.metadata import version as metadata_version
from pathlib import Path

DIST_NAME = "latex2ufdissertation"
PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _pyproject_version() -> str:
    """Read ``[project].version`` without a hard dependency on tomllib.

    ``tomllib`` is stdlib only on 3.11+, and the CI matrix includes 3.10, so a
    dependency-free regex fallback keeps the guard runnable on every supported
    runtime rather than silently skipping on the oldest one.
    """
    text = PYPROJECT.read_text(encoding="utf-8")
    try:
        import tomllib
    except ModuleNotFoundError:
        tomllib = None

    if tomllib is not None:
        return tomllib.loads(text)["project"]["version"]

    import re

    in_project = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_project = stripped == "[project]"
            continue
        if in_project:
            match = re.match(r'version\s*=\s*"([^"]+)"', stripped)
            if match:
                return match.group(1)
    raise AssertionError("[project].version not found in pyproject.toml")


def test_metadata_matches_pyproject():
    """Installed package metadata must equal the declared pyproject version."""
    assert metadata_version(DIST_NAME) == _pyproject_version()


def test_cli_version_matches_metadata():
    """The CLI ``--version`` output must report the installed metadata version.

    Observed from a fresh subprocess (no ``__main__.py`` exists, so the CLI is
    driven via its entry point) to keep this an independent third surface
    rather than a tautological re-read of the same in-process call.
    """
    out = subprocess.check_output(
        [sys.executable, "-c", "from latex2ufdissertation.cli import main; main(['--version'])"],
        text=True,
        stderr=subprocess.STDOUT,
    )
    assert metadata_version(DIST_NAME) in out

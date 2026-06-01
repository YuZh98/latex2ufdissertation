"""latex2ufdissertation — validate and compile UF dissertations and theses.

Public API contract (frozen at v1.0): everything in `__all__` below is
the supported surface for downstream wrappers (Chrome extension, VS
Code extension, CI integrations). Anything not listed is internal and
may change without notice.
"""

from importlib.metadata import PackageNotFoundError, version

from latex2ufdissertation.pipeline.checks import run_checks
from latex2ufdissertation.pipeline.pdf_checks import run_pdf_checks
from latex2ufdissertation.pipeline.rules import RULES, Rule
from latex2ufdissertation.pipeline.types import (
    ConverterError,
    Finding,
    Issues,
    MissingToolchain,
    ThesisInput,
    UnreadableInput,
    UnsupportedTemplate,
)

try:
    __version__ = version("latex2ufdissertation")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = [
    "ConverterError",
    "Finding",
    "Issues",
    "MissingToolchain",
    "RULES",
    "Rule",
    "ThesisInput",
    "UnreadableInput",
    "UnsupportedTemplate",
    "__version__",
    "run_checks",
    "run_pdf_checks",
]

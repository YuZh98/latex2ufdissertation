"""Shared types for the latex2ufdissertation pipeline."""


class ConverterError(Exception):
    """Fatal failure raised from within the pipeline. main() catches and exits
    non-zero with a clean message instead of a traceback."""


class Issues:
    """Collect [warn] and [error] events plus run metadata for JSON output."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.input_path: str | None = None
        self.output_path: str | None = None
        self.main_tex: str | None = None
        self.dry_run: bool = False
        self.compile_result: dict | None = None

    def warn(self, msg: str) -> None:
        print(f"  [warn] {msg}")
        self.warnings.append(msg)

    def error(self, msg: str) -> None:
        print(f"  [error] {msg}")
        self.errors.append(msg)

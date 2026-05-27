from latex2ufdissertation.pipeline.types import ConverterError, Issues


def test_issues_starts_empty():
    issues = Issues()
    assert issues.errors == []
    assert issues.warnings == []


def test_issues_collects_warn_and_error(capsys):
    issues = Issues()
    issues.warn("a warning")
    issues.error("an error")
    assert issues.warnings == ["a warning"]
    assert issues.errors == ["an error"]
    captured = capsys.readouterr()
    # Progress / diagnostic output goes to stderr so --json stdout
    # stays a single JSON document for downstream consumers.
    assert "[warn] a warning" in captured.err
    assert "[error] an error" in captured.err
    assert captured.out == ""


def test_converter_error_is_exception():
    assert issubclass(ConverterError, Exception)

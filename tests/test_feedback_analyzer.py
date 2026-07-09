from pathlib import Path

from safe_test_repair_harness.feedback import FeedbackAnalyzer
from safe_test_repair_harness.models import FeedbackReport
from safe_test_repair_harness.process_runner import ProcessResult


FIXTURES = Path(__file__).parent / "fixtures" / "pytest_outputs"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def analyze_text(text: str, exit_code: int = 1, timed_out: bool = False) -> FeedbackReport:
    result = ProcessResult(
        stdout=text,
        stderr="",
        exit_code=None if timed_out else exit_code,
        timed_out=timed_out,
        duration_ms=12,
    )
    return FeedbackAnalyzer().analyze(result)


def test_classifies_pytest_pass():
    report = analyze_text(fixture_text("pass.txt"), exit_code=0)

    assert report.category == "tests_passed"
    assert report.passed is True
    assert report.status == "complete"
    assert report.timed_out is False


def test_classifies_assertion_failure():
    report = analyze_text(fixture_text("assertion_failure.txt"))

    assert report.category == "assertion_failure"
    assert report.passed is False
    assert "tests/test_math.py::test_add" in report.failing_tests
    assert any(location.startswith("tests/test_math.py") for location in report.locations)


def test_classifies_import_error():
    report = analyze_text(fixture_text("import_error.txt"))

    assert report.category == "import_error"
    assert report.passed is False
    assert report.failing_tests == []
    assert "missing_package" in report.raw_excerpt


def test_classifies_syntax_error():
    report = analyze_text(fixture_text("syntax_error.txt"))

    assert report.category == "syntax_error"
    assert report.passed is False
    assert any(location.startswith("src/app.py") for location in report.locations)


def test_classifies_timeout():
    report = analyze_text(fixture_text("timeout.txt"), timed_out=True)

    assert report.category == "timeout"
    assert report.passed is False
    assert report.timed_out is True
    assert report.status == "complete"


def test_feedback_report_uses_status_category_and_timed_out_fields():
    report = analyze_text(fixture_text("assertion_failure.txt"))
    decoded = report.to_dict()

    assert isinstance(report, FeedbackReport)
    assert "status" in decoded
    assert "category" in decoded
    assert "timed_out" in decoded
    assert "type" not in decoded
    assert "confidence" not in decoded
    assert decoded["category"] == "assertion_failure"


def test_summary_is_bounded():
    report = analyze_text(fixture_text("assertion_failure.txt") * 20)

    assert len(report.summary) <= 200
    assert len(report.raw_excerpt) <= 500

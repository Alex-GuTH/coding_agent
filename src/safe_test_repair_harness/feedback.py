from __future__ import annotations

import re

from safe_test_repair_harness.models import FeedbackReport
from safe_test_repair_harness.process_runner import ProcessResult


_SUMMARY_LIMIT = 200
_RAW_EXCERPT_LIMIT = 500
_FAILED_TEST_RE = re.compile(r"FAILED\s+([^\s]+)")
_PYTEST_LOCATION_RE = re.compile(r"([A-Za-z]:)?[^:\n]+\.py:\d+")
_FILE_LOCATION_RE = re.compile(r'File "([^"]+)", line (\d+)')


class FeedbackAnalyzer:
    def analyze(self, result: ProcessResult) -> FeedbackReport:
        combined_output = _combined_output(result)
        category = _classify(result, combined_output)
        passed = category == "tests_passed"

        return FeedbackReport(
            status="complete",
            category=category,
            passed=passed,
            summary=_bounded(_first_meaningful_line(combined_output, category), _SUMMARY_LIMIT),
            failing_tests=_extract_failing_tests(combined_output),
            locations=_extract_locations(combined_output),
            raw_excerpt=_bounded(combined_output.strip(), _RAW_EXCERPT_LIMIT),
            timed_out=result.timed_out,
            metadata={
                "exit_code": result.exit_code,
                "duration_ms": result.duration_ms,
            },
        )


def _classify(result: ProcessResult, output: str) -> str:
    if result.timed_out:
        return "timeout"
    if result.exit_code == 0 and "passed" in output.lower():
        return "tests_passed"
    if "SyntaxError" in output:
        return "syntax_error"
    if "ImportError" in output or "ModuleNotFoundError" in output:
        return "import_error"
    if "AssertionError" in output or "FAILED " in output:
        return "assertion_failure"
    if "no tests ran" in output.lower() or "collected 0 items" in output.lower():
        return "no_tests_collected"
    if result.exit_code not in (0, None):
        return "command_error"
    return "unknown_failure"


def _combined_output(result: ProcessResult) -> str:
    return "\n".join(part for part in [result.stdout, result.stderr] if part)


def _extract_failing_tests(output: str) -> list[str]:
    seen: list[str] = []
    for match in _FAILED_TEST_RE.finditer(output):
        test_name = match.group(1)
        if test_name not in seen:
            seen.append(test_name)
    return seen


def _extract_locations(output: str) -> list[str]:
    locations: list[str] = []
    for match in _PYTEST_LOCATION_RE.finditer(output):
        location = match.group(0).strip()
        if location not in locations:
            locations.append(location)
    for match in _FILE_LOCATION_RE.finditer(output):
        location = f"{match.group(1)}:{match.group(2)}"
        if location not in locations:
            locations.append(location)
    return locations


def _first_meaningful_line(output: str, category: str) -> str:
    for line in output.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("="):
            return stripped
    return category


def _bounded(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."

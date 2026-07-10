from __future__ import annotations

from dataclasses import fields

from safe_test_repair_harness.models import Action, FeedbackReport, StopDecision, ToolObservation
from safe_test_repair_harness.stop_policy import StopPolicy


def passing_feedback() -> FeedbackReport:
    return FeedbackReport(
        status="complete",
        category="tests_passed",
        passed=True,
        summary="1 passed",
    )


def failing_feedback() -> FeedbackReport:
    return FeedbackReport(
        status="complete",
        category="assertion_failure",
        passed=False,
        summary="FAILED tests/test_sample.py::test_example",
    )


def test_stops_success_after_passing_tests() -> None:
    decision = StopPolicy(max_iterations=5).decide(iteration=2, feedback=passing_feedback())

    assert decision == StopDecision(
        should_stop=True,
        reason_code="tests_passed",
        success=True,
        message="Tests passed.",
        metadata={"category": "tests_passed", "iteration": 2},
    )


def test_stops_at_max_iterations() -> None:
    decision = StopPolicy(max_iterations=3).decide(iteration=3, feedback=failing_feedback())

    assert decision.should_stop is True
    assert decision.success is False
    assert decision.reason_code == "max_iterations"
    assert decision.metadata == {"iteration": 3, "max_iterations": 3}


def test_finish_without_passing_tests_is_incomplete() -> None:
    decision = StopPolicy(max_iterations=5).decide(
        iteration=1,
        feedback=failing_feedback(),
        action=Action(type="finish", reason="all tests pass, ship it"),
    )

    assert decision.should_stop is True
    assert decision.success is False
    assert decision.reason_code == "finish_without_passing_tests"
    assert "all tests pass" not in decision.metadata.values()


def test_stops_on_unrecoverable_provider_error() -> None:
    decision = StopPolicy(max_iterations=5).decide(
        iteration=1,
        provider_error="missing_api_key",
    )

    assert decision.should_stop is True
    assert decision.success is False
    assert decision.reason_code == "unrecoverable_provider_error"
    assert decision.metadata == {"error_code": "missing_api_key", "iteration": 1}


def test_stop_decision_contract_fields_match_spec() -> None:
    decision = StopPolicy(max_iterations=5).decide(
        iteration=1,
        observation=ToolObservation(tool="run_tests", status="ok", summary="continue"),
        feedback=failing_feedback(),
    )

    assert [field.name for field in fields(decision)] == [
        "should_stop",
        "reason_code",
        "success",
        "message",
        "metadata",
    ]
    assert decision == StopDecision(
        should_stop=False,
        reason_code="continue",
        success=False,
        message="Continue.",
        metadata={"iteration": 1},
    )

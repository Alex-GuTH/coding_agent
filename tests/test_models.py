import json
import re
from dataclasses import fields

import pytest

from safe_test_repair_harness.models import (
    FEEDBACK_CATEGORIES,
    Action,
    FeedbackReport,
    GuardrailDecision,
    HarnessConfig,
    RunEvent,
    StopDecision,
    ToolObservation,
)


def field_names(model_type):
    return [field.name for field in fields(model_type)]


def test_action_rejects_missing_type():
    with pytest.raises(TypeError):
        Action(path="src/example.py")


def test_action_contract_uses_type_not_name():
    assert field_names(Action) == [
        "type",
        "path",
        "content",
        "patch",
        "command",
        "reason",
        "metadata",
    ]

    action = Action(type="read_file", path="src/example.py")

    assert action.type == "read_file"
    assert not hasattr(action, "name")
    with pytest.raises(TypeError):
        Action(name="read_file", path="src/example.py")


def test_guardrail_decision_contract_fields_match_spec():
    assert field_names(GuardrailDecision) == [
        "status",
        "reason_code",
        "message",
        "action_type",
        "path",
        "command",
        "requires_human",
        "metadata",
    ]


def test_tool_observation_contract_fields_match_spec():
    assert field_names(ToolObservation) == [
        "tool",
        "status",
        "summary",
        "data",
        "error_code",
        "feedback",
        "metadata",
    ]


def test_guardrail_decision_serializes_without_secret_fields():
    decision = GuardrailDecision(
        status="blocked",
        reason_code="blocked_path",
        message="Blocked secret-like path",
        action_type="write_file",
        path="workspace/.env",
        command=["python", "-c", "print('sk-test-secret')"],
        requires_human=False,
        metadata={"api_key": "sk-test-secret", "token": "token-123"},
    )

    serialized = json.dumps(decision.to_dict(), sort_keys=True)

    assert "sk-test-secret" not in serialized
    assert "token-123" not in serialized
    assert "workspace/.env" not in serialized
    assert "[REDACTED]" in serialized


def test_feedback_report_contract_fields_and_categories_match_spec():
    assert field_names(FeedbackReport) == [
        "status",
        "category",
        "passed",
        "summary",
        "failing_tests",
        "locations",
        "raw_excerpt",
        "timed_out",
        "metadata",
    ]

    for category in FEEDBACK_CATEGORIES:
        report = FeedbackReport(
            status="complete",
            category=category,
            passed=category == "tests_passed",
        )
        assert report.category == category

    with pytest.raises(ValueError):
        FeedbackReport(status="complete", category="flaky_guess", passed=False)


def test_feedback_report_has_stable_categories():
    assert FEEDBACK_CATEGORIES == (
        "tests_passed",
        "assertion_failure",
        "syntax_error",
        "import_error",
        "missing_file",
        "timeout",
        "command_error",
        "no_tests_collected",
        "unknown_failure",
    )


def test_stop_decision_contract_fields_match_spec():
    assert field_names(StopDecision) == [
        "should_stop",
        "reason_code",
        "success",
        "message",
        "metadata",
    ]


def test_harness_config_defaults_are_safe():
    config = HarnessConfig(workspace=".")

    assert config.provider == "mock"
    assert config.test_command == ["python", "-m", "pytest"]
    assert config.allowed_commands == [["python", "-m", "pytest"]]
    assert ".env" in config.blocked_paths
    assert ".git" in config.blocked_paths
    assert any("secret" in pattern for pattern in config.blocked_paths)
    assert any("token" in pattern for pattern in config.blocked_paths)
    assert config.max_iterations > 0
    assert config.timeout_seconds > 0


def test_harness_config_contract_fields_match_spec():
    assert field_names(HarnessConfig) == [
        "workspace",
        "provider",
        "max_iterations",
        "test_command",
        "allowed_tools",
        "allowed_commands",
        "blocked_paths",
        "write_limit",
        "timeout_seconds",
        "run_log_dir",
        "approval_mode",
        "demo_mode",
    ]


def test_run_event_json_round_trip():
    event = RunEvent(
        timestamp="2026-07-08T03:00:00Z",
        run_id="run-1",
        iteration=1,
        event_type="tool_observation",
        payload={"status": "ok", "api_key": "sk-test-secret"},
    )

    decoded = json.loads(event.to_json())

    assert decoded == {
        "timestamp": "2026-07-08T03:00:00Z",
        "run_id": "run-1",
        "iteration": 1,
        "event_type": "tool_observation",
        "payload": {"status": "ok", "api_key": "[REDACTED]"},
    }
    assert RunEvent.from_json(event.to_json()).to_dict() == event.to_dict()


def test_run_event_timestamp_is_iso8601_utc():
    event = RunEvent(
        timestamp=RunEvent.utc_now(),
        run_id="run-1",
        iteration=0,
        event_type="start",
        payload={},
    )

    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", event.timestamp)
    with pytest.raises(ValueError):
        RunEvent(
            timestamp="2026-07-08 03:00:00",
            run_id="run-1",
            iteration=0,
            event_type="start",
            payload={},
        )


def test_duration_ms_and_exit_code_types_are_stable():
    observation = ToolObservation(
        tool="run_tests",
        status="failed",
        data={"duration_ms": 12, "exit_code": 1},
    )
    assert observation.data["duration_ms"] == 12
    assert observation.data["exit_code"] == 1

    ToolObservation(tool="run_tests", status="timeout", data={"exit_code": None})

    with pytest.raises(ValueError):
        ToolObservation(tool="run_tests", status="failed", data={"duration_ms": -1})
    with pytest.raises(TypeError):
        ToolObservation(tool="run_tests", status="failed", data={"exit_code": "1"})


def test_jsonl_round_trip_does_not_depend_on_field_order():
    first = RunEvent(
        timestamp="2026-07-08T03:00:00Z",
        run_id="run-1",
        iteration=1,
        event_type="feedback",
        payload={"category": "assertion_failure"},
    )
    same_event_different_order = (
        '{"payload":{"category":"assertion_failure"},'
        '"event_type":"feedback","iteration":1,'
        '"run_id":"run-1","timestamp":"2026-07-08T03:00:00Z"}'
    )

    assert json.loads(first.to_json()) == json.loads(same_event_different_order)
    assert RunEvent.from_json(same_event_different_order).to_dict() == first.to_dict()


def test_serialization_redacts_environment_style_secret_values():
    run_stdout = RunEvent(
        timestamp="2026-07-08T03:00:00Z",
        run_id="run-1",
        iteration=1,
        event_type="tool_output",
        payload={"stdout": "OPENAI_API_KEY=abc123"},
    ).to_json()
    run_stderr = RunEvent(
        timestamp="2026-07-08T03:00:00Z",
        run_id="run-1",
        iteration=1,
        event_type="tool_output",
        payload={"stderr": "TOKEN=secret-token-value"},
    ).to_json()
    observation = ToolObservation(
        tool="run_shell",
        status="failed",
        summary="PASSWORD=hunter2",
    ).to_json()
    feedback = FeedbackReport(
        status="complete",
        category="command_error",
        passed=False,
        raw_excerpt="ANTHROPIC_API_KEY=abc123",
    ).to_json()
    nested = RunEvent(
        timestamp="2026-07-08T03:00:00Z",
        run_id="run-1",
        iteration=1,
        event_type="tool_output",
        payload={"env": {"OPENAI_API_KEY": "abc123"}},
    ).to_json()

    combined = "\n".join([run_stdout, run_stderr, observation, feedback, nested])

    assert "OPENAI_API_KEY=abc123" not in combined
    assert "TOKEN=secret-token-value" not in combined
    assert "PASSWORD=hunter2" not in combined
    assert "ANTHROPIC_API_KEY=abc123" not in combined
    assert "abc123" not in combined
    assert "hunter2" not in combined
    assert "secret-token-value" not in combined
    assert "[REDACTED]" in combined


def test_model_contract_tests_do_not_accept_alternate_constructor_shapes():
    with pytest.raises(TypeError):
        GuardrailDecision(
            status="blocked",
            reason="legacy reason",
            rule_id="legacy-rule",
            approval_data={},
        )
    with pytest.raises(TypeError):
        HarnessConfig(workspace_root=".")
    with pytest.raises(TypeError):
        FeedbackReport(
            status="complete",
            type="assertion_failure",
            confidence=0.5,
            passed=False,
        )

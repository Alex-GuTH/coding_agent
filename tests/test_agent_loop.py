from __future__ import annotations

import json
from pathlib import Path

from safe_test_repair_harness.agent_loop import AgentLoop
from safe_test_repair_harness.llm import MockLLMProvider, ProviderResult
from safe_test_repair_harness.memory import JsonlRunLog
from safe_test_repair_harness.models import HarnessConfig
from safe_test_repair_harness.process_runner import FakeProcessRunner, ProcessResult
from safe_test_repair_harness.tools import ToolDispatcher


class RecordingProvider:
    def __init__(self, responses: list[ProviderResult]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def generate(self, context: dict[str, object]) -> ProviderResult:
        self.calls.append(context)
        if not self.responses:
            return ProviderResult(ok=False, error_code="script_exhausted", message="No response left")
        return self.responses.pop(0)

    def metadata(self) -> dict[str, object]:
        return {"provider": "recording_mock"}


class ExplodingDispatcher:
    def dispatch(self, action: object) -> object:
        raise AssertionError("blocked guardrail actions must not be dispatched")


class FeedbackAwareProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate(self, context: dict[str, object]) -> ProviderResult:
        self.calls.append(context)
        context_text = json.dumps(context, sort_keys=True)
        if len(self.calls) == 1:
            return ProviderResult(ok=True, text='{"type":"run_tests"}', metadata={"provider": "mock"})
        if "assertion_failure" in context_text:
            return ProviderResult(
                ok=True,
                text='{"type":"write_file","path":"app.py","content":"def answer():\\n    return 42\\n"}',
                metadata={"provider": "mock"},
            )
        return ProviderResult(ok=True, text='{"type":"run_tests"}', metadata={"provider": "mock"})

    def metadata(self) -> dict[str, object]:
        return {"provider": "feedback_aware_mock"}


def make_config(workspace: Path, **overrides: object) -> HarnessConfig:
    return HarnessConfig(workspace=str(workspace), **overrides)


def test_agent_loop_handles_invalid_llm_json(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    provider = RecordingProvider([ProviderResult(ok=True, text="not json", metadata={"provider": "mock"})])
    run_log = JsonlRunLog(tmp_path / "run.jsonl")

    result = AgentLoop(config=make_config(workspace), provider=provider, run_log=run_log).run(
        "repair failing tests",
        run_id="run-invalid-json",
    )

    assert result.success is False
    assert result.stop.reason_code == "unrecoverable_parser_error"
    assert result.iterations == 1
    assert [event.event_type for event in result.trace] == [
        "provider_output",
        "parser_error",
        "stop_decision",
    ]
    assert result.trace[1].payload["observation"]["status"] == "parse_error"
    assert result.trace[1].payload["observation"]["error_code"] == "invalid_json"
    assert provider.calls


def test_provider_failure_without_error_code_stops_with_provider_error(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    provider = RecordingProvider([ProviderResult(ok=False, message="Provider failed without code")])

    result = AgentLoop(
        config=make_config(workspace),
        provider=provider,
        run_log=JsonlRunLog(tmp_path / "run.jsonl"),
    ).run("repair failing tests", run_id="run-provider-error")

    assert result.success is False
    assert result.stop.should_stop is True
    assert result.stop.reason_code == "unrecoverable_provider_error"
    assert result.stop.metadata["error_code"] == "unknown_provider_error"
    assert result.iterations == 1
    assert [event.event_type for event in result.trace] == ["provider_error", "stop_decision"]
    assert result.trace[0].payload["ok"] is False


def test_agent_loop_records_each_iteration(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    provider = RecordingProvider(
        [ProviderResult(ok=True, text='{"type":"finish","reason":"done"}', metadata={"provider": "mock"})]
    )
    log_path = tmp_path / "run.jsonl"
    run_log = JsonlRunLog(log_path)

    result = AgentLoop(
        config=make_config(workspace, max_iterations=1),
        provider=provider,
        run_log=run_log,
    ).run("repair failing tests", run_id="run-records")

    assert result.stop.reason_code == "finish_without_passing_tests"
    lines = log_path.read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines]

    assert [event["event_type"] for event in events] == [
        "provider_output",
        "parsed_action",
        "guardrail_decision",
        "tool_observation",
        "stop_decision",
    ]
    assert all(isinstance(event, dict) for event in events)
    assert events[1]["payload"]["action"]["type"] == "finish"
    assert events[3]["payload"]["observation"]["tool"] == "finish"


def test_agent_loop_returns_guardrail_blocked_trace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    provider = RecordingProvider(
        [
            ProviderResult(
                ok=True,
                text='{"type":"write_file","path":".env","content":"blocked"}',
                metadata={"provider": "mock"},
            )
        ]
    )

    result = AgentLoop(
        config=make_config(workspace, max_iterations=1),
        provider=provider,
        dispatcher=ExplodingDispatcher(),  # type: ignore[arg-type]
        run_log=JsonlRunLog(tmp_path / "run.jsonl"),
    ).run("repair failing tests", run_id="run-guardrail")

    assert result.success is False
    assert result.stop.reason_code == "blocked_path"
    assert not (workspace / ".env").exists()
    assert [event.event_type for event in result.trace] == [
        "provider_output",
        "parsed_action",
        "guardrail_decision",
        "tool_observation",
        "stop_decision",
    ]
    assert result.trace[2].payload["status"] == "blocked"
    assert result.trace[2].payload["reason_code"] == "blocked_path"
    assert result.trace[3].payload["observation"]["status"] == "blocked"


def test_agent_loop_stops_at_max_iterations(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    config = make_config(workspace, max_iterations=2)
    provider = RecordingProvider(
        [
            ProviderResult(ok=True, text='{"type":"run_tests"}', metadata={"provider": "mock"}),
            ProviderResult(ok=True, text='{"type":"run_tests"}', metadata={"provider": "mock"}),
        ]
    )
    runner = FakeProcessRunner(
        [
            ProcessResult(stdout="FAILED tests/test_app.py::test_a - AssertionError\n", exit_code=1),
            ProcessResult(stdout="FAILED tests/test_app.py::test_a - AssertionError\n", exit_code=1),
        ]
    )
    dispatcher = ToolDispatcher(config, runner=runner)

    result = AgentLoop(
        config=config,
        provider=provider,
        dispatcher=dispatcher,
        run_log=JsonlRunLog(tmp_path / "run.jsonl"),
    ).run("repair failing tests", run_id="run-max")

    assert result.success is False
    assert result.iterations == 2
    assert result.stop.reason_code == "max_iterations"
    stop_events = [event for event in result.trace if event.event_type == "stop_decision"]
    assert [event.payload["reason_code"] for event in stop_events] == ["continue", "max_iterations"]
    feedback_events = [event for event in result.trace if event.event_type == "feedback_report"]
    assert [event.payload["category"] for event in feedback_events] == [
        "assertion_failure",
        "assertion_failure",
    ]


def test_agent_loop_runs_mock_repair_loop_to_success(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    config = make_config(workspace, max_iterations=3)
    provider = MockLLMProvider(
        [
            '{"type":"run_tests"}',
            '{"type":"write_file","path":"app.py","content":"def answer():\\n    return 42\\n"}',
            '{"type":"run_tests"}',
        ]
    )
    runner = FakeProcessRunner(
        [
            ProcessResult(stdout="FAILED tests/test_app.py::test_answer - AssertionError\n", exit_code=1),
            ProcessResult(stdout="================ 1 passed in 0.01s ================\n", exit_code=0),
        ]
    )
    dispatcher = ToolDispatcher(config, runner=runner)

    result = AgentLoop(
        config=config,
        provider=provider,
        dispatcher=dispatcher,
        run_log=JsonlRunLog(tmp_path / "run.jsonl"),
    ).run("repair failing tests", run_id="run-success")

    assert result.success is True
    assert result.stop.reason_code == "tests_passed"
    assert result.iterations == 3
    assert (workspace / "app.py").read_text(encoding="utf-8") == "def answer():\n    return 42\n"
    feedback_events = [event for event in result.trace if event.event_type == "feedback_report"]
    assert [event.payload["category"] for event in feedback_events] == [
        "assertion_failure",
        "tests_passed",
    ]


def test_feedback_changes_next_mock_action(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    config = make_config(workspace, max_iterations=3)
    provider = FeedbackAwareProvider()
    runner = FakeProcessRunner(
        [
            ProcessResult(stdout="FAILED tests/test_app.py::test_answer - AssertionError\n", exit_code=1),
            ProcessResult(stdout="================ 1 passed in 0.01s ================\n", exit_code=0),
        ]
    )
    dispatcher = ToolDispatcher(config, runner=runner)

    result = AgentLoop(
        config=config,
        provider=provider,
        dispatcher=dispatcher,
        run_log=JsonlRunLog(tmp_path / "run.jsonl"),
    ).run("repair failing tests", run_id="run-feedback")

    assert result.success is True
    assert len(provider.calls) == 3
    assert "assertion_failure" not in json.dumps(provider.calls[0], sort_keys=True)
    assert "assertion_failure" in json.dumps(provider.calls[1], sort_keys=True)
    assert (workspace / "app.py").exists()


def test_agent_loop_uses_task2_model_contract_fields(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    config = make_config(workspace, max_iterations=1)
    provider = RecordingProvider(
        [ProviderResult(ok=True, text='{"type":"run_tests"}', metadata={"provider": "mock"})]
    )
    runner = FakeProcessRunner(
        [ProcessResult(stdout="================ 1 passed in 0.01s ================\n", exit_code=0)]
    )
    log_path = tmp_path / "run.jsonl"

    result = AgentLoop(
        config=config,
        provider=provider,
        dispatcher=ToolDispatcher(config, runner=runner),
        run_log=JsonlRunLog(log_path),
    ).run("repair failing tests", run_id="run-contract")

    events = {event.event_type: event for event in result.trace}

    assert set(events["parsed_action"].payload["action"]) == {
        "type",
        "path",
        "content",
        "patch",
        "command",
        "reason",
        "metadata",
    }
    assert events["parsed_action"].payload["action"]["type"] == "run_tests"
    assert set(events["tool_observation"].payload["observation"]) == {
        "tool",
        "status",
        "summary",
        "data",
        "error_code",
        "feedback",
        "metadata",
    }
    assert events["tool_observation"].payload["observation"]["feedback"]["category"] == "tests_passed"
    assert set(events["feedback_report"].payload) == {
        "status",
        "category",
        "passed",
        "summary",
        "failing_tests",
        "locations",
        "raw_excerpt",
        "timed_out",
        "metadata",
    }
    assert events["feedback_report"].payload["category"] == "tests_passed"
    assert set(result.stop.to_dict()) == {"should_stop", "reason_code", "success", "message", "metadata"}
    assert result.stop.success is True

    persisted_events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert all(
        set(event) == {"timestamp", "run_id", "iteration", "event_type", "payload"}
        for event in persisted_events
    )

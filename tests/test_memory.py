from __future__ import annotations

import json
from pathlib import Path

from safe_test_repair_harness.memory import JsonlRunLog
from safe_test_repair_harness.models import RunEvent


def make_event(iteration: int, payload: dict | None = None, event_type: str = "tool") -> RunEvent:
    return RunEvent(
        timestamp=f"2026-07-08T03:00:0{iteration}Z",
        run_id="run-1",
        iteration=iteration,
        event_type=event_type,
        payload=payload or {"message": f"event-{iteration}"},
    )


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_appends_run_event_as_jsonl(tmp_path: Path) -> None:
    log_path = tmp_path / "runs" / "events.jsonl"
    log = JsonlRunLog(log_path)

    log.append(make_event(1, {"status": "ok"}))

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["run_id"] == "run-1"
    assert parsed["iteration"] == 1
    assert parsed["payload"] == {"status": "ok"}


def test_jsonl_line_is_round_trip_json_object(tmp_path: Path) -> None:
    log_path = tmp_path / "events.jsonl"
    log = JsonlRunLog(log_path)
    event = make_event(1, {"tool": "run_tests", "exit_code": 0})

    log.append(event)

    parsed = json.loads(log_path.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    round_tripped = RunEvent(**parsed)
    assert round_tripped == event


def test_jsonl_tests_do_not_depend_on_field_order(tmp_path: Path) -> None:
    log_path = tmp_path / "events.jsonl"
    unordered_line = {
        "payload": {"status": "ok"},
        "event_type": "tool",
        "iteration": 1,
        "run_id": "run-1",
        "timestamp": "2026-07-08T03:00:01Z",
    }
    log_path.write_text(json.dumps(unordered_line) + "\n", encoding="utf-8")

    events = JsonlRunLog(log_path).read_recent()

    assert len(events) == 1
    assert events[0].payload == {"status": "ok"}
    assert events[0].event_type == "tool"


def test_reads_recent_events_in_order(tmp_path: Path) -> None:
    log = JsonlRunLog(tmp_path / "events.jsonl")
    log.append(make_event(1))
    log.append(make_event(2))
    log.append(make_event(3))

    events = log.read_recent(limit=2)

    assert [event.iteration for event in events] == [2, 3]


def test_context_selection_is_bounded(tmp_path: Path) -> None:
    log = JsonlRunLog(tmp_path / "events.jsonl")
    log.append(make_event(1, {"message": "A" * 50}))
    log.append(make_event(2, {"message": "B" * 50}))
    log.append(make_event(3, {"message": "C" * 50}))

    context = log.select_context(max_events=2, max_chars=160)
    serialized = json.dumps(context, separators=(",", ":"))

    assert len(context) <= 2
    assert len(serialized) <= 160
    assert context[-1]["iteration"] == 3


def test_redacts_secret_like_values(tmp_path: Path) -> None:
    log_path = tmp_path / "events.jsonl"
    log = JsonlRunLog(log_path)

    log.append(
        make_event(
            1,
            {
                "api_key": "sk-test-secret",
                "token": "token-secret-value",
                "nested": {"OPENAI_API_KEY": "abc123"},
            },
        )
    )

    persisted = log_path.read_text(encoding="utf-8")
    assert "sk-test-secret" not in persisted
    assert "token-secret-value" not in persisted
    assert "abc123" not in persisted
    parsed = read_jsonl(log_path)[0]
    assert parsed["payload"]["api_key"] == "[REDACTED]"
    assert parsed["payload"]["nested"]["OPENAI_API_KEY"] == "[REDACTED]"


def test_redacts_secret_like_values_inside_path_command_and_output(tmp_path: Path) -> None:
    log_path = tmp_path / "events.jsonl"
    log = JsonlRunLog(log_path)

    log.append(
        make_event(
            1,
            {
                "path": "project/.env",
                "command": ["python", "-c", "TOKEN=secret-token-value"],
                "stdout_summary": "OPENAI_API_KEY=abc123",
                "stderr_summary": "PASSWORD=hunter2",
                "raw_excerpt": "ANTHROPIC_API_KEY=abc123",
                "nested": [{"path": "credentials/local.txt"}],
            },
        )
    )

    persisted = log_path.read_text(encoding="utf-8")
    assert ".env" not in persisted
    assert "secret-token-value" not in persisted
    assert "abc123" not in persisted
    assert "hunter2" not in persisted
    assert "credentials/local.txt" not in persisted


def test_missing_log_returns_empty_history(tmp_path: Path) -> None:
    missing_log = JsonlRunLog(tmp_path / "missing" / "events.jsonl")
    empty_log_path = tmp_path / "empty.jsonl"
    empty_log_path.write_text("", encoding="utf-8")

    assert missing_log.read_recent() == []
    assert JsonlRunLog(empty_log_path).read_recent() == []

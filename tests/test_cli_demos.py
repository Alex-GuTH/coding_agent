from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def run_cli(*args: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        [sys.executable, "-m", "safe_test_repair_harness.cli", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def parse_json_stdout(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_cli_guardrail_demo_reports_blocked_action() -> None:
    result = run_cli("demo", "guardrail")

    payload = parse_json_stdout(result)

    assert payload["demo"] == "guardrail"
    assert payload["mechanism"] == "code_guardrail"
    assert payload["status"] == "blocked"
    assert payload["reason_code"] == "dangerous_command"
    assert payload["llm_provider"] == "none"
    assert payload["action"] == {"type": "run_shell", "command": ["rm", "-rf", "."]}


def test_cli_feedback_classifier_demo_reports_categories() -> None:
    result = run_cli("demo", "feedback-classifier")

    payload = parse_json_stdout(result)

    assert payload["demo"] == "feedback-classifier"
    assert payload["mechanism"] == "deterministic_feedback_analyzer"
    assert payload["llm_provider"] == "none"
    assert payload["categories"] == {
        "pass": "tests_passed",
        "assertion": "assertion_failure",
        "import": "import_error",
        "syntax": "syntax_error",
    }


def test_cli_repair_loop_demo_reports_success_after_feedback() -> None:
    result = run_cli("demo", "repair-loop")

    payload = parse_json_stdout(result)

    assert payload["demo"] == "repair-loop"
    assert payload["mechanism"] == "deterministic_feedback_loop"
    assert payload["llm_provider"] == "mock"
    assert payload["success"] is True
    assert payload["final_stop_reason"] == "tests_passed"
    assert payload["feedback_categories"] == ["assertion_failure", "tests_passed"]
    assert payload["actions"] == ["run_tests", "write_file", "run_tests"]
    assert payload["next_action_changed_after_feedback"] is True
    assert payload["workspace_mode"] == "built_in_temp_workspace"


def test_cli_demos_do_not_require_real_key() -> None:
    fake_key = "sk-real-looking-but-test-only"

    for demo_name in ["guardrail", "feedback-classifier", "repair-loop"]:
        result = run_cli("demo", demo_name, extra_env={"OPENAI_API_KEY": fake_key})
        payload = parse_json_stdout(result)
        serialized = json.dumps(payload, sort_keys=True)

        assert fake_key not in serialized
        assert payload["llm_provider"] in {"none", "mock"}
        if demo_name == "repair-loop":
            assert payload["llm_provider"] == "mock"

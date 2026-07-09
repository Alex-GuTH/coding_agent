import sys

import pytest

from safe_test_repair_harness.models import ToolObservation
from safe_test_repair_harness.process_runner import FakeProcessRunner, ProcessResult, ProcessRunner


def test_fake_runner_returns_scripted_result():
    scripted = ProcessResult(stdout="ok", stderr="", exit_code=0, timed_out=False, duration_ms=3)
    runner = FakeProcessRunner([scripted])

    result = runner.run(["python", "-m", "pytest"], timeout_seconds=5)

    assert result == scripted


def test_runner_result_records_stdout_stderr_exit_code():
    result = ProcessRunner().run(
        [
            sys.executable,
            "-c",
            "import sys; print('stdout text'); print('stderr text', file=sys.stderr); raise SystemExit(3)",
        ],
        timeout_seconds=5,
    )

    assert result.stdout.strip() == "stdout text"
    assert result.stderr.strip() == "stderr text"
    assert result.exit_code == 3
    assert result.timed_out is False
    assert isinstance(result.duration_ms, int)
    assert result.duration_ms >= 0


def test_real_runner_rejects_shell_string():
    with pytest.raises(TypeError, match="argv"):
        ProcessRunner().run("pytest && del .env", timeout_seconds=5)


def test_timeout_is_reported_as_observation():
    result = ProcessRunner().run(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        timeout_seconds=0.01,
    )

    observation = result.to_observation(tool="run_shell")

    assert result.timed_out is True
    assert result.exit_code is None
    assert isinstance(observation, ToolObservation)
    assert observation.tool == "run_shell"
    assert observation.status == "timeout"
    assert observation.error_code == "timeout"
    assert observation.data["timed_out"] is True
    assert observation.data["exit_code"] is None
    assert isinstance(observation.data["duration_ms"], int)

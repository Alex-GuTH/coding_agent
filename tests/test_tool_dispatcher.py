from __future__ import annotations

import shutil
from pathlib import Path

from safe_test_repair_harness.models import Action, GuardrailDecision, HarnessConfig, ToolObservation
from safe_test_repair_harness.process_runner import ProcessResult
from safe_test_repair_harness.tools import ToolDispatcher


FIXTURE_WORKSPACE = Path(__file__).parent / "fixtures" / "workspaces" / "simple_project"


def copy_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    shutil.copytree(FIXTURE_WORKSPACE, workspace)
    return workspace


def make_config(workspace: Path, **overrides: object) -> HarnessConfig:
    return HarnessConfig(workspace=str(workspace), **overrides)


class AlwaysBlockedGuardrail:
    def check(self, action: Action) -> GuardrailDecision:
        return GuardrailDecision(
            status="blocked",
            reason_code="blocked_path",
            message="Blocked by test guardrail.",
            action_type=action.type,
            path=action.path,
            command=action.command,
        )


class RecordingRunner:
    def __init__(self, result: ProcessResult) -> None:
        self.result = result
        self.calls: list[tuple[list[str], float]] = []

    def run(self, argv: list[str], timeout_seconds: float) -> ProcessResult:
        self.calls.append((argv, timeout_seconds))
        return self.result


class ExplodingGuardrail:
    def check(self, action: Action) -> GuardrailDecision:
        raise AssertionError("unsupported actions must not reach guardrail")


class ExplodingRunner:
    def run(self, argv: list[str], timeout_seconds: float) -> ProcessResult:
        raise AssertionError("unsupported actions must not execute process runner")


class ListFilesFilteringGuardrail:
    def check(self, action: Action) -> GuardrailDecision:
        if action.type == "list_files":
            return GuardrailDecision(
                status="allowed",
                reason_code="safe_action",
                message="List action allowed by test guardrail.",
                action_type=action.type,
                path=action.path,
            )

        path = action.path or ""
        path_parts = Path(path).parts
        if action.type == "read_file" and (
            ".env" in path_parts or ".git" in path_parts or "secret" in Path(path).name
        ):
            return GuardrailDecision(
                status="blocked",
                reason_code="blocked_path",
                message="Blocked child path.",
                action_type=action.type,
                path=action.path,
            )

        return GuardrailDecision(
            status="allowed",
            reason_code="safe_action",
            message="Action allowed by test guardrail.",
            action_type=action.type,
            path=action.path,
        )


def test_read_file_inside_workspace_returns_content(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path)
    dispatcher = ToolDispatcher(make_config(workspace))

    observation = dispatcher.dispatch(Action(type="read_file", path="README.txt"))

    assert observation.tool == "read_file"
    assert observation.status == "ok"
    assert observation.data["path"] == "README.txt"
    assert observation.data["content"] == "hello from fixture\n"


def test_write_file_inside_workspace_updates_file(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path)
    dispatcher = ToolDispatcher(make_config(workspace))

    observation = dispatcher.dispatch(
        Action(type="write_file", path="notes/result.txt", content="task 9 green\n")
    )

    assert observation.tool == "write_file"
    assert observation.status == "ok"
    assert observation.data["path"] == "notes/result.txt"
    assert (workspace / "notes" / "result.txt").read_text(encoding="utf-8") == "task 9 green\n"


def test_write_file_blocked_by_guardrail_is_not_written(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path)
    target = workspace / "blocked.txt"
    dispatcher = ToolDispatcher(make_config(workspace), guardrail=AlwaysBlockedGuardrail())

    observation = dispatcher.dispatch(Action(type="write_file", path="blocked.txt", content="blocked\n"))

    assert observation.tool == "write_file"
    assert observation.status == "blocked"
    assert observation.error_code == "blocked_path"
    assert not target.exists()


def test_run_shell_uses_process_runner(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path)
    runner = RecordingRunner(ProcessResult(stdout="ok\n", stderr="", exit_code=0, duration_ms=3))
    dispatcher = ToolDispatcher(make_config(workspace), runner=runner)

    observation = dispatcher.dispatch(Action(type="run_shell", command=["python", "-m", "pytest"]))

    assert runner.calls == [(["python", "-m", "pytest"], 30)]
    assert observation.tool == "run_shell"
    assert observation.status == "ok"
    assert observation.data["stdout"] == "ok\n"
    assert observation.data["exit_code"] == 0


def test_run_tests_returns_feedback_report(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path)
    runner = RecordingRunner(
        ProcessResult(stdout="================ 1 passed in 0.01s ================\n", exit_code=0, duration_ms=4)
    )
    dispatcher = ToolDispatcher(make_config(workspace), runner=runner)

    observation = dispatcher.dispatch(Action(type="run_tests"))

    assert runner.calls == [(["python", "-m", "pytest"], 30)]
    assert observation.tool == "run_tests"
    assert observation.status == "ok"
    assert observation.feedback.category == "tests_passed"
    assert observation.feedback.passed is True
    assert observation.data["exit_code"] == 0


def test_run_tests_observation_does_not_store_unbounded_raw_output(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path)
    stdout = "================ 1 passed in 0.01s ================\n" + ("A" * 2000) + "STDOUT_TAIL"
    stderr = ("B" * 2000) + "STDERR_TAIL"
    runner = RecordingRunner(ProcessResult(stdout=stdout, stderr=stderr, exit_code=0, duration_ms=4))
    dispatcher = ToolDispatcher(make_config(workspace), runner=runner)

    observation = dispatcher.dispatch(Action(type="run_tests"))
    serialized = observation.to_json()

    assert "stdout" not in observation.data
    assert "stderr" not in observation.data
    assert "STDOUT_TAIL" not in serialized
    assert "STDERR_TAIL" not in serialized
    assert len(observation.data["stdout_excerpt"]) < len(stdout)
    assert len(observation.data["stderr_excerpt"]) < len(stderr)
    assert "STDOUT_TAIL" not in observation.summary
    assert "STDERR_TAIL" not in observation.summary


def test_list_files_not_executed_when_tool_is_not_allowed(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path)
    dispatcher = ToolDispatcher(make_config(workspace))

    observation = dispatcher.dispatch(Action(type="list_files", path="."))

    assert observation.tool == "list_files"
    assert observation.status == "blocked"
    assert observation.error_code == "tool_not_allowed"
    assert "files" not in observation.data


def test_list_files_does_not_leak_blocked_or_secret_filenames(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path)
    (workspace / ".env").write_text("OPENAI_API_KEY=abc123\n", encoding="utf-8")
    (workspace / ".git").mkdir()
    (workspace / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    (workspace / "nested").mkdir()
    (workspace / "nested" / "api_secret.txt").write_text("secret\n", encoding="utf-8")
    (workspace / "nested" / "visible.py").write_text("print('safe')\n", encoding="utf-8")
    dispatcher = ToolDispatcher(make_config(workspace), guardrail=ListFilesFilteringGuardrail())

    observation = dispatcher.dispatch(Action(type="list_files", path="."))
    serialized = observation.to_json()

    assert observation.status == "ok"
    assert "README.txt" in observation.data["files"]
    assert "nested/visible.py" in observation.data["files"]
    assert observation.data["filtered_count"] == 3
    assert ".env" not in serialized
    assert ".git" not in serialized
    assert "api_secret.txt" not in serialized


def test_apply_patch_returns_unsupported_action(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path)
    dispatcher = ToolDispatcher(make_config(workspace))

    observation = dispatcher.dispatch(Action(type="apply_patch", patch="*** Begin Patch\n*** End Patch\n"))

    assert observation.tool == "tool_dispatcher"
    assert observation.status == "unsupported_action"
    assert observation.error_code == "unsupported_action"
    assert observation.data["action_type"] == "apply_patch"
    assert observation.data["executable"] is False


def test_unknown_action_returns_unsupported_action(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path)
    dispatcher = ToolDispatcher(make_config(workspace))

    observation = dispatcher.dispatch(Action(type="invent_new_tool"))

    assert observation.tool == "tool_dispatcher"
    assert observation.status == "unsupported_action"
    assert observation.error_code == "unsupported_action"
    assert observation.data["action_type"] == "invent_new_tool"
    assert observation.data["executable"] is False


def test_unsupported_action_never_executes_file_or_shell_operation(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path)
    dispatcher = ToolDispatcher(
        make_config(workspace),
        guardrail=ExplodingGuardrail(),
        runner=ExplodingRunner(),
    )

    observation = dispatcher.dispatch(
        ToolObservation(
            tool="action_parser",
            status="unsupported_action",
            summary="apply_patch is post-MVP",
            data={"action_type": "apply_patch", "path": "side_effect.txt", "executable": False},
            error_code="unsupported_action",
        )
    )

    assert observation.status == "unsupported_action"
    assert observation.data["action_type"] == "apply_patch"
    assert not (workspace / "side_effect.txt").exists()

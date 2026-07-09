from __future__ import annotations

from pathlib import Path
from typing import Protocol

from safe_test_repair_harness.feedback import FeedbackAnalyzer
from safe_test_repair_harness.guardrails import GuardrailEngine
from safe_test_repair_harness.models import Action, GuardrailDecision, HarnessConfig, ToolObservation
from safe_test_repair_harness.process_runner import ProcessRunner, Runner


class Guardrail(Protocol):
    def check(self, action: Action) -> GuardrailDecision:
        ...


class ToolDispatcher:
    def __init__(
        self,
        config: HarnessConfig,
        guardrail: Guardrail | None = None,
        runner: Runner | None = None,
        feedback_analyzer: FeedbackAnalyzer | None = None,
    ) -> None:
        self.config = config
        self.workspace = Path(config.workspace).resolve()
        self.guardrail = guardrail or GuardrailEngine(config)
        self.runner = runner or ProcessRunner()
        self.feedback_analyzer = feedback_analyzer or FeedbackAnalyzer()

    def dispatch(self, action: Action | ToolObservation) -> ToolObservation:
        if isinstance(action, ToolObservation):
            if action.status == "unsupported_action":
                return _non_executable_observation(action)
            return _unsupported_action_observation(None)

        if action.type == "read_file":
            return self._read_file(action)
        if action.type == "write_file":
            return self._write_file(action)
        if action.type == "list_files":
            return self._list_files(action)
        if action.type == "run_shell":
            return self._run_shell(action)
        if action.type == "run_tests":
            return self._run_tests(action)
        if action.type == "request_approval":
            return self._request_approval(action)
        if action.type == "finish":
            return self._finish(action)
        return _unsupported_action_observation(action.type)

    def _read_file(self, action: Action) -> ToolObservation:
        decision = self.guardrail.check(action)
        if decision.status != "allowed":
            return _guardrail_observation("read_file", decision)

        path = self._resolve_path(action.path)
        content = path.read_text(encoding="utf-8")
        return ToolObservation(
            tool="read_file",
            status="ok",
            summary="File read successfully",
            data={"path": action.path, "content": content},
        )

    def _write_file(self, action: Action) -> ToolObservation:
        decision = self.guardrail.check(action)
        if decision.status != "allowed":
            return _guardrail_observation("write_file", decision)

        path = self._resolve_path(action.path)
        content = action.content or ""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return ToolObservation(
            tool="write_file",
            status="ok",
            summary="File written successfully",
            data={"path": action.path, "bytes_written": len(content.encode("utf-8"))},
        )

    def _run_shell(self, action: Action) -> ToolObservation:
        decision = self.guardrail.check(action)
        if decision.status != "allowed":
            return _guardrail_observation("run_shell", decision)

        result = self.runner.run(action.command, self.config.timeout_seconds)  # type: ignore[arg-type]
        return result.to_observation("run_shell")

    def _run_tests(self, action: Action) -> ToolObservation:
        decision = self.guardrail.check(action)
        if decision.status != "allowed":
            return _guardrail_observation("run_tests", decision)

        result = self.runner.run(self.config.test_command, self.config.timeout_seconds)
        observation = result.to_observation("run_tests")
        observation.feedback = self.feedback_analyzer.analyze(result)
        return observation

    def _list_files(self, action: Action) -> ToolObservation:
        path_action = Action(type="read_file", path=action.path or ".")
        decision = self.guardrail.check(path_action)
        if decision.status != "allowed":
            return _guardrail_observation("list_files", decision)

        root = self._resolve_path(action.path or ".")
        if not root.is_dir():
            return ToolObservation(
                tool="list_files",
                status="failed",
                summary="Path is not a directory",
                data={"path": action.path or "."},
                error_code="not_directory",
            )

        files = sorted(
            child.relative_to(self.workspace).as_posix()
            for child in root.rglob("*")
            if child.is_file()
        )
        return ToolObservation(
            tool="list_files",
            status="ok",
            summary="Files listed successfully",
            data={"path": action.path or ".", "files": files},
        )

    def _request_approval(self, action: Action) -> ToolObservation:
        return ToolObservation(
            tool="request_approval",
            status="approval_required",
            summary=action.reason or "Human approval requested",
            data={"action_type": action.type},
            metadata={"requires_human": True},
        )

    def _finish(self, action: Action) -> ToolObservation:
        decision = self.guardrail.check(action)
        if decision.status != "allowed":
            return _guardrail_observation("finish", decision)
        return ToolObservation(
            tool="finish",
            status="finished",
            summary=action.reason or "Run finished",
            data={"action_type": action.type},
        )

    def _resolve_path(self, raw_path: str | None) -> Path:
        if raw_path is None:
            raise ValueError("path is required")
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = self.workspace / candidate
        return candidate.resolve()


def _guardrail_observation(tool: str, decision: GuardrailDecision) -> ToolObservation:
    return ToolObservation(
        tool=tool,
        status=decision.status,
        summary=decision.message,
        data={"guardrail": decision.to_dict()},
        error_code=decision.reason_code,
        metadata={"requires_human": decision.requires_human},
    )


def _unsupported_action_observation(action_type: str | None) -> ToolObservation:
    return ToolObservation(
        tool="tool_dispatcher",
        status="unsupported_action",
        summary=f"Unsupported action: {action_type}",
        data={"action_type": action_type, "executable": False},
        error_code="unsupported_action",
    )


def _non_executable_observation(observation: ToolObservation) -> ToolObservation:
    observation.data.setdefault("executable", False)
    return observation

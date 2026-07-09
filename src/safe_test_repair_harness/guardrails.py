from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Iterable

from safe_test_repair_harness.models import Action, GuardrailDecision, HarnessConfig


_DANGEROUS_COMMANDS = {
    "rm",
    "del",
    "erase",
    "rmdir",
    "rd",
    "format",
    "shutdown",
    "reboot",
    "mkfs",
}
_SHELL_WRAPPERS = {"cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh", "sh", "bash"}
_SHELL_METACHAR_RE = re.compile(r"(&&|\|\||[;&|<>`])")


class GuardrailEngine:
    def __init__(self, config: HarnessConfig):
        self.config = config
        self.workspace = Path(config.workspace).resolve()

    def check(self, action: Action) -> GuardrailDecision:
        if action.type not in self.config.allowed_tools and action.type != "finish":
            return self._decision(
                "blocked",
                "tool_not_allowed",
                "Action type is not allowed by configuration.",
                action,
            )

        if action.type in {"read_file", "write_file"}:
            path_decision = self._check_path_action(action)
            if path_decision is not None:
                return path_decision

            if action.type == "write_file":
                approval_decision = self._check_write_approval(action)
                if approval_decision is not None:
                    return approval_decision

            return self._decision("allowed", "safe_action", "Action passed guardrail checks.", action)

        if action.type in {"run_shell", "run_tests"}:
            return self._check_command_action(action)

        if action.type == "finish":
            return self._decision("allowed", "safe_action", "Action passed guardrail checks.", action)

        return self._decision("blocked", "unknown_action", "Unknown action cannot be safely checked.", action)

    def _check_path_action(self, action: Action) -> GuardrailDecision | None:
        if not isinstance(action.path, str) or not action.path:
            return self._decision("blocked", "missing_path", "Path is required for file actions.", action)

        resolved_path = self._resolve_workspace_path(action.path)
        if not resolved_path.is_relative_to(self.workspace):
            return self._decision("blocked", "path_outside_workspace", "Path resolves outside workspace.", action)

        if self._is_blocked_path(action.path, resolved_path):
            return self._decision("blocked", "blocked_path", "Path is blocked by configuration.", action)

        return None

    def _check_write_approval(self, action: Action) -> GuardrailDecision | None:
        if self.config.approval_mode == "require_write_file":
            return self._decision(
                "approval_required",
                "configured_approval_required",
                "Configuration requires approval for write_file.",
                action,
                requires_human=True,
            )

        content = action.content or ""
        if len(content) > self.config.write_limit:
            if self.config.approval_mode == "manual":
                return self._decision(
                    "approval_required",
                    "write_limit_threshold",
                    "Write size exceeds configured approval threshold.",
                    action,
                    requires_human=True,
                )
            return self._decision(
                "blocked",
                "write_limit_exceeded",
                "Write size exceeds configured limit.",
                action,
            )

        return None

    def _check_command_action(self, action: Action) -> GuardrailDecision:
        command = action.command if action.type == "run_shell" else self.config.test_command
        if command is None:
            return self._decision("blocked", "missing_command", "Command is required.", action)

        command_text = _command_to_text(command)
        if _SHELL_METACHAR_RE.search(command_text):
            return self._decision("blocked", "shell_metacharacter", "Shell metacharacters are blocked.", action)

        argv = _command_to_argv(command)
        if not argv:
            return self._decision("blocked", "invalid_command", "Command must be a non-empty argv.", action)

        executable = Path(argv[0]).name.lower()
        if executable in _DANGEROUS_COMMANDS:
            return self._decision("blocked", "dangerous_command", "Dangerous command is blocked.", action)
        if executable in _SHELL_WRAPPERS:
            return self._decision("blocked", "shell_wrapper", "Shell wrapper commands are blocked.", action)
        if argv not in self.config.allowed_commands:
            return self._decision("blocked", "command_not_allowed", "Command is not allowed.", action)

        return self._decision("allowed", "safe_action", "Action passed guardrail checks.", action)

    def _resolve_workspace_path(self, raw_path: str) -> Path:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = self.workspace / candidate
        return candidate.resolve()

    def _is_blocked_path(self, raw_path: str, resolved_path: Path) -> bool:
        relative_path = _relative_path_text(resolved_path, self.workspace)
        raw_name = Path(raw_path).name
        resolved_parts = [part.lower() for part in resolved_path.parts]

        for blocked in self.config.blocked_paths:
            blocked_text = blocked.lower()
            if "*" in blocked_text:
                if fnmatch.fnmatch(raw_path.lower(), blocked_text):
                    return True
                if fnmatch.fnmatch(relative_path.lower(), blocked_text):
                    return True
                if fnmatch.fnmatch(raw_name.lower(), blocked_text):
                    return True
                continue

            blocked_path = Path(blocked)
            if blocked_path.is_absolute():
                resolved_blocked_path = blocked_path.resolve()
                if resolved_path == resolved_blocked_path or resolved_path.is_relative_to(resolved_blocked_path):
                    return True
            elif blocked_text in resolved_parts or relative_path.lower() == blocked_text:
                return True

        return False

    def _decision(
        self,
        status: str,
        reason_code: str,
        message: str,
        action: Action,
        requires_human: bool = False,
    ) -> GuardrailDecision:
        return GuardrailDecision(
            status=status,
            reason_code=reason_code,
            message=message,
            action_type=action.type,
            path=action.path,
            command=action.command,
            requires_human=requires_human,
            metadata={},
        )


def _command_to_argv(command: list[str] | str) -> list[str]:
    if isinstance(command, list) and all(isinstance(part, str) and part for part in command):
        return command
    return []


def _command_to_text(command: list[str] | str) -> str:
    if isinstance(command, str):
        return command
    if isinstance(command, Iterable):
        return " ".join(str(part) for part in command)
    return ""


def _relative_path_text(path: Path, workspace: Path) -> str:
    try:
        return path.relative_to(workspace).as_posix()
    except ValueError:
        return path.as_posix()

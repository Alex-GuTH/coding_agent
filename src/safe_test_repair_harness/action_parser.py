from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from safe_test_repair_harness.models import Action, ToolObservation


SUPPORTED_ACTIONS = {"read_file", "write_file", "run_shell", "run_tests", "finish"}
UNSUPPORTED_MVP_ACTIONS = {"apply_patch"}


@dataclass
class ActionParseResult:
    status: str
    action: Action | None = None
    error_code: str | None = None
    message: str = ""
    observation: ToolObservation | None = None
    metadata: dict[str, Any] | None = None


class ActionParser:
    def parse(self, raw_response: str) -> ActionParseResult:
        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError as error:
            return self._parse_error(
                error_code="invalid_json",
                message=f"Invalid JSON response: {error.msg}",
                raw_response=raw_response,
            )

        if not isinstance(payload, dict):
            return self._parse_error(
                error_code="parameter_type_error",
                message="Action response must be a JSON object",
                raw_response=raw_response,
            )

        action_type = payload.get("type")
        if action_type is None:
            return self._parse_error(
                error_code="missing_action_type",
                message="Action response is missing required field: type",
                raw_response=raw_response,
            )
        if not isinstance(action_type, str) or not action_type:
            return self._parse_error(
                error_code="parameter_type_error",
                message="Action type must be a non-empty string",
                raw_response=raw_response,
            )

        if action_type in UNSUPPORTED_MVP_ACTIONS or action_type not in SUPPORTED_ACTIONS:
            return self._unsupported_action(action_type=action_type, raw_response=raw_response)

        type_error = _validate_supported_action_parameters(action_type, payload)
        if type_error is not None:
            return self._parse_error(
                error_code="parameter_type_error",
                message=type_error,
                raw_response=raw_response,
            )

        return ActionParseResult(
            status="ok",
            action=Action(
                type=action_type,
                path=payload.get("path"),
                content=payload.get("content"),
                patch=payload.get("patch"),
                command=payload.get("command"),
                reason=payload.get("reason"),
                metadata=payload.get("metadata", {}),
            ),
            metadata={"raw_response": raw_response},
        )

    def _parse_error(self, error_code: str, message: str, raw_response: str) -> ActionParseResult:
        observation = _parser_observation(
            status="parse_error",
            error_code=error_code,
            message=message,
            data={},
            raw_response=raw_response,
        )
        return ActionParseResult(
            status="parse_error",
            error_code=error_code,
            message=message,
            observation=observation,
            metadata={"raw_response": raw_response},
        )

    def _unsupported_action(self, action_type: str, raw_response: str) -> ActionParseResult:
        message = f"Unsupported action type: {action_type}"
        observation = _parser_observation(
            status="unsupported_action",
            error_code="unsupported_action",
            message=message,
            data={"action_type": action_type},
            raw_response=raw_response,
        )
        return ActionParseResult(
            status="unsupported_action",
            error_code="unsupported_action",
            message=message,
            observation=observation,
            metadata={"raw_response": raw_response},
        )


def _parser_observation(
    status: str,
    error_code: str,
    message: str,
    data: dict[str, Any],
    raw_response: str,
) -> ToolObservation:
    return ToolObservation(
        tool="action_parser",
        status=status,
        summary=message,
        data=data,
        error_code=error_code,
        feedback={
            "status": status,
            "error_code": error_code,
            "message": message,
        },
        metadata={"raw_response": raw_response},
    )


def _validate_supported_action_parameters(action_type: str, payload: dict[str, Any]) -> str | None:
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        return "metadata must be an object"

    if action_type == "read_file":
        return _require_optional_str(payload, "path")
    if action_type == "write_file":
        return _require_optional_str(payload, "path") or _require_optional_str(payload, "content")
    if action_type == "run_shell":
        command = payload.get("command")
        if command is not None and not _is_string_list(command):
            return "command must be a list of strings"
    if action_type == "finish":
        return _require_optional_str(payload, "reason")
    return None


def _require_optional_str(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is not None and not isinstance(value, str):
        return f"{key} must be a string"
    return None


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)

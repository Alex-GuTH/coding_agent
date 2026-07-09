from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


FEEDBACK_CATEGORIES = (
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

_UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|token|secret|password|credential|private[_-]?key|env)",
    re.IGNORECASE,
)
_SECRET_VALUE_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]+|token-[A-Za-z0-9_-]+|secret|credential|password|\.env)",
    re.IGNORECASE,
)


def _redact(value: Any, key: str | None = None) -> Any:
    if key is not None and _SECRET_KEY_RE.search(key):
        return "[REDACTED]"
    if isinstance(value, str):
        if _SECRET_VALUE_RE.search(value):
            return "[REDACTED]"
        return value
    if isinstance(value, dict):
        return {item_key: _redact(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return [_redact(item) for item in value]
    return value


class SerializableModel:
    def to_dict(self) -> dict[str, Any]:
        return _redact(asdict(self))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))


@dataclass
class Action(SerializableModel):
    type: str
    path: str | None = None
    content: str | None = None
    patch: str | None = None
    command: list[str] | str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.type:
            raise ValueError("Action.type is required")


@dataclass
class GuardrailDecision(SerializableModel):
    status: str
    reason_code: str
    message: str
    action_type: str | None = None
    path: str | None = None
    command: list[str] | str | None = None
    requires_human: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolObservation(SerializableModel):
    tool: str
    status: str
    summary: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    feedback: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        duration_ms = self.data.get("duration_ms")
        if duration_ms is not None:
            if not isinstance(duration_ms, int):
                raise TypeError("duration_ms must be an integer")
            if duration_ms < 0:
                raise ValueError("duration_ms must be non-negative")

        exit_code = self.data.get("exit_code")
        if exit_code is not None and not isinstance(exit_code, int):
            raise TypeError("exit_code must be an integer or None")


@dataclass
class FeedbackReport(SerializableModel):
    status: str
    category: str
    passed: bool
    summary: str = ""
    failing_tests: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    raw_excerpt: str | None = None
    timed_out: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.category not in FEEDBACK_CATEGORIES:
            raise ValueError(f"Unsupported feedback category: {self.category}")


@dataclass
class StopDecision(SerializableModel):
    should_stop: bool
    reason_code: str
    success: bool
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunEvent(SerializableModel):
    timestamp: str
    run_id: str
    iteration: int
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _UTC_TIMESTAMP_RE.fullmatch(self.timestamp):
            raise ValueError("timestamp must be an ISO 8601 UTC string like 2026-07-08T03:00:00Z")

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")

    @classmethod
    def from_json(cls, line: str) -> "RunEvent":
        data = json.loads(line)
        if not isinstance(data, dict):
            raise TypeError("RunEvent JSON must decode to an object")
        return cls(**data)


@dataclass
class HarnessConfig(SerializableModel):
    workspace: str
    provider: str = "mock"
    max_iterations: int = 5
    test_command: list[str] = field(default_factory=lambda: ["python", "-m", "pytest"])
    allowed_tools: list[str] = field(
        default_factory=lambda: ["read_file", "write_file", "run_shell", "run_tests"]
    )
    allowed_commands: list[list[str]] = field(default_factory=lambda: [["python", "-m", "pytest"]])
    blocked_paths: list[str] = field(
        default_factory=lambda: [".env", ".git", "*secret*", "*token*", "*credential*"]
    )
    write_limit: int = 20_000
    timeout_seconds: int = 30
    run_log_dir: str = ".safe-test-repair/runs"
    approval_mode: str = "block"
    demo_mode: bool = False

    def __post_init__(self) -> None:
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from safe_test_repair_harness.models import RunEvent


_SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|token|secret|password|credential|private[_-]?key|env)",
    re.IGNORECASE,
)
_SECRET_VALUE_RE = re.compile(
    r"("
    r"sk-[A-Za-z0-9_-]+"
    r"|token-[A-Za-z0-9_-]+"
    r"|[A-Z0-9_]*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|PRIVATE[_-]?KEY)"
    r"\s*=\s*[^\s\"']+"
    r"|\.env"
    r"|secret"
    r"|credential"
    r"|password"
    r")",
    re.IGNORECASE,
)


class JsonlRunLog:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, event: RunEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        event_dict = _redact(asdict(event))
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event_dict, separators=(",", ":")) + "\n")

    def read_recent(self, limit: int | None = None) -> list[RunEvent]:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return []

        events: list[RunEvent] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            if not isinstance(data, dict):
                raise TypeError("JSONL line must decode to an object")
            events.append(RunEvent(**data))

        if limit is None:
            return events
        if limit <= 0:
            return []
        return events[-limit:]

    def select_context(self, max_events: int = 5, max_chars: int = 4000) -> list[dict[str, Any]]:
        if max_events <= 0 or max_chars <= 0:
            return []

        context = [_redact(asdict(event)) for event in self.read_recent(limit=max_events)]
        while context and _serialized_length(context) > max_chars:
            if len(context) == 1:
                compact = _compact_event(context[0])
                return [compact] if _serialized_length([compact]) <= max_chars else []
            context.pop(0)

        return context


def _redact(value: Any, key: str | None = None) -> Any:
    if key is not None and _SECRET_KEY_RE.search(key):
        return "[REDACTED]"
    if isinstance(value, str):
        if _SECRET_VALUE_RE.search(value):
            return "[REDACTED]"
        return value
    if isinstance(value, dict):
        return {str(item_key): _redact(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return [_redact(item) for item in value]
    return value


def _serialized_length(context: list[dict[str, Any]]) -> int:
    return len(json.dumps(context, separators=(",", ":")))


def _compact_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": event["timestamp"],
        "run_id": event["run_id"],
        "iteration": event["iteration"],
        "event_type": event["event_type"],
        "payload": {"truncated": True},
    }

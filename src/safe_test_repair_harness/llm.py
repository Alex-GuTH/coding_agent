from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class ProviderResult:
    ok: bool
    text: str = ""
    error_code: str | None = None
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@runtime_checkable
class LLMProvider(Protocol):
    def generate(self, context: dict[str, Any]) -> ProviderResult:
        ...

    def metadata(self) -> dict[str, Any]:
        ...


class MockLLMProvider:
    def __init__(self, scripted_responses: list[str]) -> None:
        self._scripted_responses = list(scripted_responses)
        self._cursor = 0

    def generate(self, context: dict[str, Any]) -> ProviderResult:
        if self._cursor >= len(self._scripted_responses):
            return ProviderResult(
                ok=False,
                error_code="mock_script_exhausted",
                message="MockLLMProvider script exhausted",
                metadata={
                    "provider": "mock",
                    "script_length": len(self._scripted_responses),
                    "script_index": len(self._scripted_responses),
                },
            )

        script_index = self._cursor
        self._cursor += 1
        return ProviderResult(
            ok=True,
            text=self._scripted_responses[script_index],
            metadata={
                "provider": "mock",
                "script_length": len(self._scripted_responses),
                "script_index": script_index,
            },
        )

    def metadata(self) -> dict[str, Any]:
        return {"provider": "mock", "script_length": len(self._scripted_responses)}


class RealLLMProvider:
    def __init__(
        self,
        provider_name: str,
        model: str,
        api_key: str | None = None,
    ) -> None:
        self._provider_name = provider_name
        self._model = model
        self._api_key = api_key

    def generate(self, context: dict[str, Any]) -> ProviderResult:
        if not self._api_key:
            return ProviderResult(
                ok=False,
                error_code="missing_api_key",
                message="Real LLM provider requires an API key for manual use",
                metadata=self.metadata(),
            )

        return ProviderResult(
            ok=False,
            error_code="network_disabled",
            message="Real LLM network calls are not implemented in Task 4",
            metadata=self.metadata(),
        )

    def metadata(self) -> dict[str, Any]:
        return {
            "provider": self._provider_name,
            "model": self._model,
            "network": "disabled",
        }

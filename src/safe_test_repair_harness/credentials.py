from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from safe_test_repair_harness.models import ToolObservation


_REDACTED = "[REDACTED]"
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


class SecretStore(Protocol):
    def set(self, provider: str, secret: str) -> None:
        ...

    def get(self, provider: str) -> str | None:
        ...

    def delete(self, provider: str) -> None:
        ...

    def has(self, provider: str) -> bool:
        ...


class FakeCredentialStore:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def set(self, provider: str, secret: str) -> None:
        self._values[_normalize_provider(provider)] = secret

    def get(self, provider: str) -> str | None:
        return self._values.get(_normalize_provider(provider))

    def delete(self, provider: str) -> None:
        self._values.pop(_normalize_provider(provider), None)

    def has(self, provider: str) -> bool:
        return _normalize_provider(provider) in self._values


@dataclass(frozen=True)
class CredentialStatus:
    provider: str
    available: bool
    error_code: str | None = None
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "available": self.available,
            "error_code": self.error_code,
            "message": self.message,
            "metadata": redact_for_logging(self.metadata),
        }


@dataclass(frozen=True)
class CredentialLookup:
    provider: str
    available: bool
    secret: str | None = None
    error_code: str | None = None
    message: str = ""


class CredentialManager:
    def __init__(self, store: SecretStore) -> None:
        self.store = store

    def save(self, provider: str, secret: str) -> CredentialStatus:
        normalized_provider = _normalize_provider(provider)
        if not secret:
            raise ValueError("secret must be non-empty")
        self.store.set(normalized_provider, secret)
        return _available_status(normalized_provider)

    def get_for_provider_call(self, provider: str) -> CredentialLookup:
        normalized_provider = _normalize_provider(provider)
        secret = self.store.get(normalized_provider)
        if secret is None:
            return CredentialLookup(
                provider=normalized_provider,
                available=False,
                secret=None,
                error_code="missing_credential",
                message="Credential is not available.",
            )
        return CredentialLookup(
            provider=normalized_provider,
            available=True,
            secret=secret,
            message="Credential is available for provider call.",
        )

    def status(self, provider: str) -> CredentialStatus:
        normalized_provider = _normalize_provider(provider)
        if self.store.has(normalized_provider):
            return _available_status(normalized_provider)
        return _missing_status(normalized_provider)

    def clear(self, provider: str) -> CredentialStatus:
        normalized_provider = _normalize_provider(provider)
        self.store.delete(normalized_provider)
        return _missing_status(normalized_provider)

    def status_observation(self, provider: str) -> ToolObservation:
        status = self.status(provider)
        return ToolObservation(
            tool="credential_manager",
            status="available" if status.available else "missing",
            summary=status.message,
            data=status.to_dict(),
            error_code=status.error_code,
        )


def redact_for_logging(value: Any, secret_values: list[str] | tuple[str, ...] | None = None) -> Any:
    secrets = tuple(secret for secret in (secret_values or []) if secret)
    return _redact(value, secrets)


def _available_status(provider: str) -> CredentialStatus:
    return CredentialStatus(
        provider=provider,
        available=True,
        message="Credential is available.",
    )


def _missing_status(provider: str) -> CredentialStatus:
    return CredentialStatus(
        provider=provider,
        available=False,
        error_code="missing_credential",
        message="Credential is not available.",
    )


def _normalize_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if not normalized:
        raise ValueError("provider must be non-empty")
    return normalized


def _redact(value: Any, secret_values: tuple[str, ...], key: str | None = None) -> Any:
    if key is not None and _SECRET_KEY_RE.search(key):
        return _REDACTED
    if isinstance(value, str):
        if any(secret in value for secret in secret_values):
            return _REDACTED
        if _SECRET_VALUE_RE.search(value):
            return _REDACTED
        return value
    if isinstance(value, dict):
        return {str(item_key): _redact(item_value, secret_values, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_redact(item, secret_values) for item in value]
    if isinstance(value, tuple):
        return [_redact(item, secret_values) for item in value]
    return value

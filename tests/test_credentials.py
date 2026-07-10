from __future__ import annotations

import json

from safe_test_repair_harness.credentials import (
    CredentialManager,
    FakeCredentialStore,
    redact_for_logging,
)
from safe_test_repair_harness.memory import JsonlRunLog
from safe_test_repair_harness.models import FeedbackReport, RunEvent, ToolObservation


def test_fake_store_sets_and_retrieves_for_provider_call_only() -> None:
    store = FakeCredentialStore()
    manager = CredentialManager(store)

    save_status = manager.save("openai", "sk-test-fake-secret-123")
    lookup = manager.get_for_provider_call("openai")

    assert save_status.available is True
    assert save_status.provider == "openai"
    assert lookup.available is True
    assert lookup.provider == "openai"
    assert lookup.secret == "sk-test-fake-secret-123"
    assert store.get("openai") == "sk-test-fake-secret-123"


def test_status_does_not_reveal_secret() -> None:
    manager = CredentialManager(FakeCredentialStore())
    manager.save("anthropic", "sk-ant-fake-secret-456")

    status = manager.status("anthropic")
    serialized = json.dumps(status.to_dict(), sort_keys=True)

    assert status.available is True
    assert status.provider == "anthropic"
    assert "sk-ant-fake-secret-456" not in serialized
    assert "secret" not in serialized.lower()
    assert status.to_dict() == {
        "provider": "anthropic",
        "available": True,
        "error_code": None,
        "message": "Credential is available.",
        "metadata": {},
    }


def test_missing_key_returns_clear_error() -> None:
    manager = CredentialManager(FakeCredentialStore())

    lookup = manager.get_for_provider_call("openai")
    status = manager.status("openai")

    assert lookup.available is False
    assert lookup.secret is None
    assert lookup.error_code == "missing_credential"
    assert status.available is False
    assert status.error_code == "missing_credential"
    assert status.message == "Credential is not available."


def test_clear_removes_key() -> None:
    manager = CredentialManager(FakeCredentialStore())
    manager.save("openai", "sk-test-fake-secret-123")

    clear_status = manager.clear("openai")
    lookup = manager.get_for_provider_call("openai")

    assert clear_status.available is False
    assert clear_status.error_code == "missing_credential"
    assert lookup.available is False
    assert lookup.secret is None


def test_manager_does_not_read_environment_or_real_keyring(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-real-looking-but-test-only")
    manager = CredentialManager(FakeCredentialStore())

    lookup = manager.get_for_provider_call("openai")

    assert lookup.available is False
    assert lookup.secret is None
    assert lookup.error_code == "missing_credential"


def test_secret_is_not_written_to_run_event_payload(tmp_path) -> None:
    manager = CredentialManager(FakeCredentialStore())
    manager.save("openai", "sk-test-fake-secret-123")
    observation = manager.status_observation("openai")
    log = JsonlRunLog(tmp_path / "run.jsonl")

    log.append(
        RunEvent(
            timestamp=RunEvent.utc_now(),
            run_id="credential-test",
            iteration=1,
            event_type="credential_status",
            payload={"observation": observation.to_dict(), "raw_secret": "sk-test-fake-secret-123"},
        )
    )

    persisted = (tmp_path / "run.jsonl").read_text(encoding="utf-8")
    persisted_event = json.loads(persisted)

    assert "sk-test-fake-secret-123" not in persisted
    assert persisted_event["payload"]["observation"]["status"] == "available"


def test_secret_like_values_are_redacted_from_observation_and_feedback_payloads() -> None:
    secret = "sk-test-fake-secret-123"
    payload = {
        "observation": ToolObservation(
            tool="run_shell",
            status="failed",
            summary=f"TOKEN={secret}",
            data={"stdout_excerpt": f"OPENAI_API_KEY={secret}", "path": "credentials/local.txt"},
        ).to_dict(),
        "feedback": FeedbackReport(
            status="complete",
            category="command_error",
            passed=False,
            summary=f"command printed {secret}",
            raw_excerpt=f"stderr TOKEN={secret}",
        ).to_dict(),
        "direct_value": secret,
    }

    redacted = redact_for_logging(payload, secret_values=[secret])
    serialized = json.dumps(redacted, sort_keys=True)

    assert secret not in serialized
    assert "OPENAI_API_KEY" not in serialized
    assert "credentials/local.txt" not in serialized
    assert "[REDACTED]" in serialized

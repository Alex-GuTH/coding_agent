from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "Dockerfile"


def test_dockerfile_exists() -> None:
    assert DOCKERFILE.exists()


def test_dockerfile_does_not_copy_env_secrets() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")
    normalized = " ".join(text.lower().split())

    assert ".env" not in normalized
    assert "copy . ." not in normalized
    assert "add . ." not in normalized
    assert "openai_api_key" not in normalized
    assert "anthropic_api_key" not in normalized
    assert "api_key" not in normalized
    assert " token" not in normalized
    assert "secret" not in normalized
    assert "credential" not in normalized


def test_dockerfile_has_mock_safe_default_command_or_documented_entrypoint() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")
    normalized = " ".join(text.lower().split())

    assert "from python:" in normalized
    assert "pip install" in normalized
    assert "cmd" in normalized
    assert "safe-repair" in normalized
    assert "demo" in normalized
    assert any(name in normalized for name in ["guardrail", "feedback-classifier", "repair-loop"])
    assert "real" not in normalized

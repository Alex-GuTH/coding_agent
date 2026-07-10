from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
RENDER_CONFIG = ROOT / "render.yaml"


def deployment_text() -> str:
    chunks: list[str] = []
    if README.exists():
        chunks.append(README.read_text(encoding="utf-8"))
    if RENDER_CONFIG.exists():
        chunks.append(RENDER_CONFIG.read_text(encoding="utf-8"))
    return "\n".join(chunks).lower()


def test_deployment_config_exists_or_readme_documents_manual_deploy() -> None:
    readme_text = README.read_text(encoding="utf-8").lower() if README.exists() else ""

    assert RENDER_CONFIG.exists() or "manual deployment" in readme_text


def test_deployment_contract_documents_public_url_placeholder_before_deploy() -> None:
    text = deployment_text()

    assert "public url" in text
    assert "pending" in text or "manual" in text
    assert "health" in text
    assert "/demos/repair-loop" in text


def test_deployment_contract_records_public_smoke_after_deploy() -> None:
    text = deployment_text()

    assert "https://safe-test-repair-harness-mock-webui.onrender.com" in text
    assert "2026-07-11" in text
    assert "get /health" in text
    assert "/health` => `200" in text
    assert "get /demos/repair-loop" in text
    assert "/demos/repair-loop` => `200" in text
    assert "get /upload" in text
    assert "/upload` => `404" in text
    assert "workspace" in text
    assert "=> `400" in text
    assert "built-in mock repair-loop demo trace" in text


def test_deployment_contract_states_mock_only_no_real_key() -> None:
    text = deployment_text()

    assert "mock-only" in text
    assert "no real llm" in text or "does not require real llm" in text
    assert "does not require real llm keys" in text or "no real llm keys" in text
    forbidden = [
        "openai_api_key",
        "anthropic_api_key",
        "api_key",
        "token",
        "secret",
        "real_provider",
        "real-llm",
    ]
    for term in forbidden:
        assert term not in text


def test_deployment_contract_disallows_upload_and_arbitrary_workspace() -> None:
    text = deployment_text()

    assert "not an online ide" in text
    assert "does not accept arbitrary code upload" in text
    assert "does not execute arbitrary workspace" in text
    assert "does not execute arbitrary project" in text

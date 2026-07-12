from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
AGENT_LOG = ROOT / "AGENT_LOG.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def readme_text() -> str:
    return read(README).lower()


def test_readme_mentions_mock_demo_without_key() -> None:
    text = readme_text()

    assert "safe test-repair coding harness" in text
    assert "safe-repair demo guardrail" in text
    assert "safe-repair demo feedback-classifier" in text
    assert "safe-repair demo repair-loop" in text
    assert "no-key mock mode" in text
    assert "mock/stub tests and demos do not require real llm keys" in text


def test_readme_documents_docker_usage() -> None:
    text = readme_text()

    assert "docker build -t safe-test-repair-harness:local ." in text
    assert "docker run --rm safe-test-repair-harness:local" in text
    assert "docker pull ghcr.io/alex-guth/coding_agent:latest" in text
    assert "safe mock default command" in text


def test_readme_documents_github_actions_and_gitlab_ci() -> None:
    text = readme_text()

    assert ".github/workflows/ci.yml" in text
    assert "runs on push" in text
    assert "docker build" in text
    assert ".gitlab-ci.yml" in text
    assert "unit-test" in text
    assert "github actions is configured" in text
    assert "github actions passed" not in text


def test_readme_documents_credential_safety() -> None:
    text = readme_text()

    assert "credential safety" in text
    assert "fakecredentialstore" in text
    assert "missing_credential" in text
    assert "plaintext keys" in text
    assert "redact_for_logging" in text


def test_readme_states_apply_patch_is_post_mvp() -> None:
    text = readme_text()

    assert "apply_patch" in text
    assert "post-mvp" in text
    assert "unsupported_action" in text


def test_readme_documents_public_webui_url_and_smoke_endpoints() -> None:
    text = readme_text()

    assert "https://safe-test-repair-harness-mock-webui.onrender.com" in text
    assert "2026-07-11" in text
    assert "/health` => `200" in text
    assert "/demos/repair-loop` => `200" in text
    assert "/upload` => `404" in text
    assert "workspace" in text
    assert "=> `400" in text


def test_readme_documents_no_upload_and_no_arbitrary_workspace_execution() -> None:
    text = readme_text()

    assert "webui does not accept arbitrary code upload" in text
    assert "webui does not execute arbitrary workspace" in text
    assert "webui does not execute arbitrary project" in text
    assert "guardrails block dangerous actions" in text


def test_readme_maps_acceptance_deliverables_to_files() -> None:
    text = readme_text()

    expected = [
        "spec.md",
        "plan.md",
        "spec_process.md",
        "agent_log.md",
        "readme.md",
        "dockerfile",
        ".github/workflows/ci.yml",
        ".gitlab-ci.yml",
        "render.yaml",
        "src/safe_test_repair_harness/agent_loop.py",
        "src/safe_test_repair_harness/webui.py",
        "tests/",
    ]
    for item in expected:
        assert item in text


def test_readme_does_not_require_real_provider_env_vars_for_tests_ci_or_demos() -> None:
    text = readme_text()

    forbidden = [
        "openai_api_key",
        "anthropic_api_key",
        "api_key=",
        "token=",
        "secret=",
        "real_provider",
        "real-llm",
    ]
    for term in forbidden:
        assert term not in text


def test_agent_log_has_task_entries() -> None:
    text = read(AGENT_LOG)

    for task_id in range(1, 20):
        assert f"Task {task_id}" in text
    assert "Acceptance Sweep Notes" in text
    assert "README contract" in text

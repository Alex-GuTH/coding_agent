from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GITHUB_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
GITLAB_CI = ROOT / ".gitlab-ci.yml"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def assert_installs_pytest_before_running_tests(text: str) -> None:
    lines = [line.strip().lower() for line in text.splitlines()]
    pytest_run_index = next(index for index, line in enumerate(lines) if "pytest -v" in line)
    prior_lines = lines[:pytest_run_index]

    assert any("python -m pip install" in line and "pytest" in line for line in prior_lines)


def test_github_actions_workflow_exists() -> None:
    assert GITHUB_WORKFLOW.exists()


def test_github_actions_runs_on_push() -> None:
    text = read(GITHUB_WORKFLOW).lower()

    assert "on:" in text
    assert "push:" in text or "push]" in text or "- push" in text


def test_github_actions_has_test_job() -> None:
    text = read(GITHUB_WORKFLOW).lower()

    assert "jobs:" in text
    assert "test:" in text
    assert "python -m pip install" in text
    assert "pytest -v" in text
    assert_installs_pytest_before_running_tests(text)


def test_github_actions_has_docker_build_job() -> None:
    text = read(GITHUB_WORKFLOW).lower()

    assert "docker-build:" in text
    assert "docker build" in text
    assert "safe-test-repair-harness:ci" in text


def test_github_actions_publishes_docker_image_to_ghcr() -> None:
    text = read(GITHUB_WORKFLOW).lower()

    assert "packages: write" in text
    assert "docker-publish:" in text
    assert "ghcr.io/alex-guth/coding_agent:latest" in text
    assert "docker login ghcr.io" in text
    assert "docker push ghcr.io/alex-guth/coding_agent:latest" in text


def test_gitlab_ci_exists() -> None:
    assert GITLAB_CI.exists()


def test_gitlab_ci_contains_unit_test_job() -> None:
    text = read(GITLAB_CI).lower()

    assert "\nunit-test:" in f"\n{text}"
    assert "python -m pip install" in text
    assert "pytest -v" in text
    assert_installs_pytest_before_running_tests(text)


def test_ci_configs_do_not_reference_real_api_keys() -> None:
    combined = "\n".join(read(path) for path in [GITHUB_WORKFLOW, GITLAB_CI]).lower()

    forbidden = [
        "openai_api_key",
        "anthropic_api_key",
        "api_key",
        "token=",
        "secret=",
        "secrets.",
        "sk-",
        "real_provider",
        "real-llm",
    ]
    for term in forbidden:
        assert term not in combined

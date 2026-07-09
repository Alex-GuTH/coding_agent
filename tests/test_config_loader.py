from pathlib import Path

import pytest

from safe_test_repair_harness.config import ConfigError, load_config
from safe_test_repair_harness.models import HarnessConfig


FIXTURES = Path(__file__).parent / "fixtures" / "config"


def test_loads_minimal_config_with_mock_provider():
    config = load_config(FIXTURES / "minimal.toml")

    assert isinstance(config, HarnessConfig)
    assert config.workspace == str((FIXTURES / ".").resolve())
    assert config.provider == "mock"


def test_default_test_command_is_pytest_argv():
    config = load_config(FIXTURES / "minimal.toml")

    assert config.test_command == ["python", "-m", "pytest"]


def test_default_allowed_commands_only_include_test_command():
    config = load_config(FIXTURES / "minimal.toml")

    assert config.allowed_commands == [config.test_command]
    assert ["cmd", "/c", "dir"] not in config.allowed_commands
    assert ["bash", "-lc", "ls"] not in config.allowed_commands


def test_default_blocked_paths_include_env_git_and_secret_patterns():
    config = load_config(FIXTURES / "minimal.toml")

    assert ".env" in config.blocked_paths
    assert ".git" in config.blocked_paths
    assert any("secret" in pattern for pattern in config.blocked_paths)
    assert any("token" in pattern for pattern in config.blocked_paths)
    assert any("credential" in pattern for pattern in config.blocked_paths)


def test_default_limits_are_finite_and_positive():
    config = load_config(FIXTURES / "minimal.toml")

    assert isinstance(config.max_iterations, int)
    assert isinstance(config.timeout_seconds, int)
    assert 0 < config.max_iterations <= 50
    assert 0 < config.timeout_seconds <= 600


def test_rejects_workspace_escape_in_protected_path():
    with pytest.raises(ConfigError, match="workspace"):
        load_config(FIXTURES / "unsafe.toml")


def test_rejects_blocked_path_glob_with_parent_traversal(tmp_path):
    config_path = tmp_path / "blocked-parent-glob.toml"
    config_path.write_text('workspace = "."\nblocked_paths = ["../*"]\n', encoding="utf-8")

    with pytest.raises(ConfigError, match="blocked_paths"):
        load_config(config_path)


def test_rejects_blocked_path_pattern_with_path_separator(tmp_path):
    config_path = tmp_path / "blocked-path-pattern.toml"
    config_path.write_text('workspace = "."\nblocked_paths = ["secrets/*"]\n', encoding="utf-8")

    with pytest.raises(ConfigError, match="blocked_paths"):
        load_config(config_path)


def test_rejects_unsafe_test_command_even_if_allowed_commands_match(tmp_path):
    config_path = tmp_path / "unsafe-command.toml"
    config_path.write_text(
        '\n'.join(
            [
                'workspace = "."',
                'test_command = ["cmd", "/c", "dir"]',
                'allowed_commands = [["cmd", "/c", "dir"]]',
                "",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="test_command"):
        load_config(config_path)


def test_accepts_secret_like_blocked_path_patterns_without_traversal(tmp_path):
    config_path = tmp_path / "safe-secret-patterns.toml"
    config_path.write_text(
        '\n'.join(
            [
                'workspace = "."',
                'blocked_paths = [".env", ".git", "*secret*", "*credential*", "*token*"]',
                "",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert "*secret*" in config.blocked_paths
    assert "*credential*" in config.blocked_paths
    assert "*token*" in config.blocked_paths


def test_defaults_do_not_enable_real_llm(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-real-secret")

    config = load_config(FIXTURES / "minimal.toml")

    assert config.provider == "mock"
    assert "sk-real-secret" not in config.to_json()


def test_rejects_negative_timeout_seconds(tmp_path):
    config_path = tmp_path / "negative-timeout.toml"
    config_path.write_text('workspace = "."\ntimeout_seconds = -1\n', encoding="utf-8")

    with pytest.raises(ConfigError, match="timeout_seconds"):
        load_config(config_path)

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from safe_test_repair_harness.models import HarnessConfig


class ConfigError(ValueError):
    pass


def load_config(path: str | Path) -> HarnessConfig:
    config_path = Path(path)
    try:
        data = _read_config(config_path)
        workspace = _resolve_workspace(config_path, data)
        values = dict(data)
        values["workspace"] = str(workspace)
        config = HarnessConfig(**values)
        _validate_config(config, workspace)
        return config
    except ConfigError:
        raise
    except (TypeError, ValueError) as error:
        raise ConfigError(str(error)) from error


def _read_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Config file does not exist: {path}")
    if path.suffix == ".toml":
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    elif path.suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    else:
        raise ConfigError("Config file must be TOML or JSON")

    if not isinstance(data, dict):
        raise ConfigError("Config root must be an object")
    return data


def _resolve_workspace(config_path: Path, data: dict[str, Any]) -> Path:
    raw_workspace = data.get("workspace")
    if not isinstance(raw_workspace, str) or not raw_workspace:
        raise ConfigError("workspace is required")

    workspace = Path(raw_workspace)
    if not workspace.is_absolute():
        workspace = config_path.parent / workspace
    return workspace.resolve()


def _validate_config(config: HarnessConfig, workspace: Path) -> None:
    if config.provider != "mock":
        raise ConfigError("provider must default to mock for Task 3")
    if config.allowed_commands != [config.test_command]:
        raise ConfigError("allowed_commands must only include test_command by default")
    if config.max_iterations <= 0:
        raise ConfigError("max_iterations must be positive")
    if config.timeout_seconds <= 0:
        raise ConfigError("timeout_seconds must be positive")

    for blocked_path in config.blocked_paths:
        _validate_blocked_path(blocked_path, workspace)


def _validate_blocked_path(blocked_path: str, workspace: Path) -> None:
    if "*" in blocked_path:
        return

    candidate = Path(blocked_path)
    if not candidate.is_absolute():
        candidate = workspace / candidate
    resolved = candidate.resolve()

    if not resolved.is_relative_to(workspace):
        raise ConfigError("blocked_paths must stay within workspace or use explicit patterns")

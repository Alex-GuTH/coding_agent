from pathlib import Path

from safe_test_repair_harness.guardrails import GuardrailEngine
from safe_test_repair_harness.models import Action, GuardrailDecision, HarnessConfig


def make_config(workspace: Path, **overrides) -> HarnessConfig:
    return HarnessConfig(workspace=str(workspace), **overrides)


def test_blocks_write_outside_workspace(tmp_path):
    config = make_config(tmp_path)
    action = Action(type="write_file", path=str(tmp_path.parent / "outside.py"), content="x = 1")

    decision = GuardrailEngine(config).check(action)

    assert isinstance(decision, GuardrailDecision)
    assert decision.status == "blocked"
    assert decision.reason_code == "path_outside_workspace"
    assert decision.requires_human is False


def test_blocks_protected_file_write(tmp_path):
    config = make_config(tmp_path)
    action = Action(type="write_file", path=".env", content="OPENAI_API_KEY=abc123")

    decision = GuardrailEngine(config).check(action)

    assert decision.status == "blocked"
    assert decision.reason_code == "blocked_path"
    assert decision.action_type == "write_file"
    assert decision.path == ".env"


def test_blocks_dangerous_shell_command(tmp_path):
    config = make_config(tmp_path)
    action = Action(type="run_shell", command=["rm", "-rf", "."])

    decision = GuardrailEngine(config).check(action)

    assert decision.status == "blocked"
    assert decision.reason_code == "dangerous_command"
    assert decision.command == ["rm", "-rf", "."]


def test_rejects_shell_chaining_and_redirection(tmp_path):
    config = make_config(tmp_path)

    chained = GuardrailEngine(config).check(Action(type="run_shell", command="pytest && rm -rf ."))
    redirected = GuardrailEngine(config).check(Action(type="run_shell", command="pytest > output.txt"))

    assert chained.status == "blocked"
    assert chained.reason_code == "shell_metacharacter"
    assert redirected.status == "blocked"
    assert redirected.reason_code == "shell_metacharacter"


def test_allows_safe_read_inside_workspace(tmp_path):
    config = make_config(tmp_path)
    inside = tmp_path / "src" / "app.py"
    action = Action(type="read_file", path=str(inside))

    decision = GuardrailEngine(config).check(action)

    assert decision.status == "allowed"
    assert decision.reason_code == "safe_action"
    assert decision.path == str(inside)
    assert decision.requires_human is False


def test_requires_approval_for_configured_action(tmp_path):
    config = make_config(tmp_path, approval_mode="require_write_file")
    action = Action(type="write_file", path="src/app.py", content="print('safe')")

    decision = GuardrailEngine(config).check(action)

    assert decision.status == "approval_required"
    assert decision.reason_code == "configured_approval_required"
    assert decision.action_type == "write_file"
    assert decision.requires_human is True


def test_uncertain_safety_defaults_to_blocked(tmp_path):
    config = make_config(tmp_path)
    action = Action(type="write_file", content="missing path")

    decision = GuardrailEngine(config).check(action)

    assert decision.status == "blocked"
    assert decision.reason_code == "missing_path"
    assert decision.requires_human is False


def test_approval_required_only_for_explicit_config_or_threshold(tmp_path):
    default_config = make_config(tmp_path)
    explicit_config = make_config(tmp_path, approval_mode="require_write_file")
    threshold_config = make_config(tmp_path, approval_mode="manual", write_limit=4)

    safe_write = Action(type="write_file", path="src/app.py", content="abcd")
    large_write = Action(type="write_file", path="src/app.py", content="abcde")

    default_decision = GuardrailEngine(default_config).check(safe_write)
    explicit_decision = GuardrailEngine(explicit_config).check(safe_write)
    threshold_decision = GuardrailEngine(threshold_config).check(large_write)
    uncertain_decision = GuardrailEngine(threshold_config).check(Action(type="write_file", content="abcde"))

    assert default_decision.status == "allowed"
    assert explicit_decision.status == "approval_required"
    assert explicit_decision.reason_code == "configured_approval_required"
    assert threshold_decision.status == "approval_required"
    assert threshold_decision.reason_code == "write_limit_threshold"
    assert uncertain_decision.status == "blocked"
    assert uncertain_decision.reason_code == "missing_path"

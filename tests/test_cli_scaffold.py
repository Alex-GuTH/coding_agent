import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def test_package_imports():
    sys.path.insert(0, str(SRC))

    import safe_test_repair_harness

    assert safe_test_repair_harness.__version__


def test_cli_help_exits_zero():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)

    result = subprocess.run(
        [sys.executable, "-m", "safe_test_repair_harness.cli", "--help"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "safe-repair" in result.stdout


def test_agent_log_contains_required_fields():
    log_path = ROOT / "AGENT_LOG.md"

    content = log_path.read_text(encoding="utf-8")

    required_fields = [
        "task id",
        "subagent",
        "prompt/context",
        "test commands",
        "test results",
        "human modifications",
        "review outcome",
        "commit hash",
    ]

    lowered = content.lower()
    for field in required_fields:
        assert field in lowered

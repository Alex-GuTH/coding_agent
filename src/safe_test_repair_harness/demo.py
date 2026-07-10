from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from safe_test_repair_harness.feedback import FeedbackAnalyzer
from safe_test_repair_harness.guardrails import GuardrailEngine
from safe_test_repair_harness.agent_loop import AgentLoop
from safe_test_repair_harness.llm import MockLLMProvider
from safe_test_repair_harness.models import Action, HarnessConfig
from safe_test_repair_harness.memory import JsonlRunLog
from safe_test_repair_harness.process_runner import FakeProcessRunner, ProcessResult
from safe_test_repair_harness.tools import ToolDispatcher


def guardrail_demo() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="safe-repair-demo-") as workspace:
        action = Action(type="run_shell", command=["rm", "-rf", "."])
        decision = GuardrailEngine(HarnessConfig(workspace=workspace)).check(action)

    return {
        "demo": "guardrail",
        "mechanism": "code_guardrail",
        "llm_provider": "none",
        "workspace_mode": "built_in_temp_workspace",
        "status": decision.status,
        "reason_code": decision.reason_code,
        "action": {"type": action.type, "command": action.command},
        "trace": [
            {
                "event_type": "guardrail_decision",
                "status": decision.status,
                "reason_code": decision.reason_code,
                "action_type": decision.action_type,
            }
        ],
    }


def feedback_classifier_demo() -> dict[str, Any]:
    analyzer = FeedbackAnalyzer()
    samples = {
        "pass": ProcessResult(stdout="================ 1 passed in 0.01s ================\n", exit_code=0),
        "assertion": ProcessResult(
            stdout="FAILED tests/test_app.py::test_answer - AssertionError\n",
            exit_code=1,
        ),
        "import": ProcessResult(
            stderr="ModuleNotFoundError: No module named 'missing_package'\n",
            exit_code=1,
        ),
        "syntax": ProcessResult(
            stderr='File "app.py", line 1\n    def broken(:\nSyntaxError: invalid syntax\n',
            exit_code=1,
        ),
    }
    reports = {name: analyzer.analyze(result) for name, result in samples.items()}

    return {
        "demo": "feedback-classifier",
        "mechanism": "deterministic_feedback_analyzer",
        "llm_provider": "none",
        "categories": {name: report.category for name, report in reports.items()},
        "trace": [
            {
                "sample": name,
                "category": report.category,
                "passed": report.passed,
                "timed_out": report.timed_out,
            }
            for name, report in reports.items()
        ],
    }


def repair_loop_demo() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="safe-repair-demo-") as workspace:
        workspace_path = Path(workspace)
        config = HarnessConfig(workspace=workspace, max_iterations=3)
        provider = MockLLMProvider(
            [
                '{"type":"run_tests"}',
                '{"type":"write_file","path":"app.py","content":"def answer():\\n    return 42\\n"}',
                '{"type":"run_tests"}',
            ]
        )
        runner = FakeProcessRunner(
            [
                ProcessResult(stdout="FAILED tests/test_app.py::test_answer - AssertionError\n", exit_code=1),
                ProcessResult(stdout="================ 1 passed in 0.01s ================\n", exit_code=0),
            ]
        )
        dispatcher = ToolDispatcher(config, runner=runner)
        result = AgentLoop(
            config=config,
            provider=provider,
            dispatcher=dispatcher,
            run_log=JsonlRunLog(workspace_path / "demo-run.jsonl"),
        ).run("repair failing tests", run_id="demo-repair-loop")

        actions = [
            event.payload["action"]["type"]
            for event in result.trace
            if event.event_type == "parsed_action"
        ]
        feedback_categories = [
            event.payload["category"]
            for event in result.trace
            if event.event_type == "feedback_report"
        ]

    return {
        "demo": "repair-loop",
        "mechanism": "deterministic_feedback_loop",
        "llm_provider": "mock",
        "workspace_mode": "built_in_temp_workspace",
        "success": result.success,
        "iterations": result.iterations,
        "final_stop_reason": result.stop.reason_code,
        "actions": actions,
        "feedback_categories": feedback_categories,
        "next_action_changed_after_feedback": actions[:2] == ["run_tests", "write_file"]
        and feedback_categories[:1] == ["assertion_failure"],
        "trace": [
            {
                "event_type": event.event_type,
                "iteration": event.iteration,
                "payload": event.payload,
            }
            for event in result.trace
        ],
    }

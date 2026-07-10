from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from safe_test_repair_harness.action_parser import ActionParser
from safe_test_repair_harness.guardrails import GuardrailEngine
from safe_test_repair_harness.llm import LLMProvider
from safe_test_repair_harness.memory import JsonlRunLog
from safe_test_repair_harness.models import FeedbackReport, HarnessConfig, RunEvent, StopDecision, ToolObservation
from safe_test_repair_harness.stop_policy import StopPolicy
from safe_test_repair_harness.tools import Guardrail, ToolDispatcher


@dataclass
class AgentRunResult:
    success: bool
    stop: StopDecision
    iterations: int
    trace: list[RunEvent]
    run_id: str
    log_path: str


class AgentLoop:
    def __init__(
        self,
        config: HarnessConfig,
        provider: LLMProvider,
        parser: ActionParser | None = None,
        guardrail: Guardrail | None = None,
        dispatcher: ToolDispatcher | None = None,
        run_log: JsonlRunLog | None = None,
        stop_policy: StopPolicy | None = None,
    ) -> None:
        self.config = config
        self.provider = provider
        self.parser = parser or ActionParser()
        self.guardrail = guardrail or GuardrailEngine(config)
        self.dispatcher = dispatcher or ToolDispatcher(config, guardrail=self.guardrail)
        self.run_log = run_log
        self.stop_policy = stop_policy or StopPolicy(config.max_iterations)
        self._trace: list[RunEvent] = []

    def run(self, task: str, run_id: str | None = None) -> AgentRunResult:
        active_run_id = run_id or "run"
        self._trace = []
        log = self.run_log or self._default_run_log(active_run_id)
        stop = StopDecision(
            should_stop=True,
            reason_code="max_iterations",
            success=False,
            message="No iterations were run.",
        )
        iterations_run = 0

        for iteration in range(1, self.config.max_iterations + 1):
            iterations_run = iteration
            provider_result = self.provider.generate(self._build_context(task, log))
            if provider_result.ok:
                self._record(log, active_run_id, iteration, "provider_output", provider_result.to_dict())
            else:
                self._record(log, active_run_id, iteration, "provider_error", provider_result.to_dict())
                stop = self.stop_policy.decide(iteration, provider_error=provider_result.error_code)
                self._record(log, active_run_id, iteration, "stop_decision", stop.to_dict())
                break

            parse_result = self.parser.parse(provider_result.text)
            if parse_result.status == "parse_error":
                self._record(
                    log,
                    active_run_id,
                    iteration,
                    "parser_error",
                    {
                        "status": parse_result.status,
                        "error_code": parse_result.error_code,
                        "message": parse_result.message,
                        "observation": parse_result.observation.to_dict() if parse_result.observation else None,
                    },
                )
                stop = self.stop_policy.decide(iteration, parser_error=parse_result.error_code)
                self._record(log, active_run_id, iteration, "stop_decision", stop.to_dict())
                break

            if parse_result.status == "unsupported_action":
                observation = parse_result.observation or ToolObservation(
                    tool="action_parser",
                    status="unsupported_action",
                    summary=parse_result.message,
                    error_code=parse_result.error_code,
                )
                self._record(
                    log,
                    active_run_id,
                    iteration,
                    "tool_observation",
                    {"observation": observation.to_dict()},
                )
                stop = self.stop_policy.decide(iteration, observation=observation)
                self._record(log, active_run_id, iteration, "stop_decision", stop.to_dict())
                if stop.should_stop:
                    break
                continue

            action = parse_result.action
            if action is None:
                stop = self.stop_policy.decide(iteration, parser_error="missing_action")
                self._record(log, active_run_id, iteration, "stop_decision", stop.to_dict())
                break

            self._record(log, active_run_id, iteration, "parsed_action", {"action": action.to_dict()})
            decision = self.guardrail.check(action)
            self._record(log, active_run_id, iteration, "guardrail_decision", decision.to_dict())

            if decision.status == "allowed":
                observation = self.dispatcher.dispatch(action)
            else:
                observation = ToolObservation(
                    tool=action.type,
                    status=decision.status,
                    summary=decision.message,
                    data={"guardrail": decision.to_dict()},
                    error_code=decision.reason_code,
                    metadata={"requires_human": decision.requires_human},
                )

            self._record(
                log,
                active_run_id,
                iteration,
                "tool_observation",
                {"observation": observation.to_dict()},
            )
            if decision.status != "allowed":
                stop = StopDecision(
                    should_stop=True,
                    reason_code=decision.reason_code,
                    success=False,
                    message=decision.message,
                    metadata={"iteration": iteration, "guardrail_status": decision.status},
                )
                self._record(log, active_run_id, iteration, "stop_decision", stop.to_dict())
                break

            feedback = observation.feedback if isinstance(observation.feedback, FeedbackReport) else None
            if feedback is not None:
                self._record(log, active_run_id, iteration, "feedback_report", feedback.to_dict())

            stop = self.stop_policy.decide(iteration, observation=observation, feedback=feedback, action=action)
            self._record(log, active_run_id, iteration, "stop_decision", stop.to_dict())
            if stop.should_stop:
                break

        return AgentRunResult(
            success=stop.success,
            stop=stop,
            iterations=iterations_run,
            trace=list(self._trace),
            run_id=active_run_id,
            log_path=str(log.path),
        )

    def _build_context(self, task: str, log: JsonlRunLog) -> dict[str, Any]:
        return {
            "task": task,
            "config": {
                "provider": self.config.provider,
                "max_iterations": self.config.max_iterations,
                "allowed_tools": list(self.config.allowed_tools),
            },
            "memory": log.select_context(),
        }

    def _record(
        self,
        log: JsonlRunLog,
        run_id: str,
        iteration: int,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        event = RunEvent(
            timestamp=RunEvent.utc_now(),
            run_id=run_id,
            iteration=iteration,
            event_type=event_type,
            payload=payload,
        )
        log.append(event)
        self._trace.append(RunEvent(**event.to_dict()))

    def _default_run_log(self, run_id: str) -> JsonlRunLog:
        return JsonlRunLog(Path(self.config.workspace) / self.config.run_log_dir / f"{run_id}.jsonl")

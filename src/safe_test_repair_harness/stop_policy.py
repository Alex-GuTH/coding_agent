from __future__ import annotations

from safe_test_repair_harness.models import Action, FeedbackReport, StopDecision, ToolObservation


class StopPolicy:
    def __init__(self, max_iterations: int) -> None:
        if max_iterations <= 0:
            raise ValueError("max_iterations must be positive")
        self.max_iterations = max_iterations

    def decide(
        self,
        iteration: int,
        observation: ToolObservation | None = None,
        feedback: FeedbackReport | None = None,
        action: Action | None = None,
        provider_error: str | None = None,
        parser_error: str | None = None,
    ) -> StopDecision:
        if _tests_passed(feedback):
            return StopDecision(
                should_stop=True,
                reason_code="tests_passed",
                success=True,
                message="Tests passed.",
                metadata={"category": feedback.category, "iteration": iteration},
            )

        if provider_error:
            return StopDecision(
                should_stop=True,
                reason_code="unrecoverable_provider_error",
                success=False,
                message="Provider error is unrecoverable.",
                metadata={"error_code": provider_error, "iteration": iteration},
            )

        if parser_error:
            return StopDecision(
                should_stop=True,
                reason_code="unrecoverable_parser_error",
                success=False,
                message="Parser error is unrecoverable.",
                metadata={"error_code": parser_error, "iteration": iteration},
            )

        if _is_unrecoverable_tool_error(observation):
            return StopDecision(
                should_stop=True,
                reason_code="unrecoverable_tool_error",
                success=False,
                message="Tool error is unrecoverable.",
                metadata={"error_code": observation.error_code, "iteration": iteration},
            )

        if action is not None and action.type == "finish":
            return StopDecision(
                should_stop=True,
                reason_code="finish_without_passing_tests",
                success=False,
                message="Finish requested before objective tests passed.",
                metadata={"iteration": iteration},
            )

        if iteration >= self.max_iterations:
            return StopDecision(
                should_stop=True,
                reason_code="max_iterations",
                success=False,
                message="Maximum iterations reached.",
                metadata={"iteration": iteration, "max_iterations": self.max_iterations},
            )

        return StopDecision(
            should_stop=False,
            reason_code="continue",
            success=False,
            message="Continue.",
            metadata={"iteration": iteration},
        )


def _tests_passed(feedback: FeedbackReport | None) -> bool:
    return feedback is not None and feedback.passed is True and feedback.category == "tests_passed"


def _is_unrecoverable_tool_error(observation: ToolObservation | None) -> bool:
    if observation is None:
        return False
    return observation.status == "tool_error" or observation.error_code == "unrecoverable_tool_error"

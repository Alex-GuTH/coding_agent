from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Protocol

from safe_test_repair_harness.models import ToolObservation


@dataclass(frozen=True)
class ProcessResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    timed_out: bool = False
    duration_ms: int = 0

    def to_observation(self, tool: str) -> ToolObservation:
        if self.timed_out:
            status = "timeout"
            error_code = "timeout"
            summary = "Process timed out"
        elif self.exit_code == 0:
            status = "ok"
            error_code = None
            summary = "Process exited successfully"
        else:
            status = "failed"
            error_code = "nonzero_exit"
            summary = f"Process exited with code {self.exit_code}"

        return ToolObservation(
            tool=tool,
            status=status,
            summary=summary,
            data={
                "stdout": self.stdout,
                "stderr": self.stderr,
                "exit_code": self.exit_code,
                "timed_out": self.timed_out,
                "duration_ms": self.duration_ms,
            },
            error_code=error_code,
        )


class Runner(Protocol):
    def run(self, argv: list[str], timeout_seconds: float) -> ProcessResult:
        ...


class ProcessRunner:
    def run(self, argv: list[str], timeout_seconds: float) -> ProcessResult:
        _validate_argv(argv)
        started = time.monotonic()

        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            return ProcessResult(
                stdout=_decode_timeout_output(error.stdout),
                stderr=_decode_timeout_output(error.stderr),
                exit_code=None,
                timed_out=True,
                duration_ms=_elapsed_ms(started),
            )

        return ProcessResult(
            stdout=completed.stdout,
            stderr=completed.stderr,
            exit_code=completed.returncode,
            timed_out=False,
            duration_ms=_elapsed_ms(started),
        )


class FakeProcessRunner:
    def __init__(self, scripted_results: list[ProcessResult]) -> None:
        self._scripted_results = list(scripted_results)
        self._cursor = 0

    def run(self, argv: list[str], timeout_seconds: float) -> ProcessResult:
        _validate_argv(argv)
        if self._cursor >= len(self._scripted_results):
            return ProcessResult(
                stdout="",
                stderr="FakeProcessRunner script exhausted",
                exit_code=1,
                timed_out=False,
                duration_ms=0,
            )

        result = self._scripted_results[self._cursor]
        self._cursor += 1
        return result


def _validate_argv(argv: list[str]) -> None:
    if isinstance(argv, str):
        raise TypeError("argv must be a list of strings, not a shell string")
    if not isinstance(argv, list) or not argv or not all(isinstance(part, str) and part for part in argv):
        raise TypeError("argv must be a non-empty list of strings")


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.monotonic() - started) * 1000))


def _decode_timeout_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value

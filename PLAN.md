# Safe Test-Repair Coding Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` for task-by-task implementation, or `superpowers:executing-plans` for inline execution. Each task must follow TDD: write failing tests, confirm red, implement the minimum, confirm green, then refactor.

**Goal:** Build a Python Safe Test-Repair Coding Harness that implements its own agent loop, mockable LLM provider, controlled tools, code-level guardrails, deterministic test feedback, JSONL memory, CLI, mock WebUI demo, Docker distribution, and CI.

**Architecture:** The delivered harness owns the loop: context selection, LLM call, action parsing, guardrail check, tool dispatch, feedback analysis, memory logging, and stop decision. The LLM is replaceable and mock-first; tests and CI must use mock/stub providers only. Mechanisms must be implemented in code, not delegated to prompts or existing agent runners.

**Tech Stack:** Python 3.11+, pytest, standard-library dataclasses/enums/pathlib/subprocess/json/tomllib/http.server, Docker, GitHub Actions, GitLab CI syntax for `.gitlab-ci.yml`.

## Global Constraints

- Do not write implementation before a task's failing tests are written and confirmed red.
- Task granularity should be moderate: each task must deliver one reviewable, testable mechanism slice. Do not split work into fragments that only create files, rename constants, or add isolated placeholders.
- Do not use LangChain `AgentExecutor`, AutoGen, CrewAI, LlamaIndex agent, or any existing agent runner.
- Real LLM provider support is optional and must not be required by tests, CI, WebUI smoke, Docker build, or mechanism demos.
- All core mechanism tests must use mock/stub LLM and must not access the network.
- `apply_patch` is post-MVP. MVP behavior for an `apply_patch` action is `unsupported_action`.
- GitHub Actions must run tests on every push and, because Docker distribution is selected, build the Docker image.
- `.gitlab-ci.yml` must exist and contain a job named `unit-test`.
- The WebUI must run only built-in mock demos and must not allow arbitrary code upload or arbitrary workspace execution.
- Credential tests must use a fake keyring or stub secret store; tests must not require real keyring state or real API keys.
- `AGENT_LOG.md` must be updated after each implementation task with task id, skill used, key decision, verification command, result, and commit hash when available.

## Process Rules

- Each task follows red-green-refactor. First write the named failing tests, then run the task-specific pytest command and confirm the expected red result, then implement the minimum behavior, then run the verification command until green.
- After each completed task, update the `Task Status Tracker` in `PLAN.md`: set `Status` to `Done`, replace `Completed commit` with the task commit hash, and set `Review status` to `Passed` only after the required review gate passes.
- After each completed task, update `AGENT_LOG.md` with task id, subagent identity or execution mode, prompt/context summary, test commands, test results, human modifications, review outcome, and commit hash.
- Larger integration tasks still remain single reviewable mechanism slices, but their implementation must be executed through the listed 2-5 minute substeps so a subagent can make visible TDD progress.
- Do not start the next dependent task until Critical review issues from the current task are fixed.

## Task Status Tracker

Each task must maintain these fixed status fields:

- `Status: Pending / Done`
- `Completed commit: N/A`
- `Review status: Pending / Passed`

| Task | Status | Completed commit | Review status |
| --- | --- | --- | --- |
| Task 1 | Done | 138b17f | Passed |
| Task 2 | Done | ac5bf76 | Passed |
| Task 3 | Done | 3fd64b9 | Passed |
| Task 4 | Done | ef5bde2 | Passed |
| Task 5 | Done | 98d85d3 | Passed |
| Task 6 | Done | a39d08f | Passed |
| Task 7 | Done | b1c57c2 | Passed |
| Task 8 | Pending | N/A | Pending |
| Task 9 | Pending | N/A | Pending |
| Task 10 | Pending | N/A | Pending |
| Task 11 | Pending | N/A | Pending |
| Task 12 | Pending | N/A | Pending |
| Task 13 | Pending | N/A | Pending |
| Task 14 | Pending | N/A | Pending |
| Task 15 | Pending | N/A | Pending |
| Task 16 | Pending | N/A | Pending |
| Task 17 | Pending | N/A | Pending |
| Task 18 | Pending | N/A | Pending |
| Task 19 | Pending | N/A | Pending |
| Task 20 | Pending | N/A | Pending |

## Planned File Structure

- `pyproject.toml`: package metadata, pytest config, console script, dev dependencies.
- `README.md`: installation, mock demo, CLI, WebUI, Docker, CI, credentials, safety boundaries, limitations.
- `AGENT_LOG.md`: process log updated during implementation.
- `Dockerfile`: container distribution.
- `.github/workflows/ci.yml`: GitHub Actions workflow for push tests and Docker build.
- `.gitlab-ci.yml`: required CI deliverable with `unit-test` job.
- `src/safe_test_repair_harness/__init__.py`: package marker and version.
- `src/safe_test_repair_harness/models.py`: shared data models.
- `src/safe_test_repair_harness/config.py`: config loader and validation.
- `src/safe_test_repair_harness/llm.py`: provider protocol, mock provider, optional real-provider boundary.
- `src/safe_test_repair_harness/action_parser.py`: JSON action parsing and validation.
- `src/safe_test_repair_harness/guardrails.py`: path, command, file, and approval guardrails.
- `src/safe_test_repair_harness/process_runner.py`: real and fake process runners.
- `src/safe_test_repair_harness/feedback.py`: pytest output classifier.
- `src/safe_test_repair_harness/tools.py`: tool dispatcher and tool handlers.
- `src/safe_test_repair_harness/memory.py`: JSONL run log and context selection.
- `src/safe_test_repair_harness/stop_policy.py`: stopping rules.
- `src/safe_test_repair_harness/agent_loop.py`: harness main loop.
- `src/safe_test_repair_harness/credentials.py`: credential manager and fake keyring boundary.
- `src/safe_test_repair_harness/cli.py`: CLI commands.
- `src/safe_test_repair_harness/demo.py`: deterministic mechanism demos.
- `src/safe_test_repair_harness/webui.py`: built-in mock WebUI demo.
- `tests/`: pytest suite, grouped by module.
- `tests/fixtures/`: sample pytest outputs, mock configs, demo workspaces.

## Parallelization Map

- Task 1 must be first.
- Task 2 should follow Task 1 and unlocks most other tasks.
- After Task 2, Tasks 3, 4, 5, 6, 7, 8, 10, and 13 can be developed in separate git worktrees if each subagent only edits its assigned files and tests.
- Task 9 depends on Tasks 5, 6, 7, and 8.
- Task 12 depends on Tasks 4, 5, 9, 10, and 11.
- Tasks 14 and 15 depend on Task 12.
- Tasks 16 and 17 depend on the CLI/demo test path from Task 14.
- Task 18 depends on Tasks 15, 16, and 17 because deployment smoke should use the actual WebUI, Docker, and CI-compatible commands.
- Task 19 should be near-last because README and acceptance docs must reflect actual commands, deployment URL, and behavior.
- Task 20 is final process review and should run after implementation evidence, cold-start validation, PR/review notes, and CI/deployment status are available.

## Worktree and PR Protocol

- Each parallelizable task should use its own git worktree created from the same base branch.
- Each worktree should produce one PR for one task only.
- PR descriptions must include task id, subagent identity or execution mode, files changed, tests written, verification commands, results, human modifications, and known residual risks.
- Review happens in two stages: first SPEC/PLAN compliance, then code quality and maintainability.
- Critical review issues must be fixed before merging the PR or starting the next dependent task.
- Non-critical review notes may be recorded in `AGENT_LOG.md` and either fixed in the same task or deferred with a clear reason.
- Non-parallel integration tasks should still have their own PR or at least their own review checkpoint.
- Do not combine multiple tasks into one large PR unless the dependency structure makes separate review impossible; if combined, document the reason in `AGENT_LOG.md`.

---

## Task 1: Project Scaffold, Pytest, CLI Skeleton, and AGENT_LOG Rules

**Goal:** Create the Python package skeleton, test runner configuration, minimal CLI entrypoint contract, and process-log update rule.

**Files:**
- Create: `pyproject.toml`
- Create: `src/safe_test_repair_harness/__init__.py`
- Create: `src/safe_test_repair_harness/cli.py`
- Create: `tests/test_cli_scaffold.py`
- Create: `AGENT_LOG.md`

**Expected implementation points:**
- Define package name `safe-test-repair-harness`.
- Configure pytest to discover `tests/`.
- Expose a CLI command such as `safe-repair`.
- CLI help should work before real harness behavior exists.
- `AGENT_LOG.md` should define the required log entry format for later tasks.

**Failing tests first:**
- `test_package_imports`.
- `test_cli_help_exits_zero`.
- `test_agent_log_contains_required_fields`.

**Confirm red:**
- Run `pytest tests/test_cli_scaffold.py -v`.
- Expected: fails because package, CLI entrypoint, or `AGENT_LOG.md` does not exist yet.

**Minimum green implementation:**
- Add only the package skeleton, minimal CLI help path, pytest config, and process-log template.
- Do not implement agent loop behavior.

**Refactor checkpoint:**
- Confirm package name, import path, and CLI command are stable before later tasks depend on them.
- Remove any placeholder CLI behavior that pretends to run the harness.

**Verification command:**
- `pytest tests/test_cli_scaffold.py -v`

**Dependencies:** None.

**Parallelizable:** No. This task initializes shared structure.

**Suggested commit message:** `chore: scaffold python package and process log`

---

## Task 2: Core Data Models

**Goal:** Define shared models used by parser, guardrails, tools, feedback, memory, stop policy, and agent loop.

**Files:**
- Create: `src/safe_test_repair_harness/models.py`
- Create: `tests/test_models.py`

**Expected implementation points:**
- Define `Action` with fields aligned to `SPEC.md`: `type`, `path`, `content`, `patch`, `command`, `reason`, and `metadata`.
- `Action.type` is the external JSON and internal model action discriminator; do not introduce `name` or another internal discriminator as a normative field.
- Raw provider text belongs in parser result or `metadata`, not as a required `Action` field.
- Define `GuardrailDecision` with fields: `status`, `reason_code`, `message`, `action_type`, `path`, `command`, `requires_human`, and `metadata`.
- Do not use `reason`, `rule_id`, or `approval_data` as normative `GuardrailDecision` fields.
- Define `ToolObservation` with fields: `tool`, `status`, `summary`, `data`, `error_code`, `feedback`, and `metadata`.
- Put stdout/stderr, exit_code, and duration_ms in `ToolObservation.data`, or represent them through `ProcessResult` / `FeedbackReport`.
- Define `FeedbackReport` with fields: `status`, `category`, `passed`, `summary`, `failing_tests`, `locations`, `raw_excerpt`, `timed_out`, and `metadata`.
- `FeedbackReport.category` must be one of: `tests_passed`, `assertion_failure`, `syntax_error`, `import_error`, `missing_file`, `timeout`, `command_error`, `no_tests_collected`, `unknown_failure`.
- Do not use `type` or `confidence` as normative required `FeedbackReport` fields.
- Define `StopDecision` with fields: `should_stop`, `reason_code`, `success`, `message`, and `metadata`.
- Define `RunEvent` with fields: `timestamp`, `run_id`, `iteration`, `event_type`, and `payload`.
- `RunEvent.timestamp` must use ISO 8601 UTC string format, for example `2026-07-08T03:00:00Z`.
- `duration_ms` fields must use non-negative integer milliseconds.
- `exit_code` fields must use integer or null.
- JSONL serialization must be round-trip JSON object serialization; tests should assert parsed structure and key fields, not textual field order.
- `GuardrailDecision`, `ToolObservation`, `FeedbackReport`, and `RunEvent` serialization must not include real API keys, tokens, or complete environment variable values.
- If path, command, stdout/stderr summary, raw excerpt, or payload values look secret-like, serialization must redact or truncate them.
- Define `HarnessConfig` with fields: `workspace`, `provider`, `max_iterations`, `test_command`, `allowed_tools`, `allowed_commands`, `blocked_paths`, `write_limit`, `timeout_seconds`, `run_log_dir`, `approval_mode`, and `demo_mode`.
- Do not use `workspace_root`, `protected_paths`, or `timeout` as normative `HarnessConfig` fields.

**Failing tests first:**
- `test_action_rejects_missing_type`.
- `test_action_contract_uses_type_not_name`.
- `test_guardrail_decision_contract_fields_match_spec`.
- `test_tool_observation_contract_fields_match_spec`.
- `test_guardrail_decision_serializes_without_secret_fields`.
- `test_feedback_report_contract_fields_and_categories_match_spec`.
- `test_feedback_report_has_stable_categories`.
- `test_stop_decision_contract_fields_match_spec`.
- `test_harness_config_defaults_are_safe`.
- `test_harness_config_contract_fields_match_spec`.
- `test_run_event_json_round_trip`.
- `test_run_event_timestamp_is_iso8601_utc`.
- `test_duration_ms_and_exit_code_types_are_stable`.
- `test_jsonl_round_trip_does_not_depend_on_field_order`.
- `test_model_contract_tests_do_not_accept_alternate_constructor_shapes`.

**Confirm red:**
- Run `pytest tests/test_models.py -v`.
- Expected: fails because `models.py` and model types do not exist.

**Minimum green implementation:**
- Add model definitions and validation needed by these tests only.
- Use deterministic serialization suitable for JSONL run logs.
- Tests should fail clearly if model fields deviate from this contract.
- Do not write tests with try/except fallback paths that accept multiple constructor shapes.

**Refactor checkpoint:**
- Check that model names and fields match `SPEC.md` and do not encode behavior that belongs in later modules.

**Verification command:**
- `pytest tests/test_models.py -v`

**Dependencies:** Task 1.

**Parallelizable:** No. Other tasks depend on these interfaces.

**Suggested commit message:** `feat: add core harness data models`

---

## Task 3: Config Loader

**Goal:** Load and validate harness configuration while defaulting to safe mock behavior.

**Files:**
- Create: `src/safe_test_repair_harness/config.py`
- Create: `tests/test_config_loader.py`
- Create: `tests/fixtures/config/minimal.toml`
- Create: `tests/fixtures/config/unsafe.toml`

**Expected implementation points:**
- Load config from TOML or JSON using standard-library support where possible.
- Default provider must be mock.
- Default test command must be `["python", "-m", "pytest"]` or an equivalent argv form.
- Default allowed commands must include only the test command and must not allow arbitrary shell execution.
- Default blocked paths must include `.env`, `.git`, and credential/secret patterns.
- Default `max_iterations` and `timeout_seconds` must be safe finite positive values.
- Default allowed tools must be narrow.
- Reject missing `workspace`, `blocked_paths` conflicts, negative `timeout_seconds`, and unsafe command defaults.
- Normalize paths without allowing workspace escape.

**Failing tests first:**
- `test_loads_minimal_config_with_mock_provider`.
- `test_default_test_command_is_pytest_argv`.
- `test_default_allowed_commands_only_include_test_command`.
- `test_default_blocked_paths_include_env_git_and_secret_patterns`.
- `test_default_limits_are_finite_and_positive`.
- `test_rejects_workspace_escape_in_protected_path`.
- `test_defaults_do_not_enable_real_llm`.
- `test_rejects_negative_timeout_seconds`.

**Confirm red:**
- Run `pytest tests/test_config_loader.py -v`.
- Expected: fails because config loader does not exist.

**Minimum green implementation:**
- Add config loading and validation sufficient for the tests.
- Return `HarnessConfig`.

**Refactor checkpoint:**
- Keep parsing separate from guardrail decisions.
- Confirm no environment variable or credential lookup happens during normal config load.

**Verification command:**
- `pytest tests/test_config_loader.py -v`

**Dependencies:** Task 2.

**Parallelizable:** Yes, after Task 2. Safe in a separate worktree if only config files and config tests are edited.

**Suggested commit message:** `feat: add safe harness config loader`

---

## Task 4: LLM Provider Abstraction and MockLLMProvider

**Goal:** Define a replaceable provider interface and deterministic mock provider for all tests and demos.

**Files:**
- Create: `src/safe_test_repair_harness/llm.py`
- Create: `tests/test_llm_provider.py`

**Expected implementation points:**
- Define provider interface for one decision step.
- Implement `MockLLMProvider` with scripted responses.
- Preserve provider metadata for run logs.
- Return deterministic provider errors when the mock script is exhausted.
- Add an optional real-provider boundary that is not used in tests or CI.

**Failing tests first:**
- `test_mock_provider_returns_scripted_actions_in_order`.
- `test_mock_provider_exhaustion_is_deterministic`.
- `test_provider_metadata_marks_mock`.
- `test_real_provider_without_key_does_not_affect_mock_tests`.

**Confirm red:**
- Run `pytest tests/test_llm_provider.py -v`.
- Expected: fails because provider module does not exist.

**Minimum green implementation:**
- Add provider protocol and mock provider only.
- Real provider may be a boundary that returns a clear missing-key error without network access.

**Refactor checkpoint:**
- Confirm no provider code imports network clients as required dependencies.
- Confirm mock script format can be used by agent-loop tests.

**Verification command:**
- `pytest tests/test_llm_provider.py -v`

**Dependencies:** Task 2.

**Parallelizable:** Yes, after Task 2.

**Suggested commit message:** `feat: add mockable llm provider interface`

---

## Task 5: Action Parser

**Goal:** Parse LLM JSON responses into `Action` objects and reject malformed or unsupported actions deterministically.

**Files:**
- Create: `src/safe_test_repair_harness/action_parser.py`
- Create: `tests/test_action_parser.py`

**Expected implementation points:**
- Accept only structured JSON action responses.
- Reject invalid JSON with a parser observation or parser error.
- Reject missing action type.
- Return structured parse error for invalid JSON, missing action type, and parameter type errors.
- Mark unknown actions as unsupported instead of executing them.
- Treat `apply_patch` as unsupported in MVP.
- Unknown action and MVP-stage `apply_patch` must produce a non-executable `unsupported_action` result, not an executable action.
- Parse errors and `unsupported_action` results must be serializable to the run log and usable as next-iteration context feedback.
- Preserve raw response for debugging in parser result or metadata without trusting it; do not make raw provider text a required `Action` field.

**Failing tests first:**
- `test_parse_valid_read_file_action`.
- `test_invalid_json_returns_parse_error`.
- `test_missing_action_type_returns_parse_error`.
- `test_parameter_type_error_returns_parse_error`.
- `test_unknown_action_returns_unsupported_action`.
- `test_apply_patch_returns_unsupported_action_in_mvp`.
- `test_parse_error_and_unsupported_action_are_loggable_observations`.

**Confirm red:**
- Run `pytest tests/test_action_parser.py -v`.
- Expected: fails because parser module does not exist.

**Minimum green implementation:**
- Add the parser and supported-action list needed for MVP.
- Do not execute any action in this module.

**Refactor checkpoint:**
- Check that parsing, support checks, and tool execution remain separate responsibilities.

**Verification command:**
- `pytest tests/test_action_parser.py -v`

**Dependencies:** Task 2.

**Parallelizable:** Yes, after Task 2.

**Suggested commit message:** `feat: add structured action parser`

---

## Task 6: Guardrail Engine

**Goal:** Enforce code-level safety checks before any file or shell action can run.

**Files:**
- Create: `src/safe_test_repair_harness/guardrails.py`
- Create: `tests/test_guardrails.py`

**Expected implementation points:**
- Block file writes outside workspace.
- Block `blocked_paths` such as `.env`, `.git`, credential files, CI secrets, and configured secret patterns.
- Block dangerous shell commands and shell metacharacter patterns.
- Require approval for configured high-risk actions if the action is otherwise valid.
- `approval_required` may only be returned for explicitly configured high-risk actions or explicit scale thresholds.
- If safety cannot be determined, return `blocked`, not `approval_required`.
- Return `GuardrailDecision` with stable `status` and `reason_code`.

**Failing tests first:**
- `test_blocks_write_outside_workspace`.
- `test_blocks_protected_file_write`.
- `test_blocks_dangerous_shell_command`.
- `test_rejects_shell_chaining_and_redirection`.
- `test_allows_safe_read_inside_workspace`.
- `test_requires_approval_for_configured_action`.
- `test_uncertain_safety_defaults_to_blocked`.
- `test_approval_required_only_for_explicit_config_or_threshold`.

**Confirm red:**
- Run `pytest tests/test_guardrails.py -v`.
- Expected: fails because guardrail engine does not exist.

**Minimum green implementation:**
- Implement deterministic checks for the tested action types.
- Do not rely on prompt text or LLM self-report.

**Refactor checkpoint:**
- Confirm path normalization handles relative paths, parent traversal, and absolute paths.
- Confirm blocked reasons are stable enough for demo traces.

**Verification command:**
- `pytest tests/test_guardrails.py -v`

**Dependencies:** Tasks 2 and 3.

**Parallelizable:** Yes, after Tasks 2 and 3.

**Suggested commit message:** `feat: enforce code-level guardrails`

---

## Task 7: ProcessRunner and FakeProcessRunner

**Goal:** Provide a safe subprocess boundary and a fake runner for deterministic tests.

**Files:**
- Create: `src/safe_test_repair_harness/process_runner.py`
- Create: `tests/test_process_runner.py`

**Expected implementation points:**
- Real runner accepts argv lists, not raw shell strings.
- Real runner uses timeouts.
- Real runner captures stdout, stderr, exit code, and timeout status.
- Fake runner returns scripted process results.
- No tests should need to run dangerous commands.

**Failing tests first:**
- `test_fake_runner_returns_scripted_result`.
- `test_runner_result_records_stdout_stderr_exit_code`.
- `test_real_runner_rejects_shell_string`.
- `test_timeout_is_reported_as_observation`.

**Confirm red:**
- Run `pytest tests/test_process_runner.py -v`.
- Expected: fails because process runner module does not exist.

**Minimum green implementation:**
- Add result structure and fake runner.
- Add real-runner validation without broad shell features.

**Refactor checkpoint:**
- Confirm shell safety belongs in guardrails and execution boundary belongs in ProcessRunner.

**Verification command:**
- `pytest tests/test_process_runner.py -v`

**Dependencies:** Task 2.

**Parallelizable:** Yes, after Task 2.

**Suggested commit message:** `feat: add process runner abstraction`

---

## Task 8: Feedback Analyzer

**Goal:** Convert pytest/process outputs into deterministic feedback categories for the agent loop.

**Files:**
- Create: `src/safe_test_repair_harness/feedback.py`
- Create: `tests/test_feedback_analyzer.py`
- Create: `tests/fixtures/pytest_outputs/assertion_failure.txt`
- Create: `tests/fixtures/pytest_outputs/import_error.txt`
- Create: `tests/fixtures/pytest_outputs/syntax_error.txt`
- Create: `tests/fixtures/pytest_outputs/pass.txt`
- Create: `tests/fixtures/pytest_outputs/timeout.txt`

**Expected implementation points:**
- Classify pass, assertion failure, import error, syntax error, timeout, command error, and unknown failure.
- Produce `FeedbackReport` with fields from Task 2: `status`, `category`, `passed`, `summary`, `failing_tests`, `locations`, `raw_excerpt`, `timed_out`, and `metadata`.
- `category` must be one of the fixed Task 2 categories.
- Do not use `type` or `confidence` as normative `FeedbackReport` fields.
- Extract failing test names when present.
- Produce bounded summaries suitable for LLM context and WebUI trace.
- Do not ask the LLM to classify failures.

**Failing tests first:**
- `test_classifies_pytest_pass`.
- `test_classifies_assertion_failure`.
- `test_classifies_import_error`.
- `test_classifies_syntax_error`.
- `test_classifies_timeout`.
- `test_feedback_report_uses_status_category_and_timed_out_fields`.
- `test_summary_is_bounded`.

**Confirm red:**
- Run `pytest tests/test_feedback_analyzer.py -v`.
- Expected: fails because analyzer module and fixtures do not exist.

**Minimum green implementation:**
- Implement rule-based classification for the fixture outputs.
- Return `FeedbackReport`.

**Refactor checkpoint:**
- Check that categories match `SPEC.md`.
- Keep fixture outputs small and deterministic.

**Verification command:**
- `pytest tests/test_feedback_analyzer.py -v`

**Dependencies:** Tasks 2 and 7.

**Parallelizable:** Yes, after Task 2. It can use a minimal process-result shape agreed with Task 7.

**Suggested commit message:** `feat: add deterministic feedback analyzer`

---

## Task 9: Tool Dispatcher and MVP Tools

**Goal:** Route parsed and approved actions to controlled tool implementations.

**Files:**
- Create: `src/safe_test_repair_harness/tools.py`
- Create: `tests/test_tool_dispatcher.py`
- Create: `tests/fixtures/workspaces/simple_project/`

**Expected implementation points:**
- Implement `read_file`, `write_file`, `list_files`, `run_shell`, `run_tests`, `request_approval`, and `finish` handling.
- Return `unsupported_action` for `apply_patch`.
- Require guardrail approval before execution.
- Use ProcessRunner for `run_shell` and `run_tests`.
- Use Feedback Analyzer for `run_tests`.
- Produce `ToolObservation`.
- Defensively handle `unsupported_action` observations from the parser or prior loop state without executing any file, shell, or test operation.

**Failing tests first:**
- `test_read_file_inside_workspace_returns_content`.
- `test_write_file_inside_workspace_updates_file`.
- `test_write_file_blocked_by_guardrail_is_not_written`.
- `test_run_shell_uses_process_runner`.
- `test_run_tests_returns_feedback_report`.
- `test_apply_patch_returns_unsupported_action`.
- `test_unknown_action_returns_unsupported_action`.
- `test_unsupported_action_never_executes_file_or_shell_operation`.

**2-5 minute TDD substeps:**
- Add the first failing test for `read_file`, confirm red, then implement only safe in-workspace reads.
- Add the failing test for `write_file`, confirm red, then implement only guarded in-workspace writes.
- Add the blocked-write test, confirm red, then ensure blocked guardrail decisions prevent filesystem mutation.
- Add the `run_shell` fake-runner test, confirm red, then route command execution through `ProcessRunner`.
- Add the `run_tests` feedback test, confirm red, then connect `ProcessRunner` output to `FeedbackAnalyzer`.
- Add `apply_patch` and unknown-action tests, confirm red, then return `unsupported_action` without implementing patch application.
- Add the defensive `unsupported_action` dispatcher test, confirm red, then ensure no tool side effect is invoked for unsupported actions.
- Run the full dispatcher test file and refactor duplicated observation-building code only after green.

**Confirm red:**
- Run `pytest tests/test_tool_dispatcher.py -v`.
- Expected: fails because tool dispatcher does not exist.

**Minimum green implementation:**
- Add only the MVP tools listed above.
- Do not implement patch application.
- Do not add arbitrary shell support beyond configured safe commands.

**Refactor checkpoint:**
- Confirm dispatcher does not duplicate parser or guardrail logic.
- Confirm tool observations are safe to store in logs.

**Verification command:**
- `pytest tests/test_tool_dispatcher.py -v`

**Dependencies:** Tasks 5, 6, 7, and 8.

**Parallelizable:** No. This task integrates several earlier modules.

**Suggested commit message:** `feat: add guarded tool dispatcher`

---

## Task 10: Memory and JSONL Run Log

**Goal:** Store run events as JSONL and retrieve bounded context for later agent iterations.

**Files:**
- Create: `src/safe_test_repair_harness/memory.py`
- Create: `tests/test_memory.py`

**Expected implementation points:**
- Append `RunEvent` records to a JSONL file.
- Each JSONL line must be a round-trip JSON object.
- Field order must not have semantic meaning.
- Tests must parse JSON and assert structure/key fields rather than comparing raw line text order.
- Read back recent events.
- Select bounded context for the next LLM call.
- Redact credential-like values before writing.
- Redact or truncate secret-like values found in path, command, stdout/stderr summaries, raw excerpts, and payloads.
- Handle missing or empty log files.

**Failing tests first:**
- `test_appends_run_event_as_jsonl`.
- `test_jsonl_line_is_round_trip_json_object`.
- `test_jsonl_tests_do_not_depend_on_field_order`.
- `test_reads_recent_events_in_order`.
- `test_context_selection_is_bounded`.
- `test_redacts_secret_like_values`.
- `test_redacts_secret_like_values_inside_path_command_and_output`.
- `test_missing_log_returns_empty_history`.

**Confirm red:**
- Run `pytest tests/test_memory.py -v`.
- Expected: fails because memory module does not exist.

**Minimum green implementation:**
- Implement append, read, and simple bounded context selection.
- Do not implement complex semantic memory.

**Refactor checkpoint:**
- Confirm memory is deterministic and does not call an LLM.
- Confirm redaction happens before persistence.

**Verification command:**
- `pytest tests/test_memory.py -v`

**Dependencies:** Task 2.

**Parallelizable:** Yes, after Task 2.

**Suggested commit message:** `feat: add jsonl run log memory`

---

## Task 11: Stop Policy

**Goal:** Decide when the agent loop should stop based on deterministic state and feedback.

**Files:**
- Create: `src/safe_test_repair_harness/stop_policy.py`
- Create: `tests/test_stop_policy.py`

**Expected implementation points:**
- Stop with success when tests pass after an objective feedback signal.
- Stop with max-iteration reason when iteration limit is reached.
- Stop on unrecoverable parser/provider/tool errors.
- Treat LLM `finish` as a candidate, not as proof of success.
- Return `StopDecision` with fields from Task 2: `should_stop`, `reason_code`, `success`, `message`, and `metadata`.

**Failing tests first:**
- `test_stops_success_after_passing_tests`.
- `test_stops_at_max_iterations`.
- `test_finish_without_passing_tests_is_incomplete`.
- `test_stops_on_unrecoverable_provider_error`.
- `test_stop_decision_contract_fields_match_spec`.

**Confirm red:**
- Run `pytest tests/test_stop_policy.py -v`.
- Expected: fails because stop policy module does not exist.

**Minimum green implementation:**
- Implement deterministic stop rules needed by tests.

**Refactor checkpoint:**
- Confirm stop policy does not inspect natural language prompt text.
- Confirm reasons are stable for CLI/WebUI output.

**Verification command:**
- `pytest tests/test_stop_policy.py -v`

**Dependencies:** Tasks 2 and 8.

**Parallelizable:** Yes, after Tasks 2 and 8.

**Suggested commit message:** `feat: add deterministic stop policy`

---

## Task 12: Agent Loop

**Goal:** Implement the project-owned main loop that coordinates provider, parser, guardrail, tools, feedback, memory, and stop policy.

**Files:**
- Create: `src/safe_test_repair_harness/agent_loop.py`
- Create: `tests/test_agent_loop.py`

**Expected implementation points:**
- Build iteration context from task input, config, and bounded memory.
- Call the injected LLM provider.
- Parse the provider response into an action.
- Dispatch approved actions through the tool layer.
- Record each step in JSONL memory.
- Feed deterministic feedback into the next iteration.
- Stop according to `StopPolicy`.
- Use the Task 2 model contract consistently: `Action.type`, `ToolObservation.feedback`, `FeedbackReport.category`, `StopDecision.success`, and `RunEvent.payload`.
- Never call a real LLM in unit tests.

**Failing tests first:**
- `test_agent_loop_runs_mock_repair_loop_to_success`.
- `test_agent_loop_records_each_iteration`.
- `test_agent_loop_returns_guardrail_blocked_trace`.
- `test_agent_loop_handles_invalid_llm_json`.
- `test_agent_loop_stops_at_max_iterations`.
- `test_feedback_changes_next_mock_action`.
- `test_agent_loop_uses_task2_model_contract_fields`.

**2-5 minute TDD substeps:**
- Add the invalid-LLM-JSON test first, confirm red, then connect provider output to `ActionParser` and produce a parser observation.
- Add the memory-recording test, confirm red, then append provider/action/tool/stop events to JSONL memory.
- Add the guardrail-blocked trace test, confirm red, then ensure blocked actions are logged and not dispatched.
- Add the max-iterations test, confirm red, then wire `StopPolicy` into the loop.
- Add the mock repair-loop success test, confirm red, then run the minimal provider-parser-tool-feedback-stop cycle.
- Add the feedback-changes-next-action test, confirm red, then include bounded `FeedbackReport` context in the next provider call.
- Run the full agent-loop test file and only then refactor context assembly into small helpers if needed.

**Confirm red:**
- Run `pytest tests/test_agent_loop.py -v`.
- Expected: fails because agent loop module does not exist.

**Minimum green implementation:**
- Implement the smallest loop that passes scripted mock provider tests.
- Use fake process runner and fixture workspace for deterministic repair-loop tests.

**Refactor checkpoint:**
- Confirm the loop has no dependency on existing agent frameworks.
- Confirm context construction is deterministic and bounded.
- Confirm all side effects go through tools and memory.

**Verification command:**
- `pytest tests/test_agent_loop.py -v`

**Dependencies:** Tasks 4, 5, 9, 10, and 11.

**Parallelizable:** No. This is the central integration task.

**Suggested commit message:** `feat: implement mock-driven agent loop`

---

## Task 13: Credential Manager With Fake Keyring Tests

**Goal:** Provide safe credential storage boundaries without requiring real credentials in tests.

**Files:**
- Create: `src/safe_test_repair_harness/credentials.py`
- Create: `tests/test_credentials.py`

**Expected implementation points:**
- Define a secret-store interface.
- Implement fake keyring/store for tests.
- Support set, get-status, clear, and missing-key behavior.
- Never return plaintext key in status output.
- Ensure logs and events receive redacted values.
- Ensure serialized `GuardrailDecision`, `ToolObservation`, `FeedbackReport`, and `RunEvent` payloads never contain real API keys, tokens, or complete environment variable values.
- Ensure secret-like values embedded in paths, commands, stdout/stderr summaries, raw excerpts, or payload fields are redacted or truncated before persistence.
- Do not require a real system keyring for unit tests.

**Failing tests first:**
- `test_fake_store_sets_and_retrieves_for_provider_call_only`.
- `test_status_does_not_reveal_secret`.
- `test_missing_key_returns_clear_error`.
- `test_clear_removes_key`.
- `test_secret_is_not_written_to_run_event_payload`.
- `test_secret_like_values_are_redacted_from_observation_and_feedback_payloads`.

**Confirm red:**
- Run `pytest tests/test_credentials.py -v`.
- Expected: fails because credential manager does not exist.

**Minimum green implementation:**
- Implement fake store and manager behavior.
- Real keyring integration may remain optional and outside CI.

**Refactor checkpoint:**
- Confirm no test reads or writes actual user keyring state.
- Confirm no output string contains full secret values.

**Verification command:**
- `pytest tests/test_credentials.py -v`

**Dependencies:** Tasks 1, 2, and 10.

**Parallelizable:** Yes, after Tasks 2 and 10.

**Suggested commit message:** `feat: add safe credential manager boundary`

---

## Task 14: CLI and Deterministic Mechanism Demos

**Goal:** Expose CLI commands for mock demos required by the course: guardrail, repair-loop, and feedback-classifier.

**Files:**
- Modify: `src/safe_test_repair_harness/cli.py`
- Create: `src/safe_test_repair_harness/demo.py`
- Create: `tests/test_cli_demos.py`

**Expected implementation points:**
- Add CLI command for guardrail demo.
- Add CLI command for repair-loop demo.
- Add CLI command for feedback-classifier demo.
- `guardrail demo` demonstrates the dangerous-action interception mechanism.
- `repair-loop demo` demonstrates failure injection followed by feedback changing the next action.
- `feedback-classifier demo` and `repair-loop demo` together correspond to the main contribution: deterministic feedback loop.
- Each demo must use mock/stub components only.
- Demo output should include trace fields useful for grading.
- No demo should require a real LLM key or network access.

**Failing tests first:**
- `test_cli_guardrail_demo_reports_blocked_action`.
- `test_cli_repair_loop_demo_reports_success_after_feedback`.
- `test_cli_feedback_classifier_demo_reports_categories`.
- `test_cli_demos_do_not_require_real_key`.

**2-5 minute TDD substeps:**
- Add the guardrail demo CLI test, confirm red, then expose only the built-in dangerous-action scenario.
- Add the feedback-classifier demo test, confirm red, then route fixture output through `FeedbackAnalyzer`.
- Add the repair-loop demo test, confirm red, then call the real mock-driven `AgentLoop` demo script.
- Add the no-real-key test, confirm red, then ensure demo config always uses `MockLLMProvider` and fake/stub dependencies.
- Run the full CLI demo test file and refactor demo trace formatting only after green.

**Confirm red:**
- Run `pytest tests/test_cli_demos.py -v`.
- Expected: fails because demo commands do not exist.

**Minimum green implementation:**
- Wire CLI commands to deterministic demo functions.
- Use built-in fixtures and mock provider scripts.

**Refactor checkpoint:**
- Confirm demo logic reuses real harness modules rather than duplicating fake behavior.
- Confirm output is stable enough for README examples and WebUI.

**Verification command:**
- `pytest tests/test_cli_demos.py -v`

**Dependencies:** Tasks 6, 8, 12, and 13.

**Parallelizable:** No. This task depends on integrated behavior.

**Suggested commit message:** `feat: add deterministic harness demos`

---

## Task 15: WebUI Built-In Mock Demo

**Goal:** Provide a minimal WebUI that displays built-in mock demo traces without accepting arbitrary uploaded code or arbitrary execution.

**Files:**
- Create: `src/safe_test_repair_harness/webui.py`
- Create: `tests/test_webui.py`

**Expected implementation points:**
- Provide health endpoint.
- Provide endpoint or page for built-in guardrail, repair-loop, and feedback-classifier traces.
- Use Python standard-library HTTP server behavior unless a later approved SPEC revision explicitly allows a WebUI dependency.
- Do not expose file upload.
- Do not accept arbitrary workspace paths from users.
- Do not call real LLM providers.
- Return trace data that matches CLI demos.

**Failing tests first:**
- `test_webui_health_does_not_require_real_llm`.
- `test_webui_mock_demo_returns_trace`.
- `test_webui_rejects_or_omits_file_upload_route`.
- `test_webui_does_not_accept_arbitrary_workspace_execution`.

**2-5 minute TDD substeps:**
- Add the health endpoint test, confirm red, then implement a minimal no-secret health response.
- Add the mock demo trace test, confirm red, then expose only built-in demo trace data from `demo.py`.
- Add the no-upload-route test, confirm red, then ensure the HTTP handler has no upload endpoint.
- Add the arbitrary-workspace rejection test, confirm red, then reject or ignore user-supplied workspace/path parameters.
- Run the full WebUI test file and refactor response serialization only after green.

**Confirm red:**
- Run `pytest tests/test_webui.py -v`.
- Expected: fails because WebUI module does not exist.

**Minimum green implementation:**
- Implement only the built-in mock demo surface.
- Keep UI minimal and focused on mechanism trace.

**Refactor checkpoint:**
- Confirm WebUI has no route that executes user-provided shell commands or uploaded code.
- Confirm WebUI smoke test can run in CI without secrets.

**Verification command:**
- `pytest tests/test_webui.py -v`

**Dependencies:** Task 14.

**Parallelizable:** No, unless Task 14's demo interfaces are already stable.

**Suggested commit message:** `feat: add mock-only webui demo`

---

## Task 16: Docker Distribution

**Goal:** Add Docker packaging that can run the mock CLI/WebUI demo without credentials.

**Files:**
- Create: `Dockerfile`
- Create: `tests/test_docker_metadata.py`
- Modify: `README.md` if already created, otherwise defer README text to Task 19.

**Expected implementation points:**
- Docker image installs the package.
- Default command should be safe and mock-based.
- Image must not contain API keys.
- Document expected runtime mode for real providers as explicit user configuration only.

**Failing tests first:**
- `test_dockerfile_exists`.
- `test_dockerfile_does_not_copy_env_secrets`.
- `test_dockerfile_has_mock_safe_default_command_or_documented_entrypoint`.

**Confirm red:**
- Run `pytest tests/test_docker_metadata.py -v`.
- Expected: fails because Dockerfile does not exist.

**Minimum green implementation:**
- Add a Dockerfile that can build the package and run a safe mock command.
- Do not add deployment-specific secrets.

**Refactor checkpoint:**
- Confirm Docker behavior matches GitHub Actions build job expectations.
- Confirm `.env` is not copied into image.

**Verification command:**
- `pytest tests/test_docker_metadata.py -v`
- `docker build -t safe-test-repair-harness:local .`

**Dependencies:** Task 14.

**Parallelizable:** Yes, after Task 14 if it only touches Docker and Docker metadata tests.

**Suggested commit message:** `build: add docker distribution`

---

## Task 17: CI Configuration for GitHub Actions and GitLab CI Deliverable

**Goal:** Add required CI paths: GitHub Actions for push tests and Docker build, plus `.gitlab-ci.yml` with `unit-test`.

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.gitlab-ci.yml`
- Create: `tests/test_ci_config.py`

**Expected implementation points:**
- GitHub Actions runs on push.
- GitHub Actions has a test job using mock/stub tests.
- GitHub Actions builds Docker image.
- GitHub Actions does not inject real LLM keys.
- `.gitlab-ci.yml` contains a job named exactly `unit-test`.
- `.gitlab-ci.yml` runs mock/stub unit tests only.
- Neither CI path calls real LLM providers.

**Failing tests first:**
- `test_github_actions_workflow_exists`.
- `test_github_actions_runs_on_push`.
- `test_github_actions_has_test_job`.
- `test_github_actions_has_docker_build_job`.
- `test_gitlab_ci_exists`.
- `test_gitlab_ci_contains_unit_test_job`.
- `test_ci_configs_do_not_reference_real_api_keys`.

**Confirm red:**
- Run `pytest tests/test_ci_config.py -v`.
- Expected: fails because CI files do not exist.

**Minimum green implementation:**
- Add CI config files with minimal valid jobs.
- Use commands already validated locally by earlier tasks.

**Refactor checkpoint:**
- Confirm CI command names match README and `pyproject.toml`.
- Confirm Docker build is in GitHub Actions, not only `.gitlab-ci.yml`.

**Verification command:**
- `pytest tests/test_ci_config.py -v`
- Local equivalent of CI unit tests: `pytest -v`
- Local Docker check: `docker build -t safe-test-repair-harness:ci-check .`

**Dependencies:** Tasks 1, 14, and 16.

**Parallelizable:** Yes, after Task 16 if CI tests are isolated to config files.

**Suggested commit message:** `ci: add github actions and gitlab unit-test job`

---

## Task 18: WebUI Deployment Smoke and Public URL

**Goal:** Deploy the mock-only WebUI, provide a public URL, and verify that the deployed service exposes only safe built-in demo behavior.

**Files:**
- Create or modify: `render.yaml` or equivalent deployment configuration if the selected platform supports repository configuration.
- Modify: `README.md`
- Create: `tests/test_deployment_contract.py`

**Expected implementation points:**
- Deploy only the built-in mock demo WebUI.
- Provide a public URL for the WebUI.
- Verify the deployed health endpoint.
- Verify the deployed mock demo trace endpoint.
- Do not allow arbitrary code upload.
- Do not allow arbitrary workspace execution.
- Do not require a real LLM key.
- Do not inject real provider secrets into the deployment path.
- README must record the deployment architecture, safety limits, and public URL after deployment succeeds.

**Failing tests first:**
- `test_deployment_config_exists_or_readme_documents_manual_deploy`.
- `test_deployment_contract_documents_public_url_placeholder_before_deploy`.
- `test_deployment_contract_states_mock_only_no_real_key`.
- `test_deployment_contract_disallows_upload_and_arbitrary_workspace`.

**2-5 minute TDD substeps:**
- Add deployment-contract metadata tests, confirm red, then add deployment config or README deployment section.
- Add mock-only/no-real-key deployment test, confirm red, then document and configure mock-only startup.
- Add no-upload/no-arbitrary-workspace deployment contract test, confirm red, then ensure README/deployment config does not expose unsafe routes.
- After deployment, manually verify the public health endpoint and mock trace endpoint, then update README with the URL and verification date.

**Confirm red:**
- Run `pytest tests/test_deployment_contract.py -v`.
- Expected: fails because deployment contract documentation/configuration does not exist.

**Minimum green implementation:**
- Add deployment metadata/configuration and documentation sufficient for local contract tests.
- Keep deployed behavior limited to built-in mock demos.

**Refactor checkpoint:**
- Confirm deployment documentation does not mention real API keys as required for the mock WebUI.
- Confirm README clearly says the WebUI is not an online IDE and cannot execute arbitrary uploaded projects.

**Verification command:**
- `pytest tests/test_deployment_contract.py -v`
- Local smoke test for the WebUI health endpoint.
- Post-deployment browser or HTTP check for the public health endpoint and mock demo trace endpoint.

**Dependencies:** Tasks 15, 16, and 17.

**Parallelizable:** No. Deployment verification depends on WebUI and CI/distribution behavior being stable.

**Suggested commit message:** `deploy: add mock webui public smoke evidence`

---

## Task 19: README, Acceptance Sweep, and AGENT_LOG Finalization

**Goal:** Finish user-facing documentation and verify that the project matches `SPEC.md`, `PLAN.md`, and course deliverables.

**Files:**
- Create or modify: `README.md`
- Modify: `AGENT_LOG.md`
- Create: `tests/test_readme_contract.py`

**Expected implementation points:**
- README explains installation, CLI mock demos, WebUI mock demo, Docker build/run, GitHub Actions, `.gitlab-ci.yml`, credential setup, credential safety, no-key mock mode, WebUI public URL, safety boundaries, known limitations, and post-MVP `apply_patch`.
- README states real LLM provider is optional and not required for CI/tests.
- README states WebUI does not accept arbitrary code upload or arbitrary execution.
- `AGENT_LOG.md` contains entries for completed tasks and verification evidence.
- Acceptance sweep maps final deliverables to files.

**Failing tests first:**
- `test_readme_mentions_mock_demo_without_key`.
- `test_readme_documents_docker_usage`.
- `test_readme_documents_github_actions_and_gitlab_ci`.
- `test_readme_documents_credential_safety`.
- `test_readme_states_apply_patch_is_post_mvp`.
- `test_agent_log_has_task_entries`.

**Confirm red:**
- Run `pytest tests/test_readme_contract.py -v`.
- Expected: fails because README and/or log content is incomplete.

**Minimum green implementation:**
- Add documentation that accurately reflects implemented commands and behavior.
- Update `AGENT_LOG.md` with process entries from implementation.

**Refactor checkpoint:**
- Check README commands against actual CLI, Docker, and CI commands.
- Remove claims about deployed URLs or CI pass status unless they have actually happened.

**Verification command:**
- `pytest tests/test_readme_contract.py -v`
- `pytest -v`

**Dependencies:** All implementation tasks that define commands or behavior.

**Parallelizable:** No. This is a final consistency task.

**Suggested commit message:** `docs: document harness usage and acceptance evidence`

---

## Task 20: Student-Written REFLECTION.md and Final Process Review

**Goal:** Prepare final process evidence and support the student in writing the required reflection without AI ghostwriting the reflection body.

**Files:**
- Create: `REFLECTION.md`
- Modify: `SPEC_PROCESS.md`
- Modify: `AGENT_LOG.md`
- Modify: `PLAN.md`

**Expected implementation points:**
- `REFLECTION.md` must be written by the student.
- AI must not draft the reflection body.
- AI may provide a checklist, structure review, gap analysis, or polishing suggestions, and any such assistance must be acknowledged according to course requirements.
- Target length is 1500-2500 Chinese characters unless the course staff provides a different requirement.
- Reflection content should be based on `SPEC_PROCESS.md`, `PLAN.md`, `AGENT_LOG.md`, PR/review records, TDD results, CI/deployment results, and cold-start validation results.
- This task writes no implementation code.
- Final process review should check that all required deliverables exist: `SPEC.md`, `PLAN.md`, `SPEC_PROCESS.md`, `AGENT_LOG.md`, `REFLECTION.md`, README, source, tests, Dockerfile, GitHub Actions workflow, `.gitlab-ci.yml`, CI evidence, public WebUI URL, and distribution instructions.

**Failing tests first:**
- `test_reflection_file_exists_after_student_writes_it`.
- `test_reflection_length_is_in_required_range`.
- `test_reflection_references_process_evidence`.
- `test_final_deliverable_checklist_is_complete`.

**Confirm red:**
- Run the final documentation/process checks selected in Task 19.
- Expected before completion: fails or reports missing evidence until the student writes `REFLECTION.md` and final deliverables are present.

**Minimum green implementation:**
- Student writes `REFLECTION.md`.
- AI or reviewer checks structure, length, evidence references, and missing deliverables without writing the reflection body.
- Update `PLAN.md` status tracker and `AGENT_LOG.md` with final review evidence.

**Refactor checkpoint:**
- Confirm the reflection is in the student's own voice.
- Confirm no future or unperformed work is described as completed.
- Confirm cold-start validation results are recorded only if the validation actually happened.

**Verification command:**
- Final documentation/process check from Task 19.
- Manual checklist review against `General_Requirements.md` and `AI4SE_Final_Project_A_Coding_Agent_Harness.md`.

**Dependencies:** Tasks 1-19 and completed cold-start validation.

**Parallelizable:** No. This is the final process task.

**Suggested commit message:** `docs: add student reflection and final process review`

---

## Cold-Start Validation Instructions

After `SPEC.md` and this `PLAN.md` are stable, run cold-start validation with a different agent type in a fresh session.

Give the validation agent only:

- `SPEC.md`
- `PLAN.md`

Do not provide prior chat history, private explanations, or extra oral context.

Ask the validation agent to:

1. Select one or two tasks from `PLAN.md`, preferably one foundational or core mechanism task with limited dependencies.
2. Explain what it believes the task requires.
3. Start with the failing tests described in the selected task.
4. Stop and ask if it finds ambiguity instead of guessing.
5. Report any mismatch between `SPEC.md` and `PLAN.md`.

Recommended cold-start task choices:

- Task 2: Core Data Models, because it tests whether SPEC field names and shared interfaces are clear.
- Task 5: Action Parser, because it tests whether structured LLM action handling and `apply_patch` post-MVP behavior are clear.
- Task 6: Guardrail Engine, because it tests whether "mechanism must be code, not prompt" is clear.

Do not ask the cold-start agent to implement Task 12, because Agent Loop depends on many prior interfaces. If Task 12 needs validation, ask the cold-start agent only to read it and report whether dependencies, interfaces, and stop/feedback flow are clear enough to implement later.

Record the result in `SPEC_PROCESS.md` after the validation happens:

- where the different agent paused or asked questions;
- which parts of SPEC or PLAN were ambiguous;
- whether the agent implemented behavior different from the intended design;
- what SPEC or PLAN revisions were made afterward.

Do not record cold-start validation as completed until it has actually happened.

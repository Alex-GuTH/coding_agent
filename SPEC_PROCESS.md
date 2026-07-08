# SPEC_PROCESS.md

## 1. Document Scope

This document records the design process for the project through brainstorming, SPEC/PLAN generation, compliance revisions, and cold-start validation.

Current status:

- Brainstorming is complete.
- The project direction has been selected as **Safe Test-Repair Coding Harness**.
- `SPEC.md` has been generated and revised.
- `PLAN.md` has been generated and revised.
- Cold-start validation with GitHub Copilot has been performed as a cold-start review/validation pass.
- The validation exposed data-format and error-semantics ambiguities, and targeted revisions were applied to `SPEC.md` and `PLAN.md`.
- No implementation code has been written as part of this process record.

This file intentionally does not describe implementation results, test results, or validation outcomes that have not occurred.

## 2. Brainstorming Stage

### 2.1 Initial Goal

At the beginning, the goal was to complete the AI4SE final project mainly with AI assistance while still satisfying the required course workflow. The user did not want an ad-hoc coding project; the project needed to follow the required process:

- use the Superpowers workflow;
- write SPEC before PLAN;
- use TDD during implementation;
- support deterministic unit tests with a mock or stub LLM;
- include a mechanism demonstration;
- keep process records;
- provide distribution artifacts;
- configure CI.

The user selected project category A: **Coding Agent Harness**.

### 2.2 Understanding of Category A Requirements

The AI interpreted category A as requiring a project that implements a coding-agent harness rather than merely building an application that calls an LLM. The central requirement is that the project must contain code-level mechanisms for controlling an agent:

- an agent loop;
- an LLM abstraction layer;
- tools that the agent can call;
- deterministic feedback signals;
- safety guardrails;
- memory or run history;
- configuration;
- tests that can run with a mock LLM;
- a demo that shows the harness mechanism.

The design therefore focused on the harness itself: how the agent observes a task, asks an LLM for a structured action, validates that action, executes allowed tools, collects deterministic feedback, and decides whether to continue or stop.

### 2.3 Project Directions Considered

During brainstorming, the AI proposed several single-person project directions suitable for a course project:

1. **Safe Test-Repair Harness**
   - A coding agent harness that repeatedly runs tests, asks an LLM for controlled edits, applies safe file changes, and uses test feedback to continue or stop.
   - Main mechanism: deterministic test-repair feedback loop.

2. **Guarded Shell-and-File Coding Harness**
   - A harness focused on safe tool execution, file access control, command allowlists, and approval boundaries.
   - Main mechanism: code-level guardrails for dangerous actions.

3. **Memory-Guided Coding Harness**
   - A harness that records prior attempts, failures, files read, edits made, and feedback, then retrieves relevant memory in later iterations.
   - Main mechanism: structured memory and retrieval for coding tasks.

The user asked whether direction 1, direction 2, or a fusion of both would be better. The final chosen direction was a fusion of the first two.

### 2.4 Selected Direction

The selected project direction is **Safe Test-Repair Coding Harness**.

This direction combines:

- the feedback-driven test-repair loop from direction 1;
- the safety and tool-control focus from direction 2.

The resulting project is narrow enough for one person to implement, but still clearly satisfies category A because it contains a real agent harness rather than only a prompt or demo script.

### 2.5 Why Feedback Loop Became the Main Contribution

Feedback loop was chosen as the main contribution because it is the clearest mechanism that distinguishes a coding-agent harness from a normal LLM wrapper.

The key idea is:

1. The harness runs deterministic tools such as tests.
2. It parses structured feedback such as pass/fail status, failing test names, error summaries, and timeout status.
3. It stores that feedback in memory.
4. It passes the relevant feedback into the next LLM request.
5. It stops according to code-defined stop policies.

This contribution is testable without a real LLM because a mock LLM can emit predetermined actions, and the harness can verify that feedback changes the next step.

### 2.6 Why Guardrail Became the Second Focus

Guardrail was selected as the second focus because coding agents can easily perform risky actions if file writes and shell commands are not constrained by code.

The design treats guardrails as code mechanisms, not prompt instructions. The harness must reject or require approval for unsafe actions before execution. Examples include:

- writing outside the workspace;
- modifying protected files;
- running non-allowlisted shell commands;
- using shell features such as pipes, redirection, command chaining, or `shell=True`;
- requesting actions that are outside the MVP action set.

This was kept as the second focus because it strengthens the harness while avoiding a project that becomes too broad. The primary contribution remains the feedback loop.

## 3. SPEC Generation Stage

### 3.1 Purpose of the First SPEC

The first version of `SPEC.md` translated the brainstorming decision into a concrete project specification. It defined the project as a coding-agent harness for safe test repair, with a CLI, a mock-demo WebUI, deterministic tests, CI, and container distribution.

The SPEC established:

- project goals and non-goals;
- expected users and use cases;
- the agent loop;
- the LLM provider abstraction;
- supported tools;
- deterministic feedback collection;
- guardrail behavior;
- memory storage and retrieval;
- configuration;
- credential handling;
- testing strategy;
- distribution strategy;
- mechanism demo expectations.

### 3.2 Coverage of General Requirements Section 4.2

The SPEC was written to cover the required SPEC structure from `General_Requirements.md` section 4.2. It included:

- project overview;
- goals and non-goals;
- user stories;
- system architecture;
- functional requirements;
- non-functional requirements;
- external dependencies;
- data model or persistence design;
- interface design;
- testing strategy;
- distribution strategy;
- acceptance criteria.

The SPEC also included process-sensitive requirements such as CI, WebUI, README, credential safety, and final deliverables.

### 3.3 Coverage of Category A Domain and Mechanism Design

Because the project is category A, the SPEC added a dedicated **Domain and Mechanism Design** section.

This section described the harness domain and the core mechanisms:

- the agent owns the loop instead of delegating control to an existing agent framework;
- the LLM provider is replaceable;
- mock LLM is a first-class testing path;
- actions are structured and parsed by code;
- tools are dispatched by a tool layer;
- feedback is produced by deterministic code;
- guardrails are enforced before tool execution;
- memory is stored as structured run records;
- configuration restricts tool behavior.

This section was added specifically because category A requires the project to demonstrate a harness mechanism, not only a user-facing app.

### 3.4 Clarifying That Mechanisms Must Be Code, Not Prompt

A later review checked whether the SPEC made it clear that mechanisms must be implemented in code rather than described only in prompts.

The SPEC was strengthened to state that:

- the agent loop is implemented by the project;
- action parsing and validation are code-level mechanisms;
- guardrails reject unsafe actions before execution;
- feedback is computed from test and command outputs by deterministic code;
- stop policy is implemented in code;
- configuration is enforced by the harness;
- prompts may provide context, but prompts are not the safety boundary or control mechanism.

The SPEC also introduced a mechanism implementation matrix to connect each core mechanism to a concrete module responsibility and a mock/stub test strategy.

### 3.5 Clarifying Mock LLM Deterministic Testing

The SPEC explicitly made mock LLM support part of the LLM abstraction layer.

The mock LLM is expected to return scripted structured actions. This allows tests to verify harness behavior without using a network call, real model, or API key.

The SPEC requires deterministic tests for:

- agent loop continuation and stopping;
- action parsing;
- unsupported actions;
- guardrail rejection;
- test feedback extraction;
- memory logging;
- configuration enforcement;
- credential manager behavior without a real keyring;
- WebUI mock demo behavior.

This keeps tests and CI independent of real LLM providers.

## 4. SPEC Compliance Revision Stage

### 4.1 First Compliance Review

After the first SPEC draft, a compliance review was requested against:

- `General_Requirements.md`;
- `AI4SE_Final_Project_A_Coding_Agent_Harness.md`;
- the current `SPEC.md`.

The review focused on whether the SPEC satisfied course requirements and whether any sections were inconsistent, too broad, vague, or risky.

The main issues identified were:

- CI/CD wording was inconsistent and did not clearly satisfy both GitHub Actions and `.gitlab-ci.yml` requirements.
- The WebUI needed to be limited to a mock demo and must not allow arbitrary uploaded code execution.
- MVP, required features, optional extensions, and post-MVP items needed clearer separation.
- `apply_patch` could be misread as part of the MVP.
- Real LLM provider support needed to be clearly optional.
- Credential Manager needed to avoid leaking keys and avoid depending on a real keyring in unit tests.
- The SPEC needed stronger language that feedback signals and dangerous-action handling are code mechanisms, not prompt conventions.

### 4.2 CI/CD Requirement Reconciliation

The CI/CD requirements needed special attention because the course documents mention two related but different deliverables:

- GitHub Actions must be configured so tests run automatically on each push. If the project uses container distribution, CI must also build the image.
- The final deliverable list requires a `.gitlab-ci.yml` file containing a job named `unit-test`.

The SPEC was revised to treat both as required:

- **GitHub Actions** is the main workflow expected to run in the GitHub repository. It must run on every push, run mock/stub tests, avoid real LLM calls and real API keys, and build the Docker image or run a mock demo smoke test. The final observed GitHub Actions run should be passing.
- **`.gitlab-ci.yml`** is a required compatibility deliverable from the course checklist. It must exist and contain a job named `unit-test`. That job must also use mock/stub tests only and must not require a real LLM or real API key.

This revision avoids treating `.gitlab-ci.yml` as a replacement for GitHub Actions, and also avoids treating GitHub Actions as a replacement for the required `.gitlab-ci.yml` file.

### 4.3 WebUI Scope Correction

The SPEC clarified that the WebUI is for mechanism demonstration only.

The WebUI should show a built-in mock scenario, such as:

- task input;
- scripted mock LLM action;
- tool execution result;
- guardrail decision;
- test feedback;
- memory trace;
- final stop reason.

The WebUI must not allow arbitrary code upload or unrestricted execution. This keeps the WebUI aligned with the course requirement while avoiding a broad and unsafe hosted coding environment.

### 4.4 `apply_patch` Scope Correction

`apply_patch` was moved to post-MVP scope.

The SPEC now states that MVP does not require implementing `apply_patch`. If an LLM returns an `apply_patch` action during MVP, the harness may return `unsupported_action`.

This prevents `PLAN.md` from later treating `apply_patch` as a core acceptance task. The MVP can still support controlled file changes through safer structured file-write behavior.

### 4.5 Wording Correction: Patch vs Controlled File Modification

The project overview originally used wording similar to "write patch", which could be confused with the post-MVP `apply_patch` action.

The wording was changed to "write controlled file modifications" to make the MVP scope clearer.

This distinction matters because the MVP should demonstrate safe, controlled file modification without requiring a full patch parser or patch-application subsystem.

## 5. Key Iterations

### 5.1 Iteration 1: Project Direction

**Problem before iteration:**  
The initial project category was known, but the concrete project direction was not yet selected.

**Dialogue Excerpt:**  

> User: "你推荐什么？是1、2，还是把1、2两个方向融合？"  
> AI: Recommended combining direction 1 and direction 2 because the test-repair loop gives the project a clear main mechanism, while guardrails make the harness safer and more aligned with category A.  
> User: "那选择1和2融合。我们继续"

**AI suggestion:**  
The AI proposed multiple Coding Agent Harness directions, including a test-repair loop, a guardrail-focused harness, and a memory-guided harness. It explained each direction's problem, mechanism, possible contribution, implementation risk, and mock LLM testability.

**User decision:**  
The user chose to combine direction 1 and direction 2.

**SPEC change:**  
The SPEC defined the project as **Safe Test-Repair Coding Harness**, with feedback loop as the main contribution and guardrail as the second focus.

### 5.2 Iteration 2: Mock LLM vs Real LLM

**Problem before iteration:**  
The user asked about the difference between mock LLM and real LLM, and whether the requirements explicitly required one.

**Dialogue Excerpt:**  

> User: "mock LLM 和真实 LLM有什么区别？现在的要求文档中有无明确要求？"  
> AI: Explained that mock LLM is for deterministic tests and CI, while real LLM is optional for manual use. The course requirement is better satisfied by making mock/stub LLM a required path.  
> User: "那就选B"

**AI suggestion:**  
The AI clarified that mock LLM is used for deterministic testing and CI, while real LLM is optional for manual demonstration. It recommended making mock/stub LLM the primary required path.

**User decision:**  
The user selected the mock-first direction.

**SPEC change:**  
The SPEC made the LLM provider replaceable, required mock LLM support, and stated that tests, CI, and mechanism demo must not depend on a real LLM or real API key.

### 5.3 Iteration 3: CI/CD Interpretation

**Problem before iteration:**  
The user was unsure whether GitHub Actions should be used. Later, the requirements were clarified: GitHub Actions is required for push-triggered tests, while `.gitlab-ci.yml` is also required as a final deliverable with a `unit-test` job.

**Dialogue Excerpt:**  

> User: "我在课上听到Github Action这个词，我不确定是不是用在这里的，是不是可以弄成这样的形式？"  
> AI: Suggested using GitHub Actions if it matches the course requirement, while keeping the design testable without real LLM calls.  
> User: "老师说明最后会查看 GitHub 仓库里的 workflow 是否成功跑通。"  
> User: "请你严格按照两个要求文档的要求来"  
> AI: Revised the CI interpretation: GitHub Actions is the main GitHub workflow that must pass, and `.gitlab-ci.yml` remains a required deliverable with a `unit-test` job.

**AI suggestion:**  
The AI first proposed GitHub Actions as a CI option, then revised the SPEC to include both systems after the requirement conflict was identified.

**User decision:**  
The user asked to strictly follow the documents: GitHub Actions for push-based CI, and `.gitlab-ci.yml` as a required deliverable.

**SPEC change:**  
The SPEC now states that GitHub Actions is the main workflow checked in the GitHub repository and must pass. It also states that `.gitlab-ci.yml` must exist and contain a `unit-test` job. Both CI paths must use mock/stub tests and must not use real LLM calls or real API keys.

### 5.4 Iteration 4: `apply_patch` and MVP Scope

**Problem before iteration:**  
The SPEC mentioned patch-like behavior, which risked making `apply_patch` appear to be part of the MVP.

**Dialogue Excerpt:**  

> User: "请把 `apply_patch` 明确为 post-MVP"  
> User: "MVP 不要求实现 `apply_patch`；MVP 中如果收到 apply_patch action，可以返回 `unsupported_action`"  
> User: "请把项目概述里的'写入补丁'改成'写入受控文件修改'"  
> AI: Accepted this as a scope-control correction and proposed targeted SPEC wording instead of redesigning the project.

**AI suggestion:**  
The AI recommended moving `apply_patch` to post-MVP and allowing MVP to return `unsupported_action` for that action.

**User decision:**  
The user accepted the correction and asked for targeted SPEC revisions only.

**SPEC change:**  
The SPEC now states that `apply_patch` is post-MVP. The project overview wording was changed from "write patch" to "write controlled file modifications."

### 5.5 Iteration 5: Mechanisms as Code

**Problem before iteration:**  
The user asked whether the SPEC clearly stated that mechanisms must be code, not prompt.

**Dialogue Excerpt:**  

> User: "请检查这个 SPEC 有没有把'机制必须是代码，而不是 prompt'写清楚？"  
> User: "请检查每个核心机制是否都可以用 mock LLM 测试？"  
> AI: Identified places where the SPEC needed stronger wording around code-level mechanisms and mock-testable boundaries.    
> User: "如果你确定你的修补符合要求文档，那么请你修改"

**AI suggestion:**  
The AI reviewed the SPEC and recommended stronger wording around code-level enforcement, deterministic feedback, mock-testable mechanisms, and guardrail boundaries.

**User decision:**  
The user allowed the SPEC to be patched if the changes matched the course documents.

**SPEC change:**  
The SPEC added clearer statements and a mechanism mapping showing that the agent loop, feedback analyzer, guardrail engine, stop policy, action parser, tool dispatcher, memory, and configuration enforcement are implemented and tested as code mechanisms.

## 6. Current Open Process Items

The following items are not completed yet and should be handled in later process stages:

- TODO: Optionally run a stricter Task 2 red-run cold-start trial if additional validation evidence is needed.
- TODO: Start implementation only after the revised `SPEC.md`, `PLAN.md`, and cold-start record are confirmed stable.
- TODO: During implementation, use TDD and record test-first steps.
- TODO: Implement the harness according to `SPEC.md` and `PLAN.md`.
- TODO: Run mock/stub LLM unit tests.
- TODO: Add GitHub Actions workflow and `.gitlab-ci.yml`.
- TODO: Build and verify Docker distribution.
- TODO: Deploy the mock WebUI and record the public URL.
- TODO: Maintain `AGENT_LOG.md` and the `PLAN.md` task status tracker during implementation.
- TODO: Complete the student-written `REFLECTION.md`.
- TODO: Perform final delivery review against both requirements files.

## 7. Cold-start Validation With a Different Agent

### 7.1 Validation Setup

Cold-start validation was performed after `SPEC.md` and `PLAN.md` had reached a stable planning state.

- Main development agent: Codex.
- Cold-start validation agent: GitHub Copilot.
- Materials provided to the cold-start agent: only `SPEC.md` and `PLAN.md`.
- Materials not provided: prior chat history, hidden context, informal explanations, or extra oral instructions.
- Selected validation targets:
  - Task 2: Core Data Models.
  - Task 5: Action Parser.

The validation agent was asked to reason from the written documents rather than from shared conversation history.

Boundary of this validation:

- This GitHub Copilot cold-start was primarily a review/validation pass.
- It validated whether Task 2 and Task 5 were understandable from `SPEC.md` and `PLAN.md`.
- It exposed document ambiguities around data formats and error semantics.
- It did not formally complete a Task 2 red-green implementation trial.
- If a stricter Task 2 red-run trial is performed later, the result should be appended to this section.

### 7.2 What the Cold-start Agent Understood

The cold-start agent understood the main project direction and did not report a Critical blocker for Task 2 or Task 5.

It correctly identified:

- the project goal: Safe Test-Repair Coding Harness;
- the architecture: a self-implemented coding-agent harness rather than a wrapper around an existing agent runner;
- the mock-first testing strategy;
- the requirement that real LLM providers must not be required for tests or CI;
- the CI and distribution constraints;
- the category A requirement that harness mechanisms must be implemented as code;
- the purpose of Task 2 as shared data model stabilization;
- the purpose of Task 5 as structured action parsing and unsupported-action handling.

### 7.3 Findings From Cold-start Validation

The validation did not require changing the project direction or main contribution, but it exposed several places where `SPEC.md` and `PLAN.md` needed more precise data and error semantics:

1. `RunEvent.timestamp` format needed to be fixed.
2. `HarnessConfig` default allowed commands needed to be more explicit.
3. unknown action and MVP-stage `apply_patch` semantics needed to be clearer at both parser and dispatcher layers.
4. parser error and `unsupported_action` return shapes needed to be distinguished.
5. JSONL round-trip tests should not depend on field order.
6. `approval_required` trigger conditions needed to be more explicit.
7. secret redaction needed to be consistent across `GuardrailDecision`, `ToolObservation`, `FeedbackReport`, and `RunEvent`.

### 7.4 Handling Decision

The feedback was accepted because it clarified deterministic interfaces and reduced the chance that a future subagent would infer incompatible formats.

The handling decision was:

- adopt the feedback;
- apply targeted revisions to `SPEC.md` and `PLAN.md`;
- preserve the project direction;
- preserve the main contribution as deterministic feedback loop;
- keep guardrail as the second focus;
- keep `apply_patch` as post-MVP;
- avoid starting implementation code until the revised SPEC, PLAN, and cold-start record are stable.

### 7.5 Revision Result Summary

The targeted revisions fixed the following semantics:

- `RunEvent.timestamp` is fixed as an ISO 8601 UTC string, for example `2026-07-08T03:00:00Z`.
- JSONL logs require each line to be a round-trip JSON object.
- JSONL tests should assert parsed structure and key fields, not raw text field order.
- Default provider is `mock`.
- Default test command is `["python", "-m", "pytest"]` or an equivalent argv form.
- Default allowed commands include only the test command and do not allow arbitrary shell execution.
- unknown action and MVP-stage `apply_patch` return a non-executable `unsupported_action`.
- Tool Dispatcher must defensively handle `unsupported_action` and must not execute file, shell, or test operations for it.
- parser errors and `unsupported_action` results must be loggable and usable as next-iteration context feedback.
- `approval_required` is triggered only by explicitly configured high-risk actions or explicit scale thresholds.
- actions that cannot be safely classified default to `blocked`.
- secret-like content must be redacted or truncated before serialization or persistence.

### 7.6 Remaining Notes

No implementation code was started during this validation update.

Further implementation should proceed only after the student confirms that the revised `SPEC.md`, `PLAN.md`, and this cold-start record are stable.

### 7.7 Stricter Task 2 Red-run Trial

After the first GitHub Copilot cold-start review/validation pass, a stricter Task 2 red-run trial was performed.

Trial constraints:

- Main development agent remained Codex.
- Cold-start validation agent was GitHub Copilot.
- The cold-start agent received only `SPEC.md` and `PLAN.md`.
- No prior chat history, hidden context, or extra oral explanation was provided.
- The trial scope was limited to Task 2: Core Data Models.
- Production implementation code was not allowed.
- Task 3 and later tasks were not allowed to start.
- Real LLM calls were not allowed.
- Existing agent runners were not allowed.

Actual process:

- GitHub Copilot inspected the workspace and found that the source scaffold did not exist yet.
- It also found that `src/safe_test_repair_harness/models.py` did not exist.
- It created a `tests/test_models.py` test draft.
- The test draft covered the main Task 2 test points:
  - `test_action_rejects_missing_type`;
  - `test_guardrail_decision_serializes_without_secret_fields`;
  - `test_feedback_report_has_stable_categories`;
  - `test_harness_config_defaults_are_safe`;
  - `test_run_event_json_round_trip`;
  - `test_run_event_timestamp_is_iso8601_utc`;
  - `test_duration_ms_and_exit_code_types_are_stable`;
  - `test_jsonl_round_trip_does_not_depend_on_field_order`.
- It attempted to run:
  - `pytest tests/test_models.py -v`;
  - `python -m pytest tests/test_models.py -v`.
- The current environment did not have pytest installed, so a complete pytest red stack was not produced.
- The expected red result should have been that the model module or model types did not exist.
- No production code was implemented during this trial.

Findings exposed by the red-run trial:

- `GuardrailDecision` fields were still inconsistent between `SPEC.md` and `PLAN.md`.
- `FeedbackReport` fields were still inconsistent between `SPEC.md` and `PLAN.md`.
- `HarnessConfig` fields were still inconsistent between `SPEC.md` and `PLAN.md`.
- The relationship between external JSON `Action.type` and the internal action discriminator could still be misunderstood.
- The test draft used try/except fallback paths to support multiple constructor shapes, which showed that the model contract was not strict enough.

Handling decision:

- The red-run findings were accepted as document clarity issues.
- Targeted revisions were applied to `SPEC.md` and `PLAN.md`.
- Core model field contracts were unified.
- The project direction was not changed.
- The main contribution remained deterministic feedback loop.
- Formal implementation code was still not started.

Revision result summary:

- `Action` is standardized as:
  - `type`;
  - `path`;
  - `content`;
  - `patch`;
  - `command`;
  - `reason`;
  - `metadata`.
- `Action.type` is both the external JSON action discriminator and the internal model action discriminator.
- `GuardrailDecision` is standardized as:
  - `status`;
  - `reason_code`;
  - `message`;
  - `action_type`;
  - `path`;
  - `command`;
  - `requires_human`;
  - `metadata`.
- `ToolObservation` is standardized as:
  - `tool`;
  - `status`;
  - `summary`;
  - `data`;
  - `error_code`;
  - `feedback`;
  - `metadata`.
- `FeedbackReport` is standardized as:
  - `status`;
  - `category`;
  - `passed`;
  - `summary`;
  - `failing_tests`;
  - `locations`;
  - `raw_excerpt`;
  - `timed_out`;
  - `metadata`.
- `StopDecision` is standardized as:
  - `should_stop`;
  - `reason_code`;
  - `success`;
  - `message`;
  - `metadata`.
- `RunEvent` is standardized as:
  - `timestamp`;
  - `run_id`;
  - `iteration`;
  - `event_type`;
  - `payload`.
- `HarnessConfig` is standardized as:
  - `workspace`;
  - `provider`;
  - `max_iterations`;
  - `test_command`;
  - `allowed_tools`;
  - `allowed_commands`;
  - `blocked_paths`;
  - `write_limit`;
  - `timeout_seconds`;
  - `run_log_dir`;
  - `approval_mode`;
  - `demo_mode`.
- `PLAN.md` Task 2 now requires tests to fail clearly if model fields deviate from the contract.
- `PLAN.md` Task 2 now explicitly says not to write tests with try/except fallback paths that accept multiple constructor shapes.

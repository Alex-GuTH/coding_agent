# Safe Test-Repair Coding Harness

Safe Test-Repair Coding Harness is a classroom-safe coding-agent harness for deterministic test-repair demos. It owns the harness loop, mockable provider boundary, action parsing, code-level guardrails, controlled tools, pytest feedback analysis, JSONL run memory, deterministic stop policy, CLI demos, mock WebUI demo, Docker packaging, and CI configuration.

The implemented course contribution is a deterministic feedback loop: pytest/process output is classified by code, written into structured feedback, and used by the mock-driven loop to choose the next action. A secondary contribution is code-level guardrail enforcement before file or shell operations.

## Setup

Requirements:

- Python 3.11 or newer
- `pip`
- Docker, only for container build/run checks

Install locally:

```powershell
python -m pip install -e . pytest
```

Run the full test suite with one command:

```powershell
pytest -v
```

## No-Key Mock Mode

No-key mock mode is the default path for tests, CI, Docker, CLI demos, and the WebUI demo. Mock/stub tests and demos do not require real LLM keys. They do not call real LLM providers and do not need provider credentials.

## CLI Mock Demos

Run deterministic mechanism demos:

```powershell
safe-repair demo guardrail
safe-repair demo feedback-classifier
safe-repair demo repair-loop
```

- `safe-repair demo guardrail` shows guardrails block dangerous actions.
- `safe-repair demo feedback-classifier` shows rule-based feedback categories.
- `safe-repair demo repair-loop` shows failure feedback changing the next mock action and ending in success.

## WebUI Mock Demo

The WebUI exposes built-in mock demo traces only. Public WebUI URL:

`https://safe-test-repair-harness-mock-webui.onrender.com`

The WebUI is not an online IDE. The WebUI does not accept arbitrary code upload. The WebUI does not execute arbitrary workspace paths or arbitrary project paths.

## Task 18 Deployment Smoke

The WebUI deployment is mock-only and runs the existing built-in demo WebUI from `safe_test_repair_harness.webui`. It does not require real LLM keys, does not call real LLM providers, and does not need provider configuration for the deployment smoke path.

Manual deployment can use `render.yaml`, which starts the built-in WebUI with:

```powershell
python -c "import os; from safe_test_repair_harness.webui import make_server; make_server('0.0.0.0', int(os.environ.get('PORT', '8000'))).serve_forever()"
```

Public URL: `https://safe-test-repair-harness-mock-webui.onrender.com`

Deployment verification date: `2026-07-11`

Remote smoke checks:

- `GET /health` => `200`; response included `{"demo_mode": true, "provider": "mock", "status": "ok"}`.
- `GET /demos/repair-loop` => `200`; response included the built-in mock repair-loop demo trace.
- `GET /upload` => `404`.
- `GET /demos/repair-loop?workspace=C:\Windows` => `400`.

Safety boundaries:

- The WebUI is not an online IDE.
- The WebUI does not accept arbitrary code upload.
- The WebUI does not execute arbitrary workspace paths.
- The WebUI does not execute arbitrary project paths.
- The WebUI exposes only built-in mock demo traces.
- Guardrails block dangerous actions before controlled tools run.

## Docker

Pull and run the public mock-demo image:

```powershell
docker pull ghcr.io/alex-guth/coding_agent:latest
docker run --rm ghcr.io/alex-guth/coding_agent:latest
```

Build and run the container locally:

```powershell
docker build -t safe-test-repair-harness:local .
docker run --rm safe-test-repair-harness:local
```

The Dockerfile installs the package from `pyproject.toml` and `src/`. The safe mock default command is `safe-repair demo guardrail`.

GitHub Actions publishes the public registry image to `ghcr.io/alex-guth/coding_agent:latest` from the mock-only Dockerfile. Public registry evidence recorded on `2026-07-12`: the GHCR `latest` manifest returned `200 OK` with digest `sha256:87fec731548672e54279e63dd6f91a2e19e059503580e242a7bcf1bdd4192819`.

## CI

GitHub Actions is configured at `.github/workflows/ci.yml`. It runs on push, installs the package plus pytest, runs `pytest -v`, and includes a Docker build job.

GitLab CI is configured at `.gitlab-ci.yml`. It contains a job named exactly `unit-test` that installs the package plus pytest and runs `pytest -v`.

These CI paths use mock/stub tests only and do not require real LLM keys.

Latest recorded GitHub Actions execution for CI/CD and GHCR publishing evidence: commit `76fb6ed` completed successfully in workflow run `29190758993`: `https://github.com/Alex-GuTH/coding_agent/actions/runs/29190758993`. The `test`, `docker-build`, and `docker-publish` jobs all completed successfully.

## Credential Safety

Credential safety is isolated in `src/safe_test_repair_harness/credentials.py`.

- Tests use `FakeCredentialStore`; they do not require system keyring state.
- Missing credentials return the stable `missing_credential` status.
- Status and logging paths do not expose plaintext keys.
- `redact_for_logging` recursively redacts sensitive-like values from observation and feedback-like payloads.
- The submitted mock/demo distribution does not call paid or authenticated provider APIs. Real-provider key setup is post-MVP for this submission; any future real-provider extension should use `CredentialManager` or OS keyring / encrypted credential storage and must not print plaintext keys.

## Safety Boundaries and Limitations

- Mock/stub tests and demos do not require real LLM keys.
- WebUI does not accept arbitrary code upload.
- WebUI does not execute arbitrary workspace paths or arbitrary project paths.
- Guardrails block dangerous actions before file or shell execution.
- Shell/test execution goes through controlled tools and the process runner boundary.
- MVP `apply_patch` is post-MVP and returns `unsupported_action`.
- The public WebUI is a mock-demo trace viewer, not a production IDE or production security boundary.
- Real provider support is optional boundary code and is not required for tests, CI, Docker, CLI demos, or WebUI demo.

## Acceptance Evidence Map

| Deliverable | Evidence |
| --- | --- |
| Specification | `SPEC.md` |
| Implementation plan | `PLAN.md` |
| Process evidence | `SPEC_PROCESS.md`, `AGENT_LOG.md` |
| User documentation | `README.md` |
| Student reflection | `REFLECTION.md` |
| Harness source | `src/safe_test_repair_harness/` |
| Agent loop | `src/safe_test_repair_harness/agent_loop.py` |
| WebUI mock demo | `src/safe_test_repair_harness/webui.py`, `render.yaml` |
| Tests | `tests/` |
| Docker distribution | `Dockerfile`, `tests/test_docker_metadata.py` |
| GitHub Actions | `.github/workflows/ci.yml`, `tests/test_ci_config.py` |
| GitLab CI | `.gitlab-ci.yml`, `tests/test_ci_config.py` |
| Deployment contract | `tests/test_deployment_contract.py` |

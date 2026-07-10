# Safe Test-Repair Coding Harness

## Task 18 Deployment Smoke

This Task 18 section is intentionally minimal. Full acceptance documentation is deferred to Task 19.

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

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler

from safe_test_repair_harness.webui import BuiltinDemoHandler, handle_builtin_request


def decode(response) -> dict[str, object]:
    return json.loads(response.body.decode("utf-8"))


def test_webui_health_does_not_require_real_llm(monkeypatch) -> None:
    fake_key = "sk-real-looking-but-test-only"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)

    response = handle_builtin_request("GET", "/health")
    payload = decode(response)

    assert response.status == 200
    assert payload["status"] == "ok"
    assert payload["provider"] == "mock"
    assert payload["demo_mode"] is True
    assert fake_key not in response.body.decode("utf-8")
    assert issubclass(BuiltinDemoHandler, BaseHTTPRequestHandler)


def test_webui_mock_demo_returns_trace() -> None:
    for demo_name in ["guardrail", "feedback-classifier", "repair-loop"]:
        response = handle_builtin_request("GET", f"/demos/{demo_name}")
        payload = decode(response)

        assert response.status == 200
        assert payload["demo"] == demo_name
        assert payload["trace"]
        assert payload["llm_provider"] in {"none", "mock"}

    unknown_response = handle_builtin_request("GET", "/demos/not-real")
    unknown_payload = decode(unknown_response)

    assert unknown_response.status == 404
    assert unknown_payload["error"] == "unknown_demo"


def test_webui_rejects_or_omits_file_upload_route() -> None:
    post_response = handle_builtin_request("POST", "/upload")
    post_payload = decode(post_response)
    get_response = handle_builtin_request("GET", "/upload")
    get_payload = decode(get_response)

    assert post_response.status == 404
    assert post_payload["error"] == "not_found"
    assert get_response.status == 404
    assert get_payload["error"] == "not_found"


def test_webui_does_not_accept_arbitrary_workspace_execution() -> None:
    response = handle_builtin_request(
        "GET",
        "/demos/repair-loop?workspace=C:/Users/AlexGu&path=.env&command=pytest",
    )
    payload = decode(response)
    serialized = json.dumps(payload, sort_keys=True)

    assert response.status == 400
    assert payload["error"] == "user_supplied_execution_context_rejected"
    assert "C:/Users/AlexGu" not in serialized
    assert ".env" not in serialized
    assert "pytest" not in serialized

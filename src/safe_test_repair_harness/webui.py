from __future__ import annotations

import json
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from safe_test_repair_harness.demo import feedback_classifier_demo, guardrail_demo, repair_loop_demo


@dataclass(frozen=True)
class WebResponse:
    status: int
    body: bytes
    content_type: str = "application/json"


class BuiltinDemoHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self._send(handle_builtin_request("GET", self.path))

    def do_POST(self) -> None:
        self._send(handle_builtin_request("POST", self.path))

    def _send(self, response: WebResponse) -> None:
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        self.end_headers()
        self.wfile.write(response.body)

    def log_message(self, format: str, *args: object) -> None:
        return


def make_server(host: str = "127.0.0.1", port: int = 8000) -> HTTPServer:
    return HTTPServer((host, port), BuiltinDemoHandler)


def handle_builtin_request(method: str, path: str) -> WebResponse:
    parsed = urlparse(path)

    if parsed.path == "/upload":
        return _json_response(404, {"error": "not_found"})

    if method.upper() != "GET":
        return _json_response(405, {"error": "method_not_allowed"})

    if parsed.path == "/health":
        return _json_response(
            200,
            {
                "status": "ok",
                "provider": "mock",
                "demo_mode": True,
            },
        )

    if parsed.path.startswith("/demos/"):
        if parse_qs(parsed.query):
            return _json_response(400, {"error": "user_supplied_execution_context_rejected"})

        demo_name = parsed.path.removeprefix("/demos/")
        demo_func = {
            "guardrail": guardrail_demo,
            "feedback-classifier": feedback_classifier_demo,
            "repair-loop": repair_loop_demo,
        }.get(demo_name)
        if demo_func is None:
            return _json_response(404, {"error": "unknown_demo"})
        return _json_response(200, demo_func())

    return _json_response(404, {"error": "not_found"})


def _json_response(status: int, payload: dict[str, object]) -> WebResponse:
    return WebResponse(
        status=status,
        body=json.dumps(payload, sort_keys=True).encode("utf-8"),
    )

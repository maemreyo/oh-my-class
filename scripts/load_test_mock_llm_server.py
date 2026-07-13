"""Mock-provider LLM server for the QA-02 smoke profile — clearly labeled
test double, not a silent success-faker.

Speaks the same minimal OpenAI-compatible surface the real 9Router sidecar
does (packages/agents/llm/smoke.py probes exactly these two endpoints, and
packages/llm_client/config.py's LLM_BASE_URL is the only thing that needs
to change to point the real gateway at it): GET /v1/models and POST
/v1/chat/completions. Point LLM_BASE_URL at this server's address to run the
gateway+worker fleet's real HTTP/DB/queue mechanics without spending real
LLM budget or waiting on real inference latency.

Known, stated limitation (see docs/ note in load_test.py's --help and the
QA-02 issue comment): this returns one generic canned JSON body for every
task. The teaching-pack pipeline is a multi-stage LangGraph with per-task
JSON contracts (triage, blueprint_design, content_generation, quality_gate,
...); this stub does not attempt to satisfy all of them, so a full pack
generally will NOT reach `completed` through this stub alone. It is honest
about that ceiling by design: it exists to load-test the submission/queueing/
DB/metrics path realistically, not to fake full pipeline success. Building
faithful per-task fixtures for every stage is future work, not attempted here.
"""
from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_MODEL_ID = "4omc"

# ponytail: one generic response body for every task; per-task fixtures are the
# upgrade path if a future session wants to prove full-pack completion via mock.
_GENERIC_CONTENT = json.dumps({"result": "mock response", "sections": [], "items": []})


class _MockLLMHandler(BaseHTTPRequestHandler):
    # Silence default request logging (one line per HTTP call would drown a load test's stdout).
    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
        pass

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler name
        if self.path.startswith("/v1/models"):
            self._respond_json(200, {"data": [{"id": DEFAULT_MODEL_ID, "object": "model"}]})
            return
        self._respond_json(404, {"error": f"unknown path {self.path}"})

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler name
        if not self.path.startswith("/v1/chat/completions"):
            self._respond_json(404, {"error": f"unknown path {self.path}"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw_body or b"{}")
        except json.JSONDecodeError:
            body = {}
        model = body.get("model", DEFAULT_MODEL_ID) if isinstance(body, dict) else DEFAULT_MODEL_ID
        # Simulate a touch of real inference latency so latency percentiles
        # aren't literally zero — small and fixed, not meant to model a real
        # model's variance.
        time.sleep(self.server.artificial_latency_seconds)  # type: ignore[attr-defined]
        response = {
            "id": "mock-chatcmpl",
            "object": "chat.completion",
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": _GENERIC_CONTENT},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 32, "completion_tokens": 16, "total_tokens": 48},
        }
        self._respond_json(200, response)

    def _respond_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class MockLlmServer(ThreadingHTTPServer):
    def __init__(self, *args, artificial_latency_seconds: float = 0.05, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.artificial_latency_seconds = artificial_latency_seconds


@contextmanager
def run_mock_llm_server(
    *, host: str = "127.0.0.1", port: int = 0, artificial_latency_seconds: float = 0.05,
) -> Iterator[str]:
    """Context manager: starts the mock server on a background thread, yields
    its base_url (e.g. http://127.0.0.1:54321/v1), tears it down on exit."""
    server = MockLlmServer(
        (host, port), _MockLLMHandler, artificial_latency_seconds=artificial_latency_seconds,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        actual_port = server.server_address[1]
        yield f"http://{host}:{actual_port}/v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5.0)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=20228)
    args = parser.parse_args()

    with run_mock_llm_server(host=args.host, port=args.port) as base_url:
        print(f"mock LLM server listening at {base_url} (Ctrl+C to stop)")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()

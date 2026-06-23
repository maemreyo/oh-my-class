"""Tests for the POST /webhook/error endpoint on routers.webhooks."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root (parent of `services/`) is on sys.path so that
# `from services.gateway...` works under plain pytest invocation.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from services.gateway.routers.webhooks import router as webhooks_router  # noqa: E402


def _make_client() -> TestClient:
    """Build a minimal FastAPI app with the webhooks router mounted at /webhook."""
    app = FastAPI()
    app.include_router(webhooks_router, prefix="/webhook")
    return TestClient(app)


class TestFrontendErrorEndpoint:
    """Tests for the ``POST /webhook/error`` endpoint."""

    def test_frontend_error_endpoint_accepts_valid_report(self) -> None:
        """Given a valid FrontendErrorReport, when POSTing, then 200 + {'status': 'received'}."""
        client = _make_client()
        payload = {
            "message": "Cannot read properties of undefined (reading 'map')",
            "component_stack": "at LessonList (LessonList.tsx:42)",
            "error_message": "TypeError",
            "request_id": "req-frontend-001",
            "url": "http://localhost:3000/run/abc",
            "user_agent": "Mozilla/5.0",
            "timestamp": "2026-06-23T10:00:00Z",
            "extra": {"component": "LessonList"},
        }

        response = client.post("/webhook/error", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "received"}

    def test_frontend_error_endpoint_rejects_empty_message(self) -> None:
        """Given message='', when POSTing, then 422 (Pydantic validation error)."""
        client = _make_client()
        payload = {"message": ""}

        response = client.post("/webhook/error", json=payload)

        assert response.status_code == 422

    def test_frontend_error_endpoint_handles_missing_optional_fields(self) -> None:
        """Given only the required 'message' field, when POSTing, then 200."""
        client = _make_client()
        payload = {"message": "Something broke"}

        response = client.post("/webhook/error", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "received"}

    def test_frontend_error_endpoint_returns_dict(self) -> None:
        """Given a valid report, when POSTing, then response is a dict with 'status'."""
        client = _make_client()
        payload = {"message": "boom"}

        response = client.post("/webhook/error", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, dict)
        assert "status" in body

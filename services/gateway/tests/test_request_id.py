"""Tests for RequestIDMiddleware."""

import sys
import uuid
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from starlette.testclient import TestClient

# Required: pytest's path setup omits workspace member paths that uv run injects.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from services.gateway.middleware.request_id import (  # noqa: E402
    RequestIDMiddleware,
    _is_valid_request_id,
    generate_request_id,
)


@pytest.fixture  # type: ignore[misc]
def client() -> TestClient:
    """Return a TestClient wired with only RequestIDMiddleware + a probe route."""
    app = FastAPI()

    @app.get("/probe")  # pyright: ignore[reportUntypedFunctionDecorator]
    async def probe(request: Request):
        # Echo the request_id back so the test can assert state was populated.
        return {"request_id": getattr(request.state, "request_id", None)}

    app.add_middleware(RequestIDMiddleware)
    return TestClient(app)


class TestRequestIDMiddleware:
    """Tests for RequestIDMiddleware.dispatch()."""

    def test_request_id_middleware_generates_when_missing(self, client: TestClient) -> None:
        """No X-Request-ID on the request → response carries a generated UUID4."""
        response = client.get("/probe")

        assert response.status_code == 200
        header = response.headers.get("X-Request-ID")
        assert header is not None
        # Must parse as a valid UUID (uuid4 hex string).
        uuid.UUID(header)

    def test_request_id_middleware_propagates_existing(self, client: TestClient) -> None:
        """Valid X-Request-ID on the request → response echoes the same value."""
        incoming = "abc-123-xyz-deadbeef"

        response = client.get("/probe", headers={"X-Request-ID": incoming})

        assert response.status_code == 200
        assert response.headers.get("X-Request-ID") == incoming

    def test_request_id_middleware_rejects_invalid_format(self, client: TestClient) -> None:
        """Malformed X-Request-ID → middleware discards it and generates a fresh one."""
        invalid = "invalid$$$"

        response = client.get("/probe", headers={"X-Request-ID": invalid})

        assert response.status_code == 200
        header = response.headers.get("X-Request-ID")
        assert header is not None
        assert header != invalid
        # New id must still be a valid UUID.
        uuid.UUID(header)

    def test_generate_request_id_returns_uuid(self) -> None:
        """generate_request_id returns a string parseable as uuid4."""
        rid = generate_request_id()
        parsed = uuid.UUID(rid)
        assert str(parsed) == rid
        assert parsed.version == 4

    def test_request_id_stored_in_state(self, client: TestClient) -> None:
        """Middleware sets request.state.request_id and it matches the response header."""
        incoming = "cafebabe-1234-5678-9abc-def012345678"

        response = client.get("/probe", headers={"X-Request-ID": incoming})

        assert response.status_code == 200
        assert response.json() == {"request_id": incoming}
        assert response.headers.get("X-Request-ID") == incoming


class TestIsValidRequestId:
    """Tests for the _is_valid_request_id helper."""

    @pytest.mark.parametrize(  # type: ignore[misc]
        "value",
        [
            "abc-123-xyz-deadbeef",
            "550e8400-e29b-41d4-a716-446655440000",
            "12345678",
            "DEADBEEF-CAFE-BABE-0000-111122223333",
        ],
    )
    def test_accepts_uuid_shaped(self, value: str) -> None:
        """Hex/dash strings of length 8-64 are accepted."""
        assert _is_valid_request_id(value) is True

    @pytest.mark.parametrize(  # type: ignore[misc]
        "value",
        [
            "invalid$$$",
            "short",            # length < 8
            "x" * 65,           # length > 64
            "contains spaces!",
            "",
        ],
    )
    def test_rejects_invalid(self, value: str) -> None:
        """Non-hex chars, out-of-range length, and empty strings are rejected."""
        assert _is_valid_request_id(value) is False
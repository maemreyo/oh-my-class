"""Tests for the centralized exception handler middleware."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from services.gateway.exceptions import (  # noqa: E402
    AuthenticationError,
    ErrorCode,
    NotFoundError,
    OMCError,
    PipelineError,
    ValidationError,
    format_error_response,
)
from services.gateway.middleware.error_handler import (  # noqa: E402
    _CODE_TO_STATUS,
    _STATUS_TO_CODE,
    register_exception_handlers,
)


def _make_request(headers: dict[str, str] | None = None) -> Request:
    """Build a minimal Starlette Request with an optional request-id on state."""
    raw = [(k.lower().encode("latin-1"), v.encode("latin-1"))
           for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/probe",
        "headers": raw,
        "query_string": b"",
    }
    req = Request(scope)
    return req


@pytest.fixture  # type: ignore[misc]
def client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise/validation")  # pyright: ignore[reportUntypedFunctionDecorator]
    def _v() -> None:
        raise ValidationError("Field 'topic' is required")

    @app.get("/raise/notfound")  # pyright: ignore[reportUntypedFunctionDecorator]
    def _n() -> None:
        raise NotFoundError("Run run-xyz does not exist")

    @app.get("/raise/auth")  # pyright: ignore[reportUntypedFunctionDecorator]
    def _a() -> None:
        raise AuthenticationError("Invalid credentials")

    @app.get("/raise/pipeline")  # pyright: ignore[reportUntypedFunctionDecorator]
    def _p() -> None:
        raise PipelineError("Step 3 failed", run_id="run-1", step=3)

    @app.get("/raise/omc")  # pyright: ignore[reportUntypedFunctionDecorator]
    def _o() -> None:
        raise OMCError(error_code=ErrorCode.PIPELINE_ERROR, message="Boom")

    @app.get("/raise/http403")  # pyright: ignore[reportUntypedFunctionDecorator]
    def _h() -> None:
        raise HTTPException(status_code=403, detail="Forbidden")

    @app.get("/raise/http404")  # pyright: ignore[reportUntypedFunctionDecorator]
    def _h2() -> None:
        raise HTTPException(status_code=404, detail="Not here")

    @app.get("/clean")  # pyright: ignore[reportUntypedFunctionDecorator]
    def _c() -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app)


class TestOMCExceptionHandler:
    """Given an OMCError subclass, the handler must format it correctly."""

    def test_validation_error_returns_422(self, client: TestClient) -> None:
        r = client.get("/raise/validation")
        assert r.status_code == 422
        body = r.json()
        assert body["error_code"] == "VALIDATION_ERROR"
        assert body["message"] == "Field 'topic' is required"
        assert "request_id" in body

    def test_notfound_returns_404(self, client: TestClient) -> None:
        r = client.get("/raise/notfound")
        assert r.status_code == 404
        assert r.json()["error_code"] == "NOT_FOUND"

    def test_auth_returns_401(self, client: TestClient) -> None:
        r = client.get("/raise/auth")
        assert r.status_code == 401
        assert r.json()["error_code"] == "AUTHENTICATION_ERROR"

    def test_pipeline_error_returns_500(self, client: TestClient) -> None:
        r = client.get("/raise/pipeline")
        assert r.status_code == 500
        body = r.json()
        assert body["error_code"] == "PIPELINE_ERROR"
        assert body["run_id"] == "run-1"
        assert body["step"] == 3

    def test_omc_error_includes_request_id_header(self, client: TestClient) -> None:
        my_id = "req-test-123"
        r = client.get("/raise/omc", headers={"X-Request-ID": my_id})
        assert r.headers.get("X-Request-ID") == my_id
        assert r.json()["request_id"] == my_id


class TestHTTPExceptionHandler:
    """Given a FastAPI HTTPException, the handler must wrap it."""

    def test_http_403_maps_to_authorization_error(self, client: TestClient) -> None:
        r = client.get("/raise/http403")
        assert r.status_code == 403
        assert r.json()["error_code"] == "AUTHORIZATION_ERROR"

    def test_http_404_maps_to_not_found(self, client: TestClient) -> None:
        r = client.get("/raise/http404")
        assert r.status_code == 404
        assert r.json()["error_code"] == "NOT_FOUND"


class TestCodeStatusMappings:
    """The mapping tables must be complete and consistent."""

    def test_all_codes_have_status(self) -> None:
        for code in ErrorCode:
            assert code in _CODE_TO_STATUS, f"{code} missing from status map"

    def test_common_statuses_have_code(self) -> None:
        for status in (400, 401, 403, 404, 422, 429, 500):
            assert status in _STATUS_TO_CODE, f"{status} missing from code map"


class TestRegisterHandlers:
    """register_exception_handlers must be safe to call and not break the app."""

    def test_register_does_not_crash(self) -> None:
        app = FastAPI()
        register_exception_handlers(app)
        assert app.exception_handlers  # type: ignore[attr-defined]

    def test_register_is_idempotent(self) -> None:
        app = FastAPI()
        register_exception_handlers(app)
        register_exception_handlers(app)
        assert app.exception_handlers  # type: ignore[attr-defined]


class TestCleanRequest:
    """A non-erroring endpoint must still produce a normal response."""

    def test_clean_returns_200(self, client: TestClient) -> None:
        r = client.get("/clean")
        assert r.status_code == 200
        assert r.json() == {"ok": True}


class TestFormatHelper:
    """The format_error_response helper must round-trip through the schema."""

    def test_format_returns_all_fields(self) -> None:
        exc = ValidationError("Bad input", details=[{"field": "x"}])
        body = format_error_response(exc)
        assert body["error_code"] == "VALIDATION_ERROR"
        assert body["message"] == "Bad input"
        assert "details" in body

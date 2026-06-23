"""Centralized exception handlers — convert OMCError + HTTPException to ErrorResponse.

Maps domain exceptions and FastAPI's HTTPException into a structured
``ErrorResponse`` envelope, logging each failure with full context and
echoing the X-Request-ID header so callers can correlate logs.

Any OMCError subclass (ValidationError, PipelineError, AgentError,
QualityGateError, ExportError, AuthenticationError, AuthorizationError,
NotFoundError, RateLimitedError) inherits the registered handler automatically.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..exceptions import (
    ErrorCode,
    OMCError,
    format_error_response,
)
from ..logging_config import bind_context, get_logger

# ErrorCode -> HTTP status mapping
_CODE_TO_STATUS: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.AUTHENTICATION_ERROR: 401,
    ErrorCode.AUTHORIZATION_ERROR: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.PIPELINE_ERROR: 500,
    ErrorCode.AGENT_ERROR: 500,
    ErrorCode.QUALITY_GATE_ERROR: 422,
    ErrorCode.EXPORT_ERROR: 500,
    ErrorCode.INTERNAL_ERROR: 500,
}

# HTTP status -> ErrorCode mapping (for FastAPI/Starlette HTTPException wrapping)
_STATUS_TO_CODE: dict[int, ErrorCode] = {
    400: ErrorCode.VALIDATION_ERROR,
    401: ErrorCode.AUTHENTICATION_ERROR,
    403: ErrorCode.AUTHORIZATION_ERROR,
    404: ErrorCode.NOT_FOUND,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.RATE_LIMITED,
    500: ErrorCode.PIPELINE_ERROR,
    502: ErrorCode.PIPELINE_ERROR,
    503: ErrorCode.PIPELINE_ERROR,
}

_REQUEST_ID_HEADER = "X-Request-ID"


def _resolve_request_id(request: Request, exc: OMCError | None = None) -> str | None:
    """Pull request-id from exception, request state, or return None."""
    if exc is not None and exc.request_id:
        return exc.request_id
    return getattr(request.state, "request_id", None)


async def omc_exception_handler(
    request: Request, exc: OMCError
) -> JSONResponse:
    """Convert OMCError -> structured JSON response."""
    request_id = _resolve_request_id(request, exc)
    if request_id is not None:
        exc.request_id = request_id

    status_code = _CODE_TO_STATUS.get(exc.error_code, 500)
    body = format_error_response(exc)

    log = get_logger("omc.error")
    bind_context(log, request_id=request_id)
    log.error(
        "omc_exception: %s (status=%d)",
        exc.error_code.value,
        status_code,
    )

    return JSONResponse(
        status_code=status_code,
        content=body,
        headers={_REQUEST_ID_HEADER: request_id} if request_id else None,
    )


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Convert FastAPI HTTPException -> structured JSON response."""
    request_id = _resolve_request_id(request)
    error_code = _STATUS_TO_CODE.get(exc.status_code, ErrorCode.PIPELINE_ERROR)

    log = get_logger("omc.http_error")
    bind_context(log, request_id=request_id)
    log.error(
        "http_exception: status=%d code=%s detail=%r",
        exc.status_code,
        error_code.value,
        exc.detail,
    )

    from common.contracts.errors import ErrorResponse

    body = ErrorResponse(
        error_code=error_code,  # type: ignore[arg-type]
        message=str(exc.detail),
        request_id=request_id,
    ).model_dump(exclude_none=True)

    return JSONResponse(
        status_code=exc.status_code,
        content=body,
        headers={_REQUEST_ID_HEADER: request_id} if request_id else None,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convert FastAPI request-validation error -> 422 structured response."""
    request_id = _resolve_request_id(request)

    from common.contracts.errors import ErrorResponse, ValidationErrorDetail

    details = [
        ValidationErrorDetail(
            field=".".join(str(p) for p in err.get("loc", [])),
            message=err.get("msg", "Invalid value"),
            code=err.get("type", "value_error"),
        )
        for err in exc.errors()
    ]
    body = ErrorResponse(
        error_code=ErrorCode.VALIDATION_ERROR,  # type: ignore[arg-type]
        message="Request validation failed",
        request_id=request_id,
        details=details,
    ).model_dump(exclude_none=True)

    log = get_logger("omc.validation_error")
    bind_context(log, request_id=request_id)
    log.error("validation_exception: %d field error(s)", len(details))

    return JSONResponse(
        status_code=422,
        content=body,
        headers={_REQUEST_ID_HEADER: request_id} if request_id else None,
    )


async def catch_all_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Last-resort handler for any uncaught Exception."""
    request_id = _resolve_request_id(request)

    log = get_logger("omc.unhandled")
    bind_context(log, request_id=request_id)
    log.exception("unhandled_exception: %s", type(exc).__name__)

    from common.contracts.errors import ErrorResponse

    body = ErrorResponse(
        error_code=ErrorCode.INTERNAL_ERROR,  # type: ignore[arg-type]
        message="Internal server error",
        request_id=request_id,
    ).model_dump(exclude_none=True)

    return JSONResponse(
        status_code=500,
        content=body,
        headers={_REQUEST_ID_HEADER: request_id} if request_id else None,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Wire all four handlers onto the FastAPI app."""
    app.add_exception_handler(OMCError, omc_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, catch_all_exception_handler)  # type: ignore[arg-type]

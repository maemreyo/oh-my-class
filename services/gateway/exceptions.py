"""Domain exception hierarchy for the oh-my-class gateway.

Every exception carries an ErrorCode, a human-readable message, optional
structured details, and an optional request_id for traceability.  Subclasses
add domain-specific fields (run_id, agent name, quality layer, etc.).

ErrorCode is defined here temporarily — once common/contracts/errors.py is
created, imports will be deduplicated.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """Machine-readable error codes shared across the gateway."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    PIPELINE_ERROR = "PIPELINE_ERROR"
    AGENT_ERROR = "AGENT_ERROR"
    QUALITY_GATE_ERROR = "QUALITY_GATE_ERROR"
    EXPORT_ERROR = "EXPORT_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class OMCError(Exception):
    """Base exception for all oh-my-class domain errors.

    Attributes:
        error_code: Machine-readable code from :class:`ErrorCode`.
        message: Human-readable description of the error.
        details: Optional list of structured detail dicts (field errors, etc.).
        request_id: Optional correlation ID for distributed tracing.
    """

    def __init__(
        self,
        *,
        error_code: ErrorCode,
        message: str,
        details: list[dict[str, Any]] | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = details or []
        self.request_id = request_id

    def __str__(self) -> str:
        base = f"[{self.error_code}] {self.message}"
        if self.request_id:
            base += f" (request_id={self.request_id})"
        return base

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"error_code={self.error_code!r}, "
            f"message={self.message!r}, "
            f"details={self.details!r}, "
            f"request_id={self.request_id!r})"
        )


# ── Domain subclasses ──────────────────────────────────────────────────


class ValidationError(OMCError):
    """Raised when input fails schema or business-rule validation."""

    def __init__(
        self,
        message: str = "Validation failed",
        *,
        details: list[dict[str, Any]] | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=message,
            details=details,
            request_id=request_id,
        )


class PipelineError(OMCError):
    """Raised when a pipeline step fails or the pipeline is in an invalid state.

    Attributes:
        run_id: The pipeline run that failed.
        step: The 1-indexed step number where the error occurred.
    """

    def __init__(
        self,
        message: str = "Pipeline error",
        *,
        run_id: str | None = None,
        step: int | None = None,
        details: list[dict[str, Any]] | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(
            error_code=ErrorCode.PIPELINE_ERROR,
            message=message,
            details=details,
            request_id=request_id,
        )
        self.run_id = run_id
        self.step = step


class AgentError(OMCError):
    """Raised when an agent call fails or returns invalid output.

    Attributes:
        agent: Name of the agent that failed.
    """

    def __init__(
        self,
        message: str = "Agent error",
        *,
        agent: str | None = None,
        details: list[dict[str, Any]] | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(
            error_code=ErrorCode.AGENT_ERROR,
            message=message,
            details=details,
            request_id=request_id,
        )
        self.agent = agent


class QualityGateError(OMCError):
    """Raised when a quality gate layer rejects an artifact.

    Attributes:
        layer: The 1-indexed quality layer that failed (1-6).
    """

    def __init__(
        self,
        message: str = "Quality gate failed",
        *,
        layer: int | None = None,
        details: list[dict[str, Any]] | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(
            error_code=ErrorCode.QUALITY_GATE_ERROR,
            message=message,
            details=details,
            request_id=request_id,
        )
        self.layer = layer


class ExportError(OMCError):
    """Raised when artifact export to a target format fails.

    Attributes:
        export_format: The target format that failed (e.g. "html", "gift").
    """

    def __init__(
        self,
        message: str = "Export failed",
        *,
        export_format: str | None = None,
        details: list[dict[str, Any]] | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(
            error_code=ErrorCode.EXPORT_ERROR,
            message=message,
            details=details,
            request_id=request_id,
        )
        self.export_format = export_format


class AuthenticationError(OMCError):
    """Raised when authentication fails (missing/invalid/expired token)."""

    def __init__(
        self,
        message: str = "Authentication failed",
        *,
        details: list[dict[str, Any]] | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(
            error_code=ErrorCode.AUTHENTICATION_ERROR,
            message=message,
            details=details,
            request_id=request_id,
        )


class AuthorizationError(OMCError):
    """Raised when the authenticated user lacks required permissions."""

    def __init__(
        self,
        message: str = "Authorization failed",
        *,
        details: list[dict[str, Any]] | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(
            error_code=ErrorCode.AUTHORIZATION_ERROR,
            message=message,
            details=details,
            request_id=request_id,
        )


class NotFoundError(OMCError):
    """Raised when a requested resource does not exist."""

    def __init__(
        self,
        message: str = "Resource not found",
        *,
        details: list[dict[str, Any]] | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(
            error_code=ErrorCode.NOT_FOUND,
            message=message,
            details=details,
            request_id=request_id,
        )


class RateLimitedError(OMCError):
    """Raised when a client exceeds the rate limit."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        details: list[dict[str, Any]] | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(
            error_code=ErrorCode.RATE_LIMITED,
            message=message,
            details=details,
            request_id=request_id,
        )


# ── Helpers ────────────────────────────────────────────────────────────


def format_error_response(exc: OMCError) -> dict[str, Any]:
    """Convert an OMCError into an ``ErrorResponse``-shaped dict.

    Returns::

        {
            "error_code": "VALIDATION_ERROR",
            "message": "Validation failed",
            "details": [],
            "request_id": None,
        }
    """
    return {
        "error_code": exc.error_code,
        "message": exc.message,
        "details": exc.details,
        "request_id": exc.request_id,
    }

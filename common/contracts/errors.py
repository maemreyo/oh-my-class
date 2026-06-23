"""Error models — typed error responses for the oh-my-class pipeline.

Provides structured error types used across all layers: gateway, agents,
quality gates, and exporters. Every error returned to the client conforms
to ErrorResponse or one of its specialisations.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ErrorCode(StrEnum):
    """Machine-readable error categories.

    Every error response must carry one of these codes so that clients
    can dispatch recovery logic without parsing the human message.
    """

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


class ValidationErrorDetail(BaseModel):
    """A single field-level validation failure.

    Returned inside ErrorResponse.details when the error code is
    VALIDATION_ERROR. Multiple details may be returned in one response
    to report all failing fields at once.
    """

    field: str = Field(..., description="Dotted path to the failing field, e.g. 'title'")
    message: str = Field(..., description="Human-readable explanation of the failure")
    code: str = Field(..., description="Machine-readable code, e.g. 'min_length'")


class ErrorResponse(BaseModel):
    """Standard error envelope returned by every API endpoint.

    Clients should switch on error_code to determine recovery strategy.
    The message field is safe to display to end users.
    """

    error_code: ErrorCode = Field(
        ..., description="Machine-readable error category"
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Human-readable error message",
    )
    request_id: str | None = Field(
        default=None, description="Correlation ID for distributed tracing"
    )
    timestamp: str | None = Field(
        default=None,
        description="ISO 8601 timestamp of when the error occurred",
    )
    details: list[ValidationErrorDetail] = Field(
        default_factory=list,
        description="Field-level validation details; empty for non-validation errors",
    )


class PipelineErrorResponse(ErrorResponse):
    """Error response specialised for pipeline and agent failures.

    Extends ErrorResponse with fields that identify which pipeline run,
    step, and agent produced the error — essential for debugging the
    13-step pipeline.
    """

    run_id: str | None = Field(default=None, description="Pipeline run identifier")
    step: int | None = Field(
        default=None,
        description="Pipeline step number (1-13) where the error occurred",
    )
    agent: str | None = Field(
        default=None,
        description="Agent that produced the error (e.g. 'planner')",
    )

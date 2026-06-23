"""Tests for errors."""

import pytest
from pydantic import ValidationError

from common.contracts.errors import (
    ErrorCode,
    ErrorResponse,
    PipelineErrorResponse,
    ValidationErrorDetail,
)


class TestErrorCode:
    """Test suite for ErrorCode enum."""

    def test_error_code_values(self):
        """All expected error codes must exist."""
        expected = {
            "VALIDATION_ERROR",
            "PIPELINE_ERROR",
            "AGENT_ERROR",
            "QUALITY_GATE_ERROR",
            "EXPORT_ERROR",
            "AUTHENTICATION_ERROR",
            "AUTHORIZATION_ERROR",
            "NOT_FOUND",
            "RATE_LIMITED",
            "INTERNAL_ERROR",
        }
        actual = {member.value for member in ErrorCode}
        assert actual == expected


class TestValidationErrorDetail:
    """Test suite for ValidationErrorDetail model."""

    def test_validation_error_detail(self):
        """ValidationErrorDetail accepts valid field, message, and code."""
        detail = ValidationErrorDetail(field="title", message="too short", code="min_length")
        assert detail.field == "title"
        assert detail.message == "too short"
        assert detail.code == "min_length"


class TestErrorResponse:
    """Test suite for ErrorResponse model."""

    def test_error_response_serialization(self):
        """ErrorResponse serialises to a dict with all expected keys."""
        response = ErrorResponse(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Invalid input",
        )
        data = response.model_dump()
        assert set(data.keys()) == {"error_code", "message", "request_id", "timestamp", "details"}
        assert data["error_code"] == "VALIDATION_ERROR"

    def test_error_response_optional_fields(self):
        """request_id and timestamp default to None."""
        response = ErrorResponse(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Something broke",
        )
        assert response.request_id is None
        assert response.timestamp is None

    def test_error_response_validation(self):
        """message must respect min_length=1 and max_length=500."""
        with pytest.raises(ValidationError):
            ErrorResponse(error_code=ErrorCode.VALIDATION_ERROR, message="")
        with pytest.raises(ValidationError):
            ErrorResponse(error_code=ErrorCode.VALIDATION_ERROR, message="x" * 501)


class TestPipelineErrorResponse:
    """Test suite for PipelineErrorResponse model."""

    def test_pipeline_error_response(self):
        """PipelineErrorResponse carries run_id, step, and agent fields."""
        response = PipelineErrorResponse(
            error_code=ErrorCode.AGENT_ERROR,
            message="Planner failed",
            run_id="run-001",
            step=3,
            agent="planner",
        )
        assert response.run_id == "run-001"
        assert response.step == 3
        assert response.agent == "planner"
        assert response.error_code == ErrorCode.AGENT_ERROR

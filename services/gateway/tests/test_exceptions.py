"""Tests for the gateway domain exception hierarchy."""

import sys
from pathlib import Path

# Ensure the project root (parent of `services/`) is on sys.path so that
# `from services.gateway.exceptions import ...` works under plain pytest
# invocation. The workspace venv installs `services.gateway` as an editable
# package, but `services` is a namespace package, so pytest collection of a
# test module inside `services/gateway/tests/` does not see `services` on
# sys.path by default.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from services.gateway.exceptions import (  # noqa: E402
    AgentError,
    AuthenticationError,
    AuthorizationError,
    ErrorCode,
    ExportError,
    NotFoundError,
    OMCError,
    PipelineError,
    QualityGateError,
    RateLimitedError,
    ValidationError,
    format_error_response,
)


class TestOMCErrorBase:
    """Tests for the OMCError base exception."""

    def test_create_omc_error(self) -> None:
        """Given an OMCError with all fields, when inspecting it, then fields are correct."""
        exc = OMCError(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Something went wrong",
            details=[{"field": "name", "issue": "required"}],
            request_id="req-123",
        )

        assert exc.error_code == ErrorCode.VALIDATION_ERROR
        assert exc.message == "Something went wrong"
        assert exc.details == [{"field": "name", "issue": "required"}]
        assert exc.request_id == "req-123"

    def test_str_representation(self) -> None:
        """Given OMCError with request_id, when str(), then includes code and id."""
        exc = OMCError(
            error_code=ErrorCode.PIPELINE_ERROR,
            message="Step 3 failed",
            request_id="req-456",
        )

        result = str(exc)

        assert "[PIPELINE_ERROR] Step 3 failed" in result
        assert "request_id=req-456" in result

    def test_str_without_request_id(self) -> None:
        """Given an OMCError without request_id, when converting to str, then no parenthetical."""
        exc = OMCError(error_code=ErrorCode.NOT_FOUND, message="Gone")

        result = str(exc)

        assert result == "[NOT_FOUND] Gone"

    def test_repr_shows_all_fields(self) -> None:
        """Given an OMCError, when calling repr, then all fields are visible."""
        exc = OMCError(
            error_code=ErrorCode.RATE_LIMITED,
            message="Slow down",
            request_id="req-789",
        )

        result = repr(exc)

        assert "OMCError(" in result
        assert "RATE_LIMITED" in result
        assert "Slow down" in result
        assert "req-789" in result

    def test_details_default_to_empty_list(self) -> None:
        """Given an OMCError without details, when accessing details, then it is empty list."""
        exc = OMCError(error_code=ErrorCode.VALIDATION_ERROR, message="Bad")

        assert exc.details == []

    def test_is_exception_subclass(self) -> None:
        """Given an OMCError, when checking inheritance, then it is an Exception."""
        exc = OMCError(error_code=ErrorCode.VALIDATION_ERROR, message="x")

        assert isinstance(exc, Exception)


class TestValidationError:
    """Tests for ValidationError subclass."""

    def test_custom_message(self) -> None:
        """Given a ValidationError with a custom message, then message is correct."""
        exc = ValidationError(
            message="Grade must be between 1 and 12",
            details=[{"field": "grade_level", "issue": "out of range"}],
        )

        assert exc.error_code == ErrorCode.VALIDATION_ERROR
        assert exc.message == "Grade must be between 1 and 12"
        assert len(exc.details) == 1

    def test_default_message(self) -> None:
        """Given a ValidationError with no message, when inspecting it, then default is used."""
        exc = ValidationError()

        assert exc.message == "Validation failed"


class TestPipelineErrorHasRunId:
    """Tests for PipelineError extra fields."""

    def test_run_id_and_step(self) -> None:
        """Given a PipelineError with run_id and step, when inspecting it, then fields are set."""
        exc = PipelineError(
            message="Node timed out",
            run_id="run-abc",
            step=7,
        )

        assert exc.run_id == "run-abc"
        assert exc.step == 7
        assert exc.error_code == ErrorCode.PIPELINE_ERROR

    def test_defaults_are_none(self) -> None:
        """Given a PipelineError without run_id/step, when inspecting it, then both are None."""
        exc = PipelineError()

        assert exc.run_id is None
        assert exc.step is None


class TestAgentErrorHasAgent:
    """Tests for AgentError extra fields."""

    def test_agent_field(self) -> None:
        """Given an AgentError with agent name, when inspecting it, then agent is set."""
        exc = AgentError(
            message="LLM returned empty response",
            agent="planner",
        )

        assert exc.agent == "planner"
        assert exc.error_code == ErrorCode.AGENT_ERROR

    def test_agent_default_is_none(self) -> None:
        """Given an AgentError without agent, when inspecting it, then agent is None."""
        exc = AgentError()

        assert exc.agent is None


class TestFormatErrorResponse:
    """Tests for the format_error_response helper."""

    def test_returns_correct_dict_shape(self) -> None:
        """Given OMCError, format_error_response returns dict matching ErrorResponse."""
        exc = ValidationError(
            message="Bad input",
            details=[{"field": "topic"}],
            request_id="req-999",
        )

        result = format_error_response(exc)

        assert result == {
            "error_code": ErrorCode.VALIDATION_ERROR,
            "message": "Bad input",
            "details": [{"field": "topic"}],
            "request_id": "req-999",
        }

    def test_with_none_request_id(self) -> None:
        """Given an error without request_id, when formatting, then request_id is None in dict."""
        exc = NotFoundError(message="Run not found")

        result = format_error_response(exc)

        assert result["request_id"] is None
        assert result["error_code"] == ErrorCode.NOT_FOUND

    def test_with_empty_details(self) -> None:
        """Given an error with no details, when formatting, then details is empty list."""
        exc = RateLimitedError()

        result = format_error_response(exc)

        assert result["details"] == []


class TestExceptionHierarchy:
    """Verify all domain exceptions inherit from OMCError."""

    ALL_SUBCLASSES = [
        ValidationError,
        PipelineError,
        AgentError,
        QualityGateError,
        ExportError,
        AuthenticationError,
        AuthorizationError,
        NotFoundError,
        RateLimitedError,
    ]

    def test_all_subclasses_inherit_from_omc_error(self) -> None:
        """Every domain exception class is an OMCError subclass."""
        for exc_class in self.ALL_SUBCLASSES:
            assert issubclass(exc_class, OMCError), f"{exc_class.__name__} not OMCError"

    def test_all_subclasses_inherit_from_exception(self) -> None:
        """Every domain exception class is an Exception subclass."""
        for exc_class in self.ALL_SUBCLASSES:
            assert issubclass(exc_class, Exception), f"{exc_class.__name__} not Exception"

    def test_all_subclasses_are_catchable_as_omc_error(self) -> None:
        """Given any domain exception raised, when catching OMCError, then it is caught."""
        for exc_class in self.ALL_SUBCLASSES:
            try:
                raise exc_class(message="test")
            except OMCError:
                pass  # expected

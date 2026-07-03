"""Input sanitization middleware — validates and sanitizes raw requests.

First line of defense: ensures requests are well-formed before entering the pipeline.
"""

from __future__ import annotations

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


class InputValidationError(Exception):
    """Raised when input fails validation."""
    pass


class InputSanitizationMiddleware(BaseMiddleware):
    """Validates and sanitizes raw_request and class_info before the LLM call."""

    name: str = "input_sanitization"
    order: int = 1

    async def before_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        raw = state.get("raw_request", "")
        if not raw or not raw.strip():
            raise InputValidationError("raw_request is empty")
        class_info = state.get("class_info", {})
        if "grade" in class_info:
            grade = class_info["grade"]
            valid = (grade == "kindergarten") or (isinstance(grade, int) and 1 <= grade <= 12)
            if not valid:
                raise InputValidationError(f"Invalid grade: {grade}")
        if "subject" in class_info and (not class_info["subject"] or not str(class_info["subject"]).strip()):  # noqa: E501
            raise InputValidationError("subject is empty")
        return state

    async def after_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        return state

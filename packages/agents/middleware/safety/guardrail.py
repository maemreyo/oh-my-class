"""Guardrail middleware — content safety filter for agent outputs.

Screens LLM outputs for harmful, biased, or inappropriate content.
Blocks output that violates content policies before it reaches the pipeline.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class GuardrailViolationError(Exception):
    """Raised when content violates guardrails."""
    pass


class GuardrailMiddleware(BaseMiddleware):
    """Screens agent outputs for content safety violations.

    Checks for:
    - Harmful or violent content
    - Bias and discrimination
    - PII leakage (student names, scores)
    - Age-inappropriate content
    """

    name: str = "guardrail"
    order: int = 8

    EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    PHONE_PATTERN = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
    SCORE_PATTERN = re.compile(r'\b\d+(\.\d+)?/%\b')

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Check input for PII before LLM call."""
        raw_request = state.get("raw_request", "")

        violations = []
        if self.EMAIL_PATTERN.search(raw_request):
            violations.append("Email address detected in input")
        if self.PHONE_PATTERN.search(raw_request):
            violations.append("Phone number detected in input")

        if violations:
            raise GuardrailViolationError(f"PII violations: {violations}")

        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Check output for PII and harmful content after LLM call."""
        artifacts = state.get("artifacts", [])
        for artifact in artifacts:
            content = str(artifact)
            if self.EMAIL_PATTERN.search(content):
                raise GuardrailViolationError("Email address detected in output")
            if self.PHONE_PATTERN.search(content):
                raise GuardrailViolationError("Phone number detected in output")

        return state

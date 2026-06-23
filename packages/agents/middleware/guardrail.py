"""Guardrail middleware — content safety filter for agent outputs.

Screens LLM outputs for harmful, biased, or inappropriate content.
Blocks output that violates content policies before it reaches the pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class GuardrailMiddleware(BaseMiddleware):
    """Screens agent outputs for content safety violations.

    Checks for:
    - Harmful or violent content
    - Bias and discrimination
    - PII leakage (student names, scores)
    - Age-inappropriate content
    """

    name: str = "guardrail"
    order: int = 5

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Pre-screen input context for safety concerns.

        TODO: Check revision_feedback and raw_request for sensitive content.
        """
        # TODO: Scan state fields for PII patterns
        # TODO: Flag any concerning content in context.metadata
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Post-screen output for content safety violations.

        TODO: Run output through safety classifier.
        TODO: Block or flag output that violates content policies.
        """
        # TODO: Extract latest LLM output from state
        # TODO: Run through content safety checks
        # TODO: If violation, either block (raise) or sanitize
        return state

from __future__ import annotations

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState
from packages.quality.layer2_content.pii import detect_pii


class GuardrailViolationError(Exception):
    pass


class GuardrailMiddleware(BaseMiddleware):
    """Screens agent input and output artifacts for PII (email, phone).

    Detection delegates to the shared `detect_pii` policy so patterns stay
    owned in one place (packages.quality.layer2_content.pii).
    """

    name: str = "guardrail"
    order: int = 7

    async def before_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        _raise_on_pii(state.get("raw_request", ""), location="input")
        return state

    async def after_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        for artifact in state.get("artifacts", []):
            content = artifact.get("content", "") if isinstance(artifact, dict) else str(artifact)
            _raise_on_pii(content, location="output")
        return state


def _raise_on_pii(text: str, *, location: str) -> None:
    counts = detect_pii(text).redaction_counts
    if counts.get("email", 0):
        raise GuardrailViolationError(f"Email address detected in {location}")
    if counts.get("phone", 0):
        raise GuardrailViolationError(f"Phone number detected in {location}")

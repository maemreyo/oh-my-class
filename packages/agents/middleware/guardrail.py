"""Backward-compatibility shim — re-exports from safety tier.

The canonical location is packages.agents.middleware.safety.guardrail.
"""

from packages.agents.middleware.safety.guardrail import GuardrailMiddleware, GuardrailViolationError

__all__ = ["GuardrailMiddleware", "GuardrailViolationError"]

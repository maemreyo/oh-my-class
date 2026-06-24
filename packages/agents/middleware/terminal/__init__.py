"""Terminal tier middleware — final gate middleware (must always be last)."""

from packages.agents.middleware.terminal.clarification import ClarificationMiddleware

__all__ = [
    "ClarificationMiddleware",
]

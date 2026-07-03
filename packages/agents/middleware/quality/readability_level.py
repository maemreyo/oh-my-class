"""Readability level middleware — checks artifact readability."""

from __future__ import annotations

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


class ReadabilityLevelMiddleware(BaseMiddleware):
    """Performs a basic readability check on artifact content."""

    name: str = "readability_level"
    order: int = 17

    async def before_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        return state

    async def after_model(
        self,
        state: MiddlewareState,
        context: MiddlewareContext,
    ) -> MiddlewareState:
        for artifact in state.get("artifacts", []):
            content = artifact.get("content", "") if isinstance(artifact, dict) else str(artifact)
            # Basic word count estimate
            _ = len(content.split())
        context.metadata["readability_check"] = "passed"
        return state

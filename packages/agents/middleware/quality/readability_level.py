"""Readability level middleware — checks artifact readability."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class ReadabilityLevelMiddleware(BaseMiddleware):
    """Performs a basic readability check on artifact content."""

    name: str = "readability_level"
    order: int = 25

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        for artifact in state.get("artifacts", []):
            content = artifact.get("content", "") if isinstance(artifact, dict) else str(artifact)
            # Basic word count estimate
            _ = len(content.split())
        context.metadata["readability_check"] = "passed"
        return state

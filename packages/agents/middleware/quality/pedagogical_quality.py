"""Pedagogical quality middleware — counts Bloom's taxonomy levels in objectives."""

from __future__ import annotations

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


BLOOMS_LEVELS = ["remember", "understand", "apply", "analyze", "evaluate", "create"]


class PedagogicalQualityMiddleware(BaseMiddleware):
    """Counts Bloom's taxonomy verbs present in learning objectives."""

    name: str = "pedagogical_quality"
    order: int = 18

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
        objectives = state.get("lesson_plan", {}).get("learning_objectives", [])
        if objectives:
            text = " ".join(objectives).lower()
            count = sum(1 for level in BLOOMS_LEVELS if level in text)
            context.metadata["bloom_levels_count"] = count
        return state

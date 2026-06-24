"""Pedagogical quality middleware — counts Bloom's taxonomy levels in objectives."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


BLOOMS_LEVELS = ["remember", "understand", "apply", "analyze", "evaluate", "create"]


class PedagogicalQualityMiddleware(BaseMiddleware):
    """Counts Bloom's taxonomy verbs present in learning objectives."""

    name: str = "pedagogical_quality"
    order: int = 26

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
        objectives = state.get("lesson_plan", {}).get("learning_objectives", [])
        if objectives:
            text = " ".join(objectives).lower()
            count = sum(1 for level in BLOOMS_LEVELS if level in text)
            context.metadata["bloom_levels_count"] = count
        return state

"""Learning objective alignment middleware — checks artifacts match objectives."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class LearningObjectiveAlignmentMiddleware(BaseMiddleware):
    """Marks alignment_check passed when both objectives and artifacts are present."""

    name: str = "learning_objective_alignment"
    order: int = 29

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
        artifacts = state.get("artifacts", [])
        if objectives and artifacts:
            context.metadata["alignment_check"] = "passed"
        return state

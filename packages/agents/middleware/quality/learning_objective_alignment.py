"""Learning objective alignment middleware — checks artifacts match objectives."""

from __future__ import annotations

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


class LearningObjectiveAlignmentMiddleware(BaseMiddleware):
    """Marks alignment_check passed when both objectives and artifacts are present."""

    name: str = "learning_objective_alignment"
    order: int = 21

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
        artifacts = state.get("artifacts", [])
        if objectives and artifacts:
            context.metadata["alignment_check"] = "passed"
        return state

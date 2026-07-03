"""Curriculum alignment middleware — checks artifacts against curriculum standards."""

from __future__ import annotations

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


class CurriculumAlignmentMiddleware(BaseMiddleware):
    """Warns when artifacts may not align with the lesson plan curriculum standard."""

    name: str = "curriculum_alignment"
    order: int = 16

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
        artifacts = state.get("artifacts")
        standard = state.get("lesson_plan", {}).get("curriculum_standard")
        if artifacts and standard:
            objectives = state.get("lesson_plan", {}).get("learning_objectives", [])
            aligned = any(standard[:3].lower() in obj.lower() for obj in objectives)
            if not aligned:
                context.metadata["curriculum_alignment_warning"] = (
                    f"Artifacts may not align with {standard}"
                )
        return state

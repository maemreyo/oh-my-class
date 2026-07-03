"""Todo list middleware — tracks lesson plan objective step count."""

from __future__ import annotations

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


class TodoListMiddleware(BaseMiddleware):
    """Injects todo_steps count from lesson plan learning objectives."""

    name: str = "todo_list"
    order: int = 16

    async def before_model(
        self,
        state: MiddlewareState,
        context: MiddlewareContext,
    ) -> MiddlewareState:
        lesson_plan = state.get("lesson_plan")
        if lesson_plan:
            objectives = lesson_plan.get("learning_objectives", [])
            context.metadata["todo_steps"] = len(objectives)
        return state

    async def after_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        return state

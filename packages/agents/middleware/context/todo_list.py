"""Todo list middleware — tracks lesson plan objective step count."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class TodoListMiddleware(BaseMiddleware):
    """Injects todo_steps count from lesson plan learning objectives."""

    name: str = "todo_list"
    order: int = 16

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        lesson_plan = state.get("lesson_plan")
        if lesson_plan:
            objectives = lesson_plan.get("learning_objectives", [])
            context.metadata["todo_steps"] = len(objectives)
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        return state

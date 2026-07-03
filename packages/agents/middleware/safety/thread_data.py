"""Thread data middleware — initializes run directory and thread metadata."""

from __future__ import annotations

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


class ThreadDataMiddleware(BaseMiddleware):
    """Populates run_dir and thread_id in context metadata."""

    name: str = "thread_data"
    order: int = 3

    async def before_model(
        self,
        state: MiddlewareState,
        context: MiddlewareContext,
    ) -> MiddlewareState:
        run_id = state.get("run_id", "unknown")
        context.metadata["run_dir"] = f"runs/{run_id}"
        context.metadata["thread_id"] = state.get("run_id", "")
        return state

    async def after_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        return state

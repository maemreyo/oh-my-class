"""Thread data middleware — initializes run directory and thread metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class ThreadDataMiddleware(BaseMiddleware):
    """Populates run_dir and thread_id in context metadata."""

    name: str = "thread_data"
    order: int = 3

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        run_id = state.get("run_id", "unknown")
        context.metadata["run_dir"] = f"runs/{run_id}"
        context.metadata["thread_id"] = state.get("run_id", "")
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        return state

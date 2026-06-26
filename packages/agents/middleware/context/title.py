"""Title middleware — derives a run title from the raw request."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class TitleMiddleware(BaseMiddleware):
    """Sets run_title in context metadata from the first N chars of raw_request."""

    name: str = "title"
    order: int = 18

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        if "run_title" not in context.metadata:
            from packages.agents.config.gate_config import GateConfig
            config = GateConfig()
            raw = state.get("raw_request", "")
            if raw:
                context.metadata["run_title"] = raw[:config.title_max_length].strip()
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        return state

"""Uploads middleware — validates uploaded file attachments."""

from __future__ import annotations

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


class UploadsMiddleware(BaseMiddleware):
    """Validates uploaded_files entries before the LLM call."""

    name: str = "uploads"
    order: int = 4

    async def before_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        uploaded_files = state.get("uploaded_files")
        if uploaded_files:
            for f in uploaded_files:
                if not isinstance(f, dict) or "path" not in f or not f["path"]:
                    raise ValueError(f"Invalid upload: {f}")
        return state

    async def after_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        return state

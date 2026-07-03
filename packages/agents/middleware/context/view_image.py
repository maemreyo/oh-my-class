"""View image middleware — tracks uploaded image count in context metadata."""

from __future__ import annotations

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


class ViewImageMiddleware(BaseMiddleware):
    """Records image_count from uploaded_images into context metadata."""

    name: str = "view_image"
    order: int = 20

    async def before_model(
        self,
        state: MiddlewareState,
        context: MiddlewareContext,
    ) -> MiddlewareState:
        images = state.get("uploaded_images")
        if images:
            context.metadata["image_count"] = len(images)
        return state

    async def after_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        return state

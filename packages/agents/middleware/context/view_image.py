"""View image middleware — tracks uploaded image count in context metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class ViewImageMiddleware(BaseMiddleware):
    """Records image_count from uploaded_images into context metadata."""

    name: str = "view_image"
    order: int = 20

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        images = state.get("uploaded_images")
        if images:
            context.metadata["image_count"] = len(images)
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        return state

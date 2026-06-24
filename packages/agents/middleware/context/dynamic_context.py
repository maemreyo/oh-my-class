"""Dynamic context middleware — injects date and class summary into context metadata."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class DynamicContextMiddleware(BaseMiddleware):
    """Injects today's date and class summary into context metadata."""

    name: str = "dynamic_context"
    order: int = 13

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        class_info = state.get("class_info", {})
        parts = []
        if class_info.get("grade"):
            parts.append(f"Grade: {class_info['grade']}")
        if class_info.get("subject"):
            parts.append(f"Subject: {class_info['subject']}")
        if class_info.get("school"):
            parts.append(f"School: {class_info['school']}")
        summary = ", ".join(parts) if parts else "No class info"
        context.metadata["injected_context"] = {
            "today": date.today().isoformat(),
            "class_summary": summary,
        }
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        return state

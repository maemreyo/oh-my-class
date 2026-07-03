"""Dynamic context middleware — injects date and class summary into context metadata."""

from __future__ import annotations

from datetime import date
from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


class DynamicContextMiddleware(BaseMiddleware):
    """Injects today's date and class summary into context metadata."""

    name: str = "dynamic_context"
    order: int = 10

    async def before_model(
        self,
        state: MiddlewareState,
        context: MiddlewareContext,
    ) -> MiddlewareState:
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
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        return state

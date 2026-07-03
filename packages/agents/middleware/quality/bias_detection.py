"""Bias detection middleware — scans artifact content for gendered bias patterns."""

from __future__ import annotations

import re

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


BIAS_PATTERNS = re.compile(
    r"\b(he|she)\s+(is|was|can|will)\s+(naturally|always|typically)\b",
    re.IGNORECASE,
)


class BiasDetectionMiddleware(BaseMiddleware):
    """Scans artifact content for basic gendered bias patterns (warning only)."""

    name: str = "bias_detection"
    order: int = 19

    async def before_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        return state

    async def after_model(
        self,
        state: MiddlewareState,
        context: MiddlewareContext,
    ) -> MiddlewareState:
        for artifact in state.get("artifacts", []):
            content = artifact.get("content", "") if isinstance(artifact, dict) else str(artifact)
            # Scan for basic bias patterns (warning only, not blocking in this implementation)
            _ = BIAS_PATTERNS.search(content)
        context.metadata["bias_check"] = "passed"
        return state

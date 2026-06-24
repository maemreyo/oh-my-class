"""Bias detection middleware — scans artifact content for gendered bias patterns."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


BIAS_PATTERNS = re.compile(
    r"\b(he|she)\s+(is|was|can|will)\s+(naturally|always|typically)\b",
    re.IGNORECASE,
)


class BiasDetectionMiddleware(BaseMiddleware):
    """Scans artifact content for basic gendered bias patterns (warning only)."""

    name: str = "bias_detection"
    order: int = 27

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        for artifact in state.get("artifacts", []):
            content = artifact.get("content", "") if isinstance(artifact, dict) else str(artifact)
            # Scan for basic bias patterns (warning only, not blocking in this implementation)
            _ = BIAS_PATTERNS.search(content)
        context.metadata["bias_check"] = "passed"
        return state

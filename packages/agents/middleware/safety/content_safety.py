"""Content safety middleware — blocks K-12-inappropriate content.

Screens both inputs and artifact outputs for content blocked in an educational context.
"""

from __future__ import annotations

import re
from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


BLOCKED_PATTERNS = re.compile(r"violence|gore|explicit|adult\s+content|nsfw", re.IGNORECASE)


class ContentSafetyError(Exception):
    """Raised when content is blocked for K-12 audiences."""
    pass


class ContentSafetyMiddleware(BaseMiddleware):
    """Blocks K-12-inappropriate content in requests and artifacts."""

    name: str = "content_safety"
    order: int = 5

    async def before_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        raw = state.get("raw_request", "")
        if BLOCKED_PATTERNS.search(raw):
            raise ContentSafetyError("Content blocked: inappropriate for K-12")
        return state

    async def after_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        for artifact in state.get("artifacts", []):
            content = artifact.get("content", "") if isinstance(artifact, dict) else str(artifact)
            if BLOCKED_PATTERNS.search(content):
                raise ContentSafetyError("Artifact content blocked: inappropriate for K-12")
        return state

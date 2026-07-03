"""Artifact coherence middleware — checks artifact type diversity."""

from __future__ import annotations

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


class ArtifactCoherenceMiddleware(BaseMiddleware):
    """Records artifact count and type diversity in context metadata."""

    name: str = "artifact_coherence"
    order: int = 20

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
        artifacts = state.get("artifacts", [])
        if artifacts:
            types = set()
            for artifact in artifacts:
                if isinstance(artifact, dict):
                    types.add(artifact.get("type", "unknown"))
                else:
                    types.add("unknown")
            context.metadata["artifact_count"] = len(artifacts)
        return state

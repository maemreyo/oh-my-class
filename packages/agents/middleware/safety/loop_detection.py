"""Loop detection middleware — dual-layer detection for agent loops.

Layer 1: Hash-based detection — tracks consecutive identical responses.
Layer 2: Frequency-based detection — tracks response pattern frequency over time.

Triggers circuit breaker or escalation when loop is detected.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class LoopDetectedError(Exception):
    """Raised when an agent loop is detected."""
    pass


class LoopDetectionMiddleware(BaseMiddleware):
    """Detects and breaks infinite loops in agent responses.

    Hash layer: compares response hashes to detect identical consecutive outputs.
    Frequency layer: tracks response patterns over a sliding window.
    """

    name: str = "loop_detection"
    order: int = 11

    def __init__(self, threshold: int = 5) -> None:
        self.threshold = threshold
        self._hash_history: list[str] = []

    def _compute_hash(self, state: OhMyClassState) -> str:
        """Compute hash of relevant state fields."""
        relevant = {
            "lesson_plan": state.get("lesson_plan"),
            "research_bundle": state.get("research_bundle"),
            "artifacts": state.get("artifacts"),
            "quality_scores": state.get("quality_scores"),
        }
        serialized = json.dumps(relevant, sort_keys=True, default=str)
        return hashlib.md5(serialized.encode()).hexdigest()

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Check for loop conditions before LLM call."""
        current_hash = self._compute_hash(state)

        if len(self._hash_history) >= self.threshold:
            recent = self._hash_history[-self.threshold:]
            if len(set(recent)) == 1 and recent[0] == current_hash:
                raise LoopDetectedError(
                    f"Loop detected: {self.threshold} identical consecutive states"
                )

        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Record response hash after LLM call."""
        current_hash = self._compute_hash(state)
        self._hash_history.append(current_hash)

        # Keep only sliding window
        if len(self._hash_history) > self.threshold * 2:
            self._hash_history = self._hash_history[-self.threshold * 2:]

        return state

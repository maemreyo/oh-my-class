"""Ordered middleware list — the complete middleware chain for the pipeline.

INVARIANT-08: Clarification middleware is always the last in the chain (order=24).
All other middleware order values must be 1–23.

This file defines the canonical order. The pipeline runtime imports this
list and chains middleware in order. Do NOT reorder without updating
all references.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packages.agents.middleware.base import BaseMiddleware

from packages.agents.middleware.loop_detection import LoopDetectionMiddleware
from packages.agents.middleware.token_budget import TokenBudgetMiddleware
from packages.agents.middleware.dangling_tool_call import DanglingToolCallMiddleware
from packages.agents.middleware.summarization import SummarizationMiddleware
from packages.agents.middleware.guardrail import GuardrailMiddleware

ORDERED_MIDDLEWARE_LIST: list[type[BaseMiddleware]] = [
    LoopDetectionMiddleware,      # order=1
    TokenBudgetMiddleware,        # order=2
    DanglingToolCallMiddleware,   # order=3
    SummarizationMiddleware,      # order=4
    GuardrailMiddleware,          # order=5
    # ── Layer 6–23: Domain-specific middleware ─────────────
    # (Add domain-specific middleware here as they are implemented)
    #
    # ── Layer 24: Clarification (MUST be last) ────────────
    # packages.agents.middleware.clarification.ClarificationMiddleware,  # order=24
]

EXPECTED_MIDDLEWARE_COUNT: int = 24

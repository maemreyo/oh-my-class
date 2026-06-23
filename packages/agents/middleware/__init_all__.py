"""Ordered middleware list — the complete middleware chain for the pipeline.

INVARIANT-08: Clarification middleware is always the last in the chain (order=24).
All other middleware order values must be 1–23.

This file defines the canonical order. The pipeline runtime imports this
list and chains middleware in order. Do NOT reorder without updating
all references.

TODO: Add real middleware classes as they are implemented.
The list below is a placeholder showing the intended structure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packages.agents.middleware.base import BaseMiddleware

# Ordered middleware list — execution order is determined by list position.
# Each entry is a class reference (not an instance).
ORDERED_MIDDLEWARE_LIST: list[type[BaseMiddleware]] = [
    # ── Layer 1–5: Infrastructure ──────────────────────────
    # packages.agents.middleware.loop_detection.LoopDetectionMiddleware,      # order=1
    # packages.agents.middleware.token_budget.TokenBudgetMiddleware,          # order=2
    # packages.agents.middleware.dangling_tool_call.DanglingToolCallMiddleware, # order=3
    # packages.agents.middleware.summarization.SummarizationMiddleware,       # order=4
    # packages.agents.middleware.guardrail.GuardrailMiddleware,              # order=5
    #
    # ── Layer 6–23: Domain-specific middleware ─────────────
    # (Add domain-specific middleware here as they are implemented)
    #
    # ── Layer 24: Clarification (MUST be last) ────────────
    # packages.agents.middleware.clarification.ClarificationMiddleware,       # order=24
]

# Total expected middleware count (including not-yet-implemented ones)
EXPECTED_MIDDLEWARE_COUNT: int = 24

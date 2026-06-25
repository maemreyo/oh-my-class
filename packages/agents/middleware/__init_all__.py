"""Ordered middleware list — the complete middleware chain for the pipeline.

This file is kept for backward compatibility. The canonical source is now
packages.agents.middleware.registry.

INVARIANT-08: ClarificationMiddleware is always the last in the chain (order=30).
"""

from __future__ import annotations

from packages.agents.middleware.registry import EXPECTED_MIDDLEWARE_COUNT, ORDERED_MIDDLEWARE_LIST

__all__ = ["ORDERED_MIDDLEWARE_LIST", "EXPECTED_MIDDLEWARE_COUNT"]

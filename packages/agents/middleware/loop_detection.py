"""Backward-compatibility shim — re-exports from safety tier.

The canonical location is packages.agents.middleware.safety.loop_detection.
"""

from packages.agents.middleware.safety.loop_detection import LoopDetectedError, LoopDetectionMiddleware

__all__ = ["LoopDetectedError", "LoopDetectionMiddleware"]

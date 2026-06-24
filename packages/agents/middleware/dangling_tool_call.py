"""Backward-compatibility shim — re-exports from safety tier.

The canonical location is packages.agents.middleware.safety.dangling_tool_call.
"""

from packages.agents.middleware.safety.dangling_tool_call import DanglingToolCallMiddleware

__all__ = ["DanglingToolCallMiddleware"]

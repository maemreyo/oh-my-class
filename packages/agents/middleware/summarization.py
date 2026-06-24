"""Backward-compatibility shim — re-exports from context tier.

The canonical location is packages.agents.middleware.context.summarization.
"""

from packages.agents.middleware.context.summarization import SummarizationMiddleware

__all__ = ["SummarizationMiddleware"]

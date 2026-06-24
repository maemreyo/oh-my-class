"""Middleware chain for the oh-my-class agent pipeline.

Exports BaseMiddleware for subclassing. Individual middleware implementations
are registered in registry.py and re-exported from their tier subpackages.

Backward-compatible re-exports are provided for the original flat-file paths.
"""

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext
from packages.agents.middleware.registry import ORDERED_MIDDLEWARE_LIST, EXPECTED_MIDDLEWARE_COUNT

__all__ = ["BaseMiddleware", "MiddlewareContext", "ORDERED_MIDDLEWARE_LIST", "EXPECTED_MIDDLEWARE_COUNT"]

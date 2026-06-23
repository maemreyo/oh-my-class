"""Middleware chain for the oh-my-class agent pipeline.

Exports BaseMiddleware for subclassing. Individual middleware implementations
are imported in __init_all__.py for the ordered middleware list.
"""

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

__all__ = ["BaseMiddleware", "MiddlewareContext"]

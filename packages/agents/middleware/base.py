"""Middleware base class for the oh-my-class agent pipeline.

Every middleware implements the BaseMiddleware interface and operates as a
single-concern layer in the chain. Middleware order is fixed (1–30);
Clarification middleware MUST always be last (order=31).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


@dataclass
class MiddlewareContext:
    """Context passed to middleware during before_model / after_model calls."""

    agent_name: str
    step: int
    run_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseMiddleware(ABC):
    """Abstract base class for all pipeline middleware.

    Each middleware must have a unique `order` value (1–30).
    The Clarification middleware (order=31) MUST always be last.

    INVARIANT-08: Clarification middleware is always the last in the chain (order=31).
    All other middleware order values must be 1–30.
    """

    name: str
    order: int

    @abstractmethod
    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Run before the LLM call. Can modify state, inject context, or short-circuit.

        Args:
            state: Current pipeline state.
            context: Middleware execution context.

        Returns:
            Modified state (or original state if no changes needed).
        """
        ...

    @abstractmethod
    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Run after the LLM call. Can validate output, modify state, or log metrics.

        Args:
            state: Current pipeline state (post-LLM).
            context: Middleware execution context.

        Returns:
            Modified state (or original state if no changes needed).
        """
        ...

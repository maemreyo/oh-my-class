"""Middleware base class for the oh-my-class agent pipeline.

Every middleware implements the BaseMiddleware interface and operates as a
single-concern layer in the chain. Middleware order is fixed (1–22);
Clarification middleware MUST always be last (order=23).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, NotRequired, TypedDict


class MiddlewareState(TypedDict, total=False):
    raw_request: str
    teacher_id: str
    class_info: dict[str, Any]
    run_id: str
    tokens_used: int
    uploaded_files: list[dict[str, Any]]
    teacher_decision: str
    clarification_needed: bool
    artifacts: list[dict[str, Any]]
    metadata: NotRequired[dict[str, Any]]


@dataclass
class MiddlewareContext:
    """Context passed to middleware during before_model / after_model calls."""

    agent_name: str
    step: int
    run_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseMiddleware(ABC):
    """Abstract base class for all pipeline middleware.

    Each middleware must have a unique `order` value (1–22).
    The Clarification middleware (order=23) MUST always be last.

    INVARIANT-08: Clarification middleware is always the last in the chain (order=23).
    All other middleware order values must be 1–22.
    """

    name: str
    order: int

    @abstractmethod
    async def before_model(
        self,
        state: MiddlewareState,
        context: MiddlewareContext,
    ) -> MiddlewareState:
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
        state: MiddlewareState,
        context: MiddlewareContext,
    ) -> MiddlewareState:
        """Run after the LLM call. Can validate output, modify state, or log metrics.

        Args:
            state: Current pipeline state (post-LLM).
            context: Middleware execution context.

        Returns:
            Modified state (or original state if no changes needed).
        """
        ...

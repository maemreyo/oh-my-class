from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from packages.agents.middleware.base import MiddlewareContext

_log = logging.getLogger(__name__)
from packages.agents.middleware.registry import (
    GATE_LAYER_MIDDLEWARE,
    GENERATION_CONTEXT_MIDDLEWARE,
    QUALITY_GATE_CONSOLIDATED_MIDDLEWARE,
    RUN_ENTRY_MIDDLEWARE,
)

if TYPE_CHECKING:
    from packages.agents.middleware.base import BaseMiddleware
    from packages.agents.teaching_pack.nodes import TeachingPackState


async def run_entry_middleware(state: TeachingPackState) -> TeachingPackState:
    return await _run_before_group("setup_contract", RUN_ENTRY_MIDDLEWARE, state, 1)


async def run_generation_context_middleware(
    agent_name: str,
    state: TeachingPackState,
    step: int,
) -> TeachingPackState:
    group = GENERATION_CONTEXT_MIDDLEWARE.get(agent_name, ())
    return await _run_before_group(agent_name, group, state, step)


async def run_gate_middleware(state: TeachingPackState, step: int) -> TeachingPackState:
    return await _run_after_group("teacher_gate", GATE_LAYER_MIDDLEWARE, state, step)


async def run_quality_consolidated_middleware(
    state: TeachingPackState,
    step: int = 9,
) -> TeachingPackState:
    """Run the 6 quality middleware in warning-only mode before render_quality.

    Follows the _run_before_group pattern: creates a MiddlewareContext,
    iterates QUALITY_GATE_CONSOLIDATED_MIDDLEWARE calling before_model() on each,
    and collects any metadata the middleware writes into
    state["quality_scores"]["middleware_warnings"].

    Warning-only: never raises — exceptions are caught and logged so the
    pipeline always continues.
    """
    current = dict(state)
    context = MiddlewareContext(
        agent_name="render_quality",
        step=step,
        run_id=state["run_id"],
    )
    for middleware_type in QUALITY_GATE_CONSOLIDATED_MIDDLEWARE:
        try:
            current = await middleware_type().before_model(current, context)
        except Exception:
            _log.warning(
                "quality_middleware.before_model failed name=%s",
                getattr(middleware_type, "name", middleware_type.__name__),
                exc_info=True,
            )
    quality_scores = dict(current.get("quality_scores", {}))
    quality_scores["middleware_warnings"] = dict(context.metadata) if context.metadata else {}
    current["quality_scores"] = quality_scores
    return cast("TeachingPackState", current)


async def _run_before_group(
    agent_name: str,
    group: tuple[type[BaseMiddleware], ...],
    state: TeachingPackState,
    step: int,
) -> TeachingPackState:
    current = dict(state)
    context = MiddlewareContext(agent_name=agent_name, step=step, run_id=state["run_id"])
    for middleware_type in group:
        current = await middleware_type().before_model(current, context)
    return cast("TeachingPackState", current)


async def _run_after_group(
    agent_name: str,
    group: tuple[type[BaseMiddleware], ...],
    state: TeachingPackState,
    step: int,
) -> TeachingPackState:
    current = dict(state)
    context = MiddlewareContext(agent_name=agent_name, step=step, run_id=state["run_id"])
    for middleware_type in group:
        current = await middleware_type().after_model(current, context)
    return cast("TeachingPackState", current)

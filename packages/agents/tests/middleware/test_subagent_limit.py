"""Tests for subagent_limit middleware."""

from typing import TYPE_CHECKING, cast

import pytest

from packages.agents.middleware.base import MiddlewareContext
from packages.agents.middleware.quality.subagent_limit import (
    SubagentLimitExceededError,
    SubagentLimitMiddleware,
)

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


@pytest.mark.asyncio
async def test_under_limit_passes():
    m = SubagentLimitMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    ctx.metadata["active_subagents"] = 4
    state = cast("OhMyClassState", {})
    result = await m.before_model(state, ctx)
    assert result is state


@pytest.mark.asyncio
async def test_at_limit_raises():
    m = SubagentLimitMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    ctx.metadata["active_subagents"] = 5
    with pytest.raises(SubagentLimitExceededError):
        await m.before_model(cast("OhMyClassState", {}), ctx)


@pytest.mark.asyncio
async def test_over_limit_raises():
    m = SubagentLimitMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    ctx.metadata["active_subagents"] = 10
    with pytest.raises(SubagentLimitExceededError):
        await m.before_model(cast("OhMyClassState", {}), ctx)


@pytest.mark.asyncio
async def test_zero_subagents_passes():
    m = SubagentLimitMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = cast("OhMyClassState", {})
    result = await m.before_model(state, ctx)
    assert result is state


@pytest.mark.asyncio
async def test_after_model_noop():
    m = SubagentLimitMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    result = await m.after_model(cast("OhMyClassState", {}), ctx)
    assert result == {}

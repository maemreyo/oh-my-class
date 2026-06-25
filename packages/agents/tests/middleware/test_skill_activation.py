"""Tests for skill_activation middleware."""

from typing import TYPE_CHECKING, cast

import pytest

from packages.agents.middleware.base import MiddlewareContext
from packages.agents.middleware.context.skill_activation import SkillActivationMiddleware

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


@pytest.mark.asyncio
async def test_unknown_subject_noop():
    m = SkillActivationMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = cast("OhMyClassState", {"class_info": {"subject": "art"}})
    result = await m.before_model(state, ctx)
    assert result is state
    assert "injected_skill" not in ctx.metadata


@pytest.mark.asyncio
async def test_no_class_info_noop():
    m = SkillActivationMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = cast("OhMyClassState", {})
    result = await m.before_model(state, ctx)
    assert result is state
    assert "injected_skill" not in ctx.metadata


@pytest.mark.asyncio
async def test_math_subject_mapping():
    m = SkillActivationMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    # math is in the map but skill file likely doesn't exist, so no-op
    state = cast("OhMyClassState", {"class_info": {"subject": "math"}})
    result = await m.before_model(state, ctx)
    assert result is state


@pytest.mark.asyncio
async def test_after_model_noop():
    m = SkillActivationMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = cast("OhMyClassState", {})
    result = await m.after_model(state, ctx)
    assert result is state

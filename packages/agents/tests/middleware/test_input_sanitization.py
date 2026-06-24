"""Tests for input_sanitization middleware."""

import pytest

from packages.agents.middleware.base import MiddlewareContext
from packages.agents.middleware.safety.input_sanitization import InputSanitizationMiddleware, InputValidationError


@pytest.mark.asyncio
async def test_empty_request_raises():
    m = InputSanitizationMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    with pytest.raises(InputValidationError):
        await m.before_model({"raw_request": ""}, ctx)


@pytest.mark.asyncio
async def test_valid_request_passes():
    m = InputSanitizationMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = {"raw_request": "Create a lesson plan for 3rd grade math"}
    result = await m.before_model(state, ctx)
    assert result is state


@pytest.mark.asyncio
async def test_invalid_grade_raises():
    m = InputSanitizationMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = {"raw_request": "test", "class_info": {"grade": 13}}
    with pytest.raises(InputValidationError):
        await m.before_model(state, ctx)


@pytest.mark.asyncio
async def test_valid_grade_passes():
    m = InputSanitizationMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = {"raw_request": "test", "class_info": {"grade": 5}}
    result = await m.before_model(state, ctx)
    assert result is state


@pytest.mark.asyncio
async def test_kindergarten_grade_passes():
    m = InputSanitizationMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = {"raw_request": "test", "class_info": {"grade": "kindergarten"}}
    result = await m.before_model(state, ctx)
    assert result is state


@pytest.mark.asyncio
async def test_after_model_noop():
    m = InputSanitizationMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = {"raw_request": "test"}
    result = await m.after_model(state, ctx)
    assert result is state

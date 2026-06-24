"""Tests for content_safety middleware."""

import pytest

from packages.agents.middleware.base import MiddlewareContext
from packages.agents.middleware.safety.content_safety import ContentSafetyMiddleware, ContentSafetyError


@pytest.mark.asyncio
async def test_blocked_keyword_raises():
    m = ContentSafetyMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = {"raw_request": "write something with explicit content"}
    with pytest.raises(ContentSafetyError):
        await m.before_model(state, ctx)


@pytest.mark.asyncio
async def test_clean_content_passes():
    m = ContentSafetyMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = {"raw_request": "Create a math lesson for grade 3"}
    result = await m.before_model(state, ctx)
    assert result is state


@pytest.mark.asyncio
async def test_after_model_blocked_artifact_raises():
    m = ContentSafetyMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = {"artifacts": [{"content": "This has nsfw material"}]}
    with pytest.raises(ContentSafetyError):
        await m.after_model(state, ctx)


@pytest.mark.asyncio
async def test_after_model_clean_artifact_passes():
    m = ContentSafetyMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = {"artifacts": [{"content": "Great lesson plan for students"}]}
    result = await m.after_model(state, ctx)
    assert result is state


@pytest.mark.asyncio
async def test_nsfw_keyword_blocked():
    m = ContentSafetyMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = {"raw_request": "This is nsfw"}
    with pytest.raises(ContentSafetyError):
        await m.before_model(state, ctx)

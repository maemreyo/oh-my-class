"""Tests for skill_activation middleware."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from packages.agents.middleware.base import MiddlewareContext, MiddlewareState
from packages.agents.middleware.context.skill_activation import SkillActivationMiddleware


# ── No-op paths ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unknown_subject_noop():
    m = SkillActivationMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = MiddlewareState(class_info={"subject": "art"})
    result = await m.before_model(state, ctx)
    assert result is state
    assert "injected_skill" not in ctx.metadata


@pytest.mark.asyncio
async def test_no_class_info_noop():
    m = SkillActivationMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = MiddlewareState()
    result = await m.before_model(state, ctx)
    assert result is state
    assert "injected_skill" not in ctx.metadata


@pytest.mark.asyncio
async def test_empty_subject_noop():
    m = SkillActivationMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = MiddlewareState(class_info={"subject": ""})
    result = await m.before_model(state, ctx)
    assert result is state
    assert "injected_skill" not in ctx.metadata


# ── Subject → skill-name mapping via SkillLoader ─────────────────────────────


@pytest.mark.asyncio
async def test_math_subject_uses_loader():
    """Math subject resolves to 'ccss_math' via SkillLoader."""
    loader = MagicMock()
    loader.load_skill.return_value = "# CCSS Math Skill"
    m = SkillActivationMiddleware(loader=loader)
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = MiddlewareState(class_info={"subject": "math"})
    result = await m.before_model(state, ctx)
    assert result is state
    loader.load_skill.assert_called_once_with("ccss_math")
    assert ctx.metadata["injected_skill"] == "# CCSS Math Skill"


@pytest.mark.asyncio
async def test_ela_subject_uses_loader():
    """ELA subject resolves to 'ccss_ela' via SkillLoader."""
    loader = MagicMock()
    loader.load_skill.return_value = "# CCSS ELA Skill"
    m = SkillActivationMiddleware(loader=loader)
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = MiddlewareState(class_info={"subject": "ela"})
    await m.before_model(state, ctx)
    loader.load_skill.assert_called_once_with("ccss_ela")
    assert ctx.metadata["injected_skill"] == "# CCSS ELA Skill"


@pytest.mark.asyncio
async def test_english_subject_maps_to_ela():
    """English subject maps to 'ccss_ela' (alias for ela)."""
    loader = MagicMock()
    loader.load_skill.return_value = "# ELA content"
    m = SkillActivationMiddleware(loader=loader)
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = MiddlewareState(class_info={"subject": "english"})
    await m.before_model(state, ctx)
    loader.load_skill.assert_called_once_with("ccss_ela")


@pytest.mark.asyncio
async def test_science_subject_maps_to_math():
    """Science subject maps to 'ccss_math' skill."""
    loader = MagicMock()
    loader.load_skill.return_value = "# Math content"
    m = SkillActivationMiddleware(loader=loader)
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = MiddlewareState(class_info={"subject": "science"})
    await m.before_model(state, ctx)
    loader.load_skill.assert_called_once_with("ccss_math")


@pytest.mark.asyncio
async def test_case_insensitive_subject():
    """Subject lookup should be case-insensitive."""
    loader = MagicMock()
    loader.load_skill.return_value = "# content"
    m = SkillActivationMiddleware(loader=loader)
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = MiddlewareState(class_info={"subject": "MATH"})
    await m.before_model(state, ctx)
    loader.load_skill.assert_called_once_with("ccss_math")


# ── Error handling ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_loader_key_error_handled():
    """KeyError from SkillLoader (unregistered skill) — skip injection."""
    loader = MagicMock()
    loader.load_skill.side_effect = KeyError("not registered")
    m = SkillActivationMiddleware(loader=loader)
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = MiddlewareState(class_info={"subject": "math"})
    result = await m.before_model(state, ctx)
    assert result is state
    assert "injected_skill" not in ctx.metadata


@pytest.mark.asyncio
async def test_loader_file_not_found_handled():
    """FileNotFoundError from SkillLoader — skip injection."""
    loader = MagicMock()
    loader.load_skill.side_effect = FileNotFoundError("missing file")
    m = SkillActivationMiddleware(loader=loader)
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = MiddlewareState(class_info={"subject": "math"})
    result = await m.before_model(state, ctx)
    assert result is state
    assert "injected_skill" not in ctx.metadata


# ── Default loader ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_default_loader_is_skill_loader():
    """Default constructor creates a real SkillLoader."""
    from packages.agents.skills.loader import SkillLoader

    m = SkillActivationMiddleware()
    assert isinstance(m._loader, SkillLoader)


# ── after_model ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_after_model_noop():
    m = SkillActivationMiddleware()
    ctx = MiddlewareContext(agent_name="test", step=1, run_id="r1")
    state = MiddlewareState()
    result = await m.after_model(state, ctx)
    assert result is state

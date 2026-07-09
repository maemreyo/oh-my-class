"""Tests for the quality consolidated middleware wiring into render_quality.

TDD red tests — these should fail until the implementation is wired.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from packages.agents.teaching_pack.middleware_runtime import (
    run_quality_consolidated_middleware,
)
from packages.agents.teaching_pack.nodes import (
    TeachingPackState,
    _teacher_approval,
)


def _make_state(**overrides: Any) -> TeachingPackState:
    base: dict[str, Any] = {
        "run_id": "run-mw-test",
        "quality_scores": {},
        "artifacts": [],
    }
    base.update(overrides)
    return TeachingPackState(**base)


class TestRunQualityConsolidatedMiddleware:
    """Test the run_quality_consolidated_middleware() function."""

    @pytest.mark.anyio
    async def test_function_exists_and_is_callable(self) -> None:
        """Given: the function is importable
        When: we call it with a valid state
        Then: it returns a TeachingPackState without error
        """
        result = await run_quality_consolidated_middleware(_make_state())
        assert "run_id" in result

    @pytest.mark.anyio
    async def test_iterates_all_six_quality_middleware_before_model(self) -> None:
        """Given: all 6 quality middleware are registered
        When: run_quality_consolidated_middleware runs
        Then: each middleware's before_model is called exactly once
        """
        mock_instances: list[Any] = []
        fake_group = tuple(
            type(f"Mw{i}", (), {
                "name": f"fake_mw_{i}",
                "order": i,
                "before_model": AsyncMock(side_effect=lambda s, c: s),
                "after_model": AsyncMock(side_effect=lambda s, c: s),
            })
            for i in range(6)
        )

        for mw_type in fake_group:
            instance = mw_type()
            mock_instances.append(instance)
            mw_type.return_value = instance  # type: ignore[attr-defined]

        with patch(
            "packages.agents.teaching_pack.middleware_runtime.QUALITY_GATE_CONSOLIDATED_MIDDLEWARE",
            fake_group,
        ):
            await run_quality_consolidated_middleware(_make_state())

        for instance in mock_instances:
            instance.before_model.assert_called_once()

    @pytest.mark.anyio
    async def test_collects_context_metadata_into_middleware_warnings(self) -> None:
        """Given: middleware writes warnings to context.metadata
        When: run_quality_consolidated_middleware runs
        Then: state["quality_scores"]["middleware_warnings"] contains the warnings
        """

        class WarningMiddleware:
            name = "warning_mw"
            order = 1

            async def before_model(self, state, context):
                context.metadata["curriculum_alignment_warning"] = (
                    "Artifacts may not align with Standard X"
                )
                return state

            async def after_model(self, state, context):
                return state

        fake_group = (WarningMiddleware,)

        with patch(
            "packages.agents.teaching_pack.middleware_runtime.QUALITY_GATE_CONSOLIDATED_MIDDLEWARE",
            fake_group,
        ):
            result = await run_quality_consolidated_middleware(_make_state())

        warnings = result.get("quality_scores", {}).get("middleware_warnings", {})
        assert "curriculum_alignment_warning" in warnings
        assert "Standard X" in warnings["curriculum_alignment_warning"]

    @pytest.mark.anyio
    async def test_never_blocks_on_middleware_exception(self) -> None:
        """Given: a middleware raises during before_model
        When: run_quality_consolidated_middleware runs
        Then: the exception is caught, pipeline continues without blocking
        """

        class FailingMiddleware:
            name = "failing"
            order = 1

            async def before_model(self, state, context):
                raise RuntimeError("boom")

            async def after_model(self, state, context):
                return state

        class GoodMiddleware:
            name = "good"
            order = 2

            async def before_model(self, state, context):
                context.metadata["good_check"] = "passed"
                return state

            async def after_model(self, state, context):
                return state

        fake_group = (FailingMiddleware, GoodMiddleware)

        with patch(
            "packages.agents.teaching_pack.middleware_runtime.QUALITY_GATE_CONSOLIDATED_MIDDLEWARE",
            fake_group,
        ):
            # Should NOT raise — warning-only mode
            result = await run_quality_consolidated_middleware(_make_state())

        assert result["run_id"] == "run-mw-test"

    @pytest.mark.anyio
    async def test_empty_metadata_produces_empty_warnings(self) -> None:
        """Given: middleware produces no metadata
        When: run_quality_consolidated_middleware runs
        Then: middleware_warnings is an empty dict
        """
        result = await run_quality_consolidated_middleware(_make_state())
        warnings = result.get("quality_scores", {}).get("middleware_warnings", {})
        assert warnings == {}


class TestRenderQualityMiddlewareWiring:
    """Test that _render_quality calls the middleware and preserves warnings."""

    @pytest.mark.anyio
    async def test_render_quality_calls_consolidated_middleware_before_quality(self) -> None:
        """Given: _render_quality is called
        When: it runs
        Then: run_quality_consolidated_middleware is called before render_quality
        """
        call_order: list[str] = []

        async def fake_middleware(state):
            call_order.append("middleware")
            return state

        async def fake_render_quality(state, quality_gate=None):
            call_order.append("render_quality")
            return {
                "run_id": state["run_id"],
                "quality_scores": {"overall": 8.0, "passed": True},
            }

        from packages.agents.teaching_pack import nodes

        with (
            patch(
                "packages.agents.teaching_pack.nodes._run_quality_middleware",
                fake_middleware,
            ),
            patch(
                "packages.agents.teaching_pack.nodes.render_quality",
                fake_render_quality,
            ),
        ):
            await nodes._render_quality(_make_state())

        assert call_order == ["middleware", "render_quality"]

    @pytest.mark.anyio
    async def test_middleware_warnings_survive_render_quality_overwrite(self) -> None:
        """Given: middleware collects warnings into quality_scores
        When: render_quality overwrites quality_scores
        Then: middleware_warnings are preserved in the merged result
        """

        async def fake_middleware(state):
            scores = dict(state.get("quality_scores", {}))
            scores["middleware_warnings"] = {"bias_check": "flagged"}
            return TeachingPackState(**{**state, "quality_scores": scores})

        async def fake_render_quality(state, quality_gate=None):
            return {
                "run_id": state["run_id"],
                "quality_scores": {"overall": 8.0, "passed": True},
            }

        from packages.agents.teaching_pack import nodes

        with (
            patch(
                "packages.agents.teaching_pack.nodes._run_quality_middleware",
                fake_middleware,
            ),
            patch(
                "packages.agents.teaching_pack.nodes.render_quality",
                fake_render_quality,
            ),
        ):
            result = await nodes._render_quality(_make_state())

        warnings = result.get("quality_scores", {}).get("middleware_warnings", {})
        assert warnings == {"bias_check": "flagged"}
        assert result["quality_scores"]["overall"] == 8.0


class TestTeacherApprovalMiddlewareWarnings:
    """Test that _teacher_approval reads middleware_warnings into gate_payload."""

    def test_gate_payload_includes_middleware_warnings(self, monkeypatch) -> None:
        """Given: quality_scores contains middleware_warnings
        When: teacher_approval builds gate_payload
        Then: middleware_warnings appear in gate_payload
        """
        captured = {}

        def fake_interrupt(payload):
            captured.update(payload)
            return {"action": "approve"}

        monkeypatch.setattr("langgraph.types.interrupt", fake_interrupt)

        _teacher_approval(TeachingPackState(
            run_id="run-mw-gate",
            quality_scores={
                "overall": 8.0,
                "passed": True,
                "middleware_warnings": {
                    "curriculum_alignment_warning": "May not align",
                },
            },
        ))

        assert "middleware_warnings" in captured
        assert captured["middleware_warnings"]["curriculum_alignment_warning"] == "May not align"

    def test_gate_payload_omits_middleware_warnings_when_empty(self, monkeypatch) -> None:
        """Given: no middleware_warnings in quality_scores
        When: teacher_approval builds gate_payload
        Then: middleware_warnings key is absent
        """
        captured = {}

        def fake_interrupt(payload):
            captured.update(payload)
            return {"action": "approve"}

        monkeypatch.setattr("langgraph.types.interrupt", fake_interrupt)

        _teacher_approval(TeachingPackState(
            run_id="run-no-mw",
            quality_scores={"overall": 8.0, "passed": True},
        ))

        assert "middleware_warnings" not in captured

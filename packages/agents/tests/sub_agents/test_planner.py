"""Tests for planner agent and ResearchBundle contract."""

import json
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, patch

import pytest

from common.contracts.lesson_plan import LessonPlan
from common.contracts.research_bundle import ResearchBundle, ResearchSource

if TYPE_CHECKING:
    from packages.agents.sub_agents.planner.state import PlannerState

# ── ResearchBundle ────────────────────────────────────────────────────────────

class TestResearchSource:
    def test_valid_source(self):
        source = ResearchSource(
            title="Encyclopedia of Science",
            credibility_score=0.9,
            verification_status="VERIFIED",
        )
        assert source.title == "Encyclopedia of Science"
        assert source.url is None

    def test_source_with_url(self):
        source = ResearchSource(
            title="Wikipedia",
            url="https://en.wikipedia.org/wiki/Photosynthesis",
            credibility_score=0.7,
            verification_status="MODIFIED",
        )
        assert source.url is not None

    def test_credibility_score_bounds(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ResearchSource(title="X", credibility_score=1.5, verification_status="VERIFIED")
        with pytest.raises(ValidationError):
            ResearchSource(title="X", credibility_score=-0.1, verification_status="VERIFIED")

    def test_verification_status_enum(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ResearchSource(title="X", credibility_score=0.5, verification_status="INVALID")  # pyright: ignore[reportArgumentType]

    def test_all_verification_statuses(self):
        for status in ("VERIFIED", "MODIFIED", "REMOVED", "UNCERTAIN"):
            src = ResearchSource(title="T", credibility_score=0.5, verification_status=status)
            assert src.verification_status == status


class TestResearchBundle:
    def _make_source(self, title: str = "Source", score: float = 0.9) -> dict[str, Any]:
        return {"title": title, "credibility_score": score, "verification_status": "VERIFIED"}

    def test_valid_with_2_sources(self):
        data = {
            "topic": "Photosynthesis",
            "sources": [self._make_source("S1"), self._make_source("S2")],
        }
        bundle = ResearchBundle.model_validate(data)
        assert len(bundle.sources) == 2

    def test_invalid_with_1_source(self):
        from pydantic import ValidationError
        data = {
            "topic": "Photosynthesis",
            "sources": [self._make_source("S1")],
        }
        with pytest.raises(ValidationError):
            ResearchBundle.model_validate(data)

    def test_invalid_with_0_sources(self):
        from pydantic import ValidationError
        data = {"topic": "Photosynthesis", "sources": []}
        with pytest.raises(ValidationError):
            ResearchBundle.model_validate(data)

    def test_default_policy_is_standard(self):
        data = {
            "topic": "Photosynthesis",
            "sources": [self._make_source("S1"), self._make_source("S2")],
        }
        bundle = ResearchBundle.model_validate(data)
        assert bundle.research_policy == "standard"

    def test_explicit_policy_basic(self):
        data = {
            "topic": "Photosynthesis",
            "sources": [self._make_source("S1"), self._make_source("S2")],
            "research_policy": "basic",
        }
        bundle = ResearchBundle.model_validate(data)
        assert bundle.research_policy == "basic"

    def test_explicit_policy_rigorous(self):
        data = {
            "topic": "Photosynthesis",
            "sources": [self._make_source(f"S{i}") for i in range(10)],
            "research_policy": "rigorous",
        }
        bundle = ResearchBundle.model_validate(data)
        assert bundle.research_policy == "rigorous"

    def test_invalid_policy(self):
        from pydantic import ValidationError
        data = {
            "topic": "Photosynthesis",
            "sources": [self._make_source("S1"), self._make_source("S2")],
            "research_policy": "extreme",
        }
        with pytest.raises(ValidationError):
            ResearchBundle.model_validate(data)

    def test_key_findings_default_empty(self):
        data = {
            "topic": "T",
            "sources": [self._make_source("S1"), self._make_source("S2")],
        }
        bundle = ResearchBundle.model_validate(data)
        assert bundle.key_findings == []

    def test_key_findings_populated(self):
        data = {
            "topic": "T",
            "sources": [self._make_source("S1"), self._make_source("S2")],
            "key_findings": ["Finding A", "Finding B"],
        }
        bundle = ResearchBundle.model_validate(data)
        assert len(bundle.key_findings) == 2

    def test_cross_references_default_empty(self):
        data = {
            "topic": "T",
            "sources": [self._make_source("S1"), self._make_source("S2")],
        }
        bundle = ResearchBundle.model_validate(data)
        assert bundle.cross_references == []

    def test_topic_min_length(self):
        from pydantic import ValidationError
        data = {
            "topic": "",
            "sources": [self._make_source("S1"), self._make_source("S2")],
        }
        with pytest.raises(ValidationError):
            ResearchBundle.model_validate(data)

    def test_exported_from_contracts(self):
        from common.contracts import ResearchBundle as ResearchBundleAlias
        from common.contracts import ResearchSource as ResearchSourceAlias
        assert ResearchBundleAlias is ResearchBundle
        assert ResearchSourceAlias is ResearchSource


# ── Planner Agent ─────────────────────────────────────────────────────────────

def _make_llm_mock(
    return_value: str | None = None,
    side_effect: Exception | None = None,
) -> AsyncMock:
    if side_effect is not None:
        return AsyncMock(side_effect=side_effect)
    return AsyncMock(return_value=return_value)


VALID_PLAN_JSON = json.dumps({
    "topic": "Photosynthesis",
    "grade_level": "Grade 5",
    "subject": "science",
    "duration_minutes": 45,
    "learning_objectives": [
        {"description": "Understand photosynthesis", "bloom_level": "understand"},
        {"description": "Apply knowledge to experiments", "bloom_level": "apply"},
    ],
})

VALID_PLAN_WRAPPED = f"```json\n{VALID_PLAN_JSON}\n```"
VALID_PLAN_GENERIC_FENCE = f"```\n{VALID_PLAN_JSON}\n```"


class TestPlannerAgent:
    def _make_state(self, **overrides) -> dict[str, Any]:
        base = {
            "raw_request": "Teach photosynthesis to grade 5",
            "class_info": {"grade": 5, "subject": "science", "student_count": 30},
            "run_id": "test-run-001",
            "current_step": 3,
        }
        base.update(overrides)
        return base

    @pytest.mark.asyncio
    async def test_returns_valid_lesson_plan(self):
        from packages.agents.sub_agents.planner.nodes import planner_node as design_lesson_plan

        mock_llm = _make_llm_mock(return_value=VALID_PLAN_WRAPPED)
        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            result = await design_lesson_plan(cast("PlannerState", self._make_state()))

        assert "lesson_plan" in result
        plan = LessonPlan.model_validate(result["lesson_plan"])
        assert plan.topic == "Photosynthesis"

    @pytest.mark.asyncio
    async def test_parses_json_code_fence(self):
        from packages.agents.sub_agents.planner.nodes import planner_node as design_lesson_plan

        mock_llm = _make_llm_mock(return_value=VALID_PLAN_WRAPPED)
        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            result = await design_lesson_plan(cast("PlannerState", self._make_state()))

        assert result["lesson_plan"]["topic"] == "Photosynthesis"

    @pytest.mark.asyncio
    async def test_parses_generic_code_fence(self):
        from packages.agents.sub_agents.planner.nodes import planner_node as design_lesson_plan

        mock_llm = _make_llm_mock(return_value=VALID_PLAN_GENERIC_FENCE)
        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            result = await design_lesson_plan(cast("PlannerState", self._make_state()))

        assert "lesson_plan" in result

    @pytest.mark.asyncio
    async def test_parses_bare_json(self):
        from packages.agents.sub_agents.planner.nodes import planner_node as design_lesson_plan

        mock_llm = _make_llm_mock(return_value=VALID_PLAN_JSON)
        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            result = await design_lesson_plan(cast("PlannerState", self._make_state()))

        assert "lesson_plan" in result

    @pytest.mark.asyncio
    async def test_raises_value_error_on_invalid_json(self):
        from packages.agents.sub_agents.planner.nodes import planner_node as design_lesson_plan

        mock_llm = _make_llm_mock(return_value="not json at all")
        with (
            patch("packages.agents.llm.complete_json_chat", mock_llm),
            pytest.raises(ValueError, match="Planner agent failed"),
        ):
            await design_lesson_plan(cast("PlannerState", self._make_state()))

    @pytest.mark.asyncio
    async def test_raises_value_error_on_llm_error(self):
        from packages.agents.sub_agents.planner.nodes import planner_node as design_lesson_plan

        mock_llm = _make_llm_mock(side_effect=RuntimeError("API timeout"))
        with (
            patch("packages.agents.llm.complete_json_chat", mock_llm),
            pytest.raises(ValueError, match="Planner agent failed"),
        ):
            await design_lesson_plan(cast("PlannerState", self._make_state()))

    @pytest.mark.asyncio
    async def test_raises_value_error_on_schema_mismatch(self):
        from packages.agents.sub_agents.planner.nodes import planner_node as design_lesson_plan

        bad_plan = json.dumps({"topic": "T"})  # Missing required fields
        mock_llm = _make_llm_mock(return_value=bad_plan)
        with (
            patch("packages.agents.llm.complete_json_chat", mock_llm),
            pytest.raises(ValueError, match="Planner agent failed"),
        ):
            await design_lesson_plan(cast("PlannerState", self._make_state()))

    @pytest.mark.asyncio
    async def test_state_missing_class_info_fields_uses_defaults(self):
        from packages.agents.sub_agents.planner.nodes import planner_node as design_lesson_plan

        mock_llm = _make_llm_mock(return_value=VALID_PLAN_WRAPPED)
        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            result = await design_lesson_plan(cast("PlannerState", self._make_state(class_info={})))

        mock_llm.assert_awaited_once()
        assert "lesson_plan" in result

    @pytest.mark.asyncio
    async def test_calls_llm_with_correct_model(self):
        from packages.agents.sub_agents.planner.nodes import planner_node as design_lesson_plan

        mock_llm = _make_llm_mock(return_value=VALID_PLAN_WRAPPED)
        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            await design_lesson_plan(cast("PlannerState", self._make_state()))

        call_kwargs = mock_llm.call_args
        assert call_kwargs.kwargs["model"] == "4omc"

    @pytest.mark.asyncio
    async def test_metadata_tags_include_run_id(self):
        from packages.agents.sub_agents.planner.nodes import planner_node as design_lesson_plan

        mock_llm = _make_llm_mock(return_value=VALID_PLAN_WRAPPED)
        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            await design_lesson_plan(cast("PlannerState", self._make_state(run_id="my-run-xyz")))

        tags = mock_llm.call_args.kwargs["tags"]
        assert any("my-run-xyz" in t for t in tags)
        assert any("agent:planner" in t for t in tags)
        assert any("pipeline:oh-my-class" in t for t in tags)

    @pytest.mark.asyncio
    async def test_lesson_plan_has_correct_bloom_levels(self):
        from packages.agents.sub_agents.planner.nodes import planner_node as design_lesson_plan

        mock_llm = _make_llm_mock(return_value=VALID_PLAN_WRAPPED)
        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            result = await design_lesson_plan(cast("PlannerState", self._make_state()))

        plan = LessonPlan.model_validate(result["lesson_plan"])
        levels = {obj.bloom_level for obj in plan.learning_objectives}
        assert len(levels) >= 2

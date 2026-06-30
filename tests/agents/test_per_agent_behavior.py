"""Per-agent behavior tests. Marked real_llm — run nightly.

These are integration tests that verify agent node behavior with a real LLM
via 9router. The scaffold is wired here; actual assertions are completed in
te-005 when the golden dataset exists.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.real_llm


class TestPlannerBehavior:
    """Tests for planner_node output shape and contract validity."""

    async def test_planner_returns_lesson_plan_contract(self, real_llm_config, real_db_session):
        pytest.skip("Scaffold: wire up in te-005 when golden dataset exists")


class TestResearcherBehavior:
    """Tests for researcher_node output shape."""

    async def test_researcher_returns_research_bundle(self, real_llm_config, real_db_session):
        pytest.skip("Scaffold: wire up in te-005 when golden dataset exists")


class TestContentCreatorBehavior:
    """Tests for content_creator_node output shape and contract validity."""

    async def test_content_creator_returns_artifact_workflow_handoff(
        self, real_llm_config, real_db_session
    ):
        pytest.skip("Scaffold: wire up in te-005 when golden dataset exists")


class TestReviewerBehavior:
    """Tests for reviewer_node quality pass/fail decision."""

    async def test_reviewer_approves_quality_artifact(self, real_llm_config, real_db_session):
        pytest.skip("Scaffold: wire up in te-005 when golden dataset exists")

    async def test_reviewer_rejects_low_quality_artifact(self, real_llm_config, real_db_session):
        pytest.skip("Scaffold: wire up in te-005 when golden dataset exists")


class TestUnitPlannerBehavior:
    """Tests for unit_planner_node topic-decomposition output."""

    async def test_unit_planner_returns_lesson_sequence(self, real_llm_config, real_db_session):
        pytest.skip("Scaffold: wire up in te-005 when golden dataset exists")


class TestSequenceCriticBehavior:
    """Tests for sequence_critic_node ordering and coherence."""

    async def test_sequence_critic_flags_disordered_lessons(
        self, real_llm_config, real_db_session
    ):
        pytest.skip("Scaffold: wire up in te-005 when golden dataset exists")

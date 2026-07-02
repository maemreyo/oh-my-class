"""Stage seam / handoff contract tests.

Asserts that the producer-output validates as the consumer-input contract at
each stage boundary (single-lesson path). A deliberately corrupted handoff
must be caught (fail-closed). No LLM required — synthetic state only.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError
from tests.scenarios import scenario_by_key

from common.contracts.seam_contracts import (
    ArtifactWorkflowHandoff,
    PlannerHandoff,
    ResearcherHandoff,
)


def _valid_lesson_plan() -> dict[str, object]:
    scenario = scenario_by_key("math_vn")
    return {
        "topic": scenario.class_info["topic"],
        "learning_objectives": [
            {"description": "Understand what a fraction represents", "bloom_level": "understand"}
        ],
        "grade_level": f"Grade {scenario.class_info['grade']}",
        "subject": scenario.class_info["subject"],
        "duration_minutes": 45,
    }


def _valid_research_brief() -> dict[str, object]:
    return {
        "topic": "Fractions",
        "sources": [
            {"title": "Khan Academy", "credibility_score": 0.9, "verification_status": "VERIFIED"}
        ],
        "research_policy": "standard",
    }


def _valid_artifact(artifact_id: str = "art-1") -> dict[str, object]:
    return {"artifact_id": artifact_id, "artifact_type": "lesson", "content": "body text"}


class TestPlannerHandoff:
    """planning_blueprint → post_blueprint_research seam."""

    def test_planner_handoff_parses_required_fields(self):
        handoff = PlannerHandoff.model_validate({"lesson_plan": _valid_lesson_plan()})
        assert handoff.lesson_plan["topic"] == scenario_by_key("math_vn").class_info["topic"]

    def test_missing_topic_is_rejected(self):
        plan = {k: v for k, v in _valid_lesson_plan().items() if k != "topic"}
        with pytest.raises(ValidationError):
            PlannerHandoff(lesson_plan=plan)

    def test_missing_objectives_is_rejected(self):
        plan = {k: v for k, v in _valid_lesson_plan().items() if k != "learning_objectives"}
        with pytest.raises(ValidationError):
            PlannerHandoff(lesson_plan=plan)

    def test_empty_dict_is_rejected(self):
        with pytest.raises(ValidationError):
            PlannerHandoff(lesson_plan={})

    def test_error_names_planning_blueprint_seam(self):
        with pytest.raises(ValidationError) as exc_info:
            PlannerHandoff(lesson_plan={})
        assert "planning_blueprint" in str(exc_info.value)


class TestResearcherHandoff:
    """post_blueprint_research → artifact_workflow seam."""

    def test_valid_handoff_passes(self):
        handoff = ResearcherHandoff(
            lesson_plan=_valid_lesson_plan(),
            research_brief=_valid_research_brief(),
        )
        assert handoff.research_brief["topic"] == "Fractions"

    def test_empty_sources_is_rejected(self):
        brief = {**_valid_research_brief(), "sources": []}
        with pytest.raises(ValidationError):
            ResearcherHandoff(lesson_plan=_valid_lesson_plan(), research_brief=brief)

    def test_missing_sources_is_rejected(self):
        brief = {"topic": "Fractions"}
        with pytest.raises(ValidationError):
            ResearcherHandoff(lesson_plan=_valid_lesson_plan(), research_brief=brief)

    def test_degraded_plan_without_topic_is_rejected(self):
        degraded = {"grade_level": "Grade 5"}  # topic dropped between stages
        with pytest.raises(ValidationError):
            ResearcherHandoff(lesson_plan=degraded, research_brief=_valid_research_brief())

    def test_error_names_post_blueprint_research_seam(self):
        brief = {**_valid_research_brief(), "sources": []}
        with pytest.raises(ValidationError) as exc_info:
            ResearcherHandoff(lesson_plan=_valid_lesson_plan(), research_brief=brief)
        assert "post_blueprint_research" in str(exc_info.value)


class TestArtifactWorkflowHandoff:
    """artifact_workflow → render_quality seam."""

    def test_valid_artifacts_pass(self):
        handoff = ArtifactWorkflowHandoff(
            artifacts=[_valid_artifact("a1"), _valid_artifact("a2")]
        )
        assert len(handoff.artifacts) == 2

    def test_empty_artifacts_is_rejected(self):
        with pytest.raises(ValidationError):
            ArtifactWorkflowHandoff(artifacts=[])

    def test_artifact_without_id_is_rejected(self):
        bad = {"artifact_type": "lesson", "content": "no id here"}
        with pytest.raises(ValidationError):
            ArtifactWorkflowHandoff(artifacts=[bad])

    def test_mixed_valid_invalid_is_rejected(self):
        good = _valid_artifact("a1")
        bad = {"artifact_type": "worksheet", "content": "y"}
        with pytest.raises(ValidationError):
            ArtifactWorkflowHandoff(artifacts=[good, bad])

    def test_error_names_artifact_workflow_seam(self):
        with pytest.raises(ValidationError) as exc_info:
            ArtifactWorkflowHandoff(artifacts=[])
        assert "artifact_workflow" in str(exc_info.value)

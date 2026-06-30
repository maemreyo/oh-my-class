"""Issue agent-interaction/001: seam-contract integration tests.

Verifies that a deliberately malformed handoff at each stage seam raises
ValidationError (fail-closed) rather than silently passing bad data forward.
No LLM; synthetic state only.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.seam_contracts import (
    ArtifactWorkflowHandoff,
    PlannerHandoff,
    ResearcherHandoff,
)


def _minimal_valid_plan() -> dict:
    return {
        "topic": "Photosynthesis",
        "learning_objectives": [{"description": "Define it", "bloom_level": "remember"}],
        "grade_level": "Grade 5",
        "subject": "science",
        "duration_minutes": 45,
    }


def _minimal_valid_brief() -> dict:
    return {
        "topic": "Photosynthesis",
        "sources": [{"title": "Wikipedia", "credibility_score": 0.6, "verification_status": "VERIFIED"}],
        "research_policy": "standard",
    }


def _minimal_valid_artifact(artifact_id: str = "art-1") -> dict:
    return {"artifact_id": artifact_id, "artifact_type": "lesson", "content": "body"}


class TestPlannerHandoffAtSeam:
    """Seam: planning_blueprint → post_blueprint_research."""

    def test_valid_plan_passes_seam(self):
        PlannerHandoff(lesson_plan=_minimal_valid_plan())

    def test_planner_returning_none_fails_closed(self):
        with pytest.raises((ValidationError, TypeError)):
            PlannerHandoff(lesson_plan=None)  # type: ignore[arg-type]

    def test_planner_returning_empty_dict_fails_closed(self):
        with pytest.raises(ValidationError):
            PlannerHandoff(lesson_plan={})

    def test_planner_omitting_topic_fails_closed(self):
        plan = {k: v for k, v in _minimal_valid_plan().items() if k != "topic"}
        with pytest.raises(ValidationError):
            PlannerHandoff(lesson_plan=plan)

    def test_planner_omitting_objectives_fails_closed(self):
        plan = {k: v for k, v in _minimal_valid_plan().items() if k != "learning_objectives"}
        with pytest.raises(ValidationError):
            PlannerHandoff(lesson_plan=plan)

    def test_error_message_names_seam(self):
        with pytest.raises(ValidationError) as exc_info:
            PlannerHandoff(lesson_plan={})
        assert "planning_blueprint" in str(exc_info.value)


class TestResearcherHandoffAtSeam:
    """Seam: post_blueprint_research → artifact_workflow."""

    def test_valid_handoff_passes_seam(self):
        ResearcherHandoff(lesson_plan=_minimal_valid_plan(), research_brief=_minimal_valid_brief())

    def test_empty_sources_fails_closed(self):
        brief = {**_minimal_valid_brief(), "sources": []}
        with pytest.raises(ValidationError):
            ResearcherHandoff(lesson_plan=_minimal_valid_plan(), research_brief=brief)

    def test_missing_sources_fails_closed(self):
        brief = {"topic": "Photosynthesis"}
        with pytest.raises(ValidationError):
            ResearcherHandoff(lesson_plan=_minimal_valid_plan(), research_brief=brief)

    def test_plan_degraded_between_stages_fails_closed(self):
        degraded_plan = {"grade_level": "Grade 5"}  # topic missing
        with pytest.raises(ValidationError):
            ResearcherHandoff(lesson_plan=degraded_plan, research_brief=_minimal_valid_brief())

    def test_error_message_names_seam(self):
        brief = {**_minimal_valid_brief(), "sources": []}
        with pytest.raises(ValidationError) as exc_info:
            ResearcherHandoff(lesson_plan=_minimal_valid_plan(), research_brief=brief)
        assert "post_blueprint_research" in str(exc_info.value)


class TestArtifactWorkflowHandoffAtSeam:
    """Seam: artifact_workflow → render_quality."""

    def test_valid_artifacts_pass_seam(self):
        artifacts = [_minimal_valid_artifact("a1"), _minimal_valid_artifact("a2")]
        ArtifactWorkflowHandoff(artifacts=artifacts)

    def test_empty_artifacts_fails_closed(self):
        with pytest.raises(ValidationError):
            ArtifactWorkflowHandoff(artifacts=[])

    def test_artifact_without_id_fails_closed(self):
        bad = {"artifact_type": "lesson", "content": "x"}
        with pytest.raises(ValidationError):
            ArtifactWorkflowHandoff(artifacts=[bad])

    def test_one_valid_one_invalid_fails_closed(self):
        ok = _minimal_valid_artifact("a1")
        bad = {"artifact_type": "worksheet", "content": "y"}
        with pytest.raises(ValidationError):
            ArtifactWorkflowHandoff(artifacts=[ok, bad])

    def test_error_message_names_seam(self):
        with pytest.raises(ValidationError) as exc_info:
            ArtifactWorkflowHandoff(artifacts=[])
        assert "artifact_workflow" in str(exc_info.value)

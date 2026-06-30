"""Issue agent-interaction/001: seam-contract model unit tests.

Each model rejects missing / malformed required fields (fail-closed).
No LLM; pure Pydantic validation.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.seam_contracts import (
    ArtifactWorkflowHandoff,
    PlannerHandoff,
    ResearcherHandoff,
)


# ── PlannerHandoff ────────────────────────────────────────────────────────────

class TestPlannerHandoff:
    def _valid_plan(self) -> dict:
        return {
            "topic": "Photosynthesis",
            "learning_objectives": [
                {"description": "Define photosynthesis", "bloom_level": "remember"},
            ],
        }

    def test_accepts_valid_lesson_plan(self):
        PlannerHandoff(lesson_plan=self._valid_plan())

    def test_rejects_empty_lesson_plan(self):
        with pytest.raises(ValidationError, match="topic"):
            PlannerHandoff(lesson_plan={})

    def test_rejects_missing_topic(self):
        plan = self._valid_plan()
        del plan["topic"]
        with pytest.raises(ValidationError, match="topic"):
            PlannerHandoff(lesson_plan=plan)

    def test_rejects_empty_topic_string(self):
        plan = {**self._valid_plan(), "topic": ""}
        with pytest.raises(ValidationError, match="topic"):
            PlannerHandoff(lesson_plan=plan)

    def test_rejects_missing_learning_objectives(self):
        plan = {"topic": "Photosynthesis"}
        with pytest.raises(ValidationError, match="learning_objectives"):
            PlannerHandoff(lesson_plan=plan)

    def test_rejects_empty_learning_objectives_list(self):
        plan = {"topic": "Photosynthesis", "learning_objectives": []}
        with pytest.raises(ValidationError, match="learning_objectives"):
            PlannerHandoff(lesson_plan=plan)

    def test_rejects_non_list_learning_objectives(self):
        plan = {"topic": "Photosynthesis", "learning_objectives": "text"}
        with pytest.raises(ValidationError, match="learning_objectives"):
            PlannerHandoff(lesson_plan=plan)

    def test_extra_fields_are_allowed(self):
        plan = {**self._valid_plan(), "grade_level": "Grade 5", "duration_minutes": 45}
        PlannerHandoff(lesson_plan=plan)


# ── ResearcherHandoff ─────────────────────────────────────────────────────────

class TestResearcherHandoff:
    def _valid_brief(self) -> dict:
        return {
            "topic": "Photosynthesis",
            "sources": [
                {"title": "Khan Academy", "credibility_score": 0.9, "verification_status": "VERIFIED"},
            ],
        }

    def _valid_plan(self) -> dict:
        return {"topic": "Photosynthesis", "learning_objectives": [{"description": "define it", "bloom_level": "remember"}]}

    def test_accepts_valid_handoff(self):
        ResearcherHandoff(lesson_plan=self._valid_plan(), research_brief=self._valid_brief())

    def test_rejects_empty_sources_list(self):
        brief = {**self._valid_brief(), "sources": []}
        with pytest.raises(ValidationError, match="sources"):
            ResearcherHandoff(lesson_plan=self._valid_plan(), research_brief=brief)

    def test_rejects_missing_sources(self):
        brief = {"topic": "Photosynthesis"}
        with pytest.raises(ValidationError, match="sources"):
            ResearcherHandoff(lesson_plan=self._valid_plan(), research_brief=brief)

    def test_rejects_sources_not_a_list(self):
        brief = {**self._valid_brief(), "sources": "not a list"}
        with pytest.raises(ValidationError, match="sources"):
            ResearcherHandoff(lesson_plan=self._valid_plan(), research_brief=brief)

    def test_rejects_missing_lesson_plan_topic(self):
        plan = {"learning_objectives": [{"description": "x", "bloom_level": "remember"}]}
        with pytest.raises(ValidationError, match="topic"):
            ResearcherHandoff(lesson_plan=plan, research_brief=self._valid_brief())

    def test_multiple_sources_accepted(self):
        brief = {
            **self._valid_brief(),
            "sources": [
                {"title": "Source A", "credibility_score": 0.8, "verification_status": "VERIFIED"},
                {"title": "Source B", "credibility_score": 0.7, "verification_status": "MODIFIED"},
            ],
        }
        ResearcherHandoff(lesson_plan=self._valid_plan(), research_brief=brief)


# ── ArtifactWorkflowHandoff ───────────────────────────────────────────────────

class TestArtifactWorkflowHandoff:
    def _artifact(self, artifact_id: str, artifact_type: str = "lesson") -> dict:
        return {"artifact_id": artifact_id, "artifact_type": artifact_type, "content": "x"}

    def test_accepts_valid_artifacts(self):
        ArtifactWorkflowHandoff(artifacts=[self._artifact("id-1"), self._artifact("id-2")])

    def test_rejects_empty_artifacts_list(self):
        with pytest.raises(ValidationError, match="artifact_workflow"):
            ArtifactWorkflowHandoff(artifacts=[])

    def test_rejects_artifact_missing_id(self):
        bad = {"artifact_type": "lesson", "content": "x"}  # no artifact_id or id
        with pytest.raises(ValidationError, match="artifact_id"):
            ArtifactWorkflowHandoff(artifacts=[bad])

    def test_accepts_artifact_with_id_field_instead_of_artifact_id(self):
        artifact = {"id": "alt-id", "artifact_type": "lesson", "content": "x"}
        ArtifactWorkflowHandoff(artifacts=[artifact])

    def test_second_artifact_missing_id_raises(self):
        ok = self._artifact("id-1")
        bad = {"artifact_type": "worksheet", "content": "y"}
        with pytest.raises(ValidationError, match=r"artifacts\[1\]"):
            ArtifactWorkflowHandoff(artifacts=[ok, bad])

    def test_single_artifact_accepted(self):
        ArtifactWorkflowHandoff(artifacts=[self._artifact("solo")])

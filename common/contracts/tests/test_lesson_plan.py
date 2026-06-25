"""Tests for LessonPlan contract and methodology extensions."""
from __future__ import annotations
import pytest
from pydantic import ValidationError
from common.contracts.lesson_plan import (
    LessonPlan, LearningObjective, AssessmentCheckpoint, MethodologyMetadata,
)

class TestLearningObjective:
    def test_valid_bloom_levels(self):
        for level in ("remember", "understand", "apply", "analyze", "evaluate", "create"):
            obj = LearningObjective(description="Do something", bloom_level=level)
            assert obj.bloom_level == level

    def test_invalid_bloom_level(self):
        with pytest.raises(ValidationError):
            LearningObjective(description="x", bloom_level="memorize")

    def test_description_max_length(self):
        with pytest.raises(ValidationError):
            LearningObjective(description="x" * 501, bloom_level="remember")

class TestLessonPlan:
    def _valid_plan(self, **kwargs):
        defaults = {
            "topic": "Unit 2 Travel", "grade_level": "Grade 10", "subject": "english",
            "duration_minutes": 60,
            "learning_objectives": [
                LearningObjective(description="Distinguish arrive/reach/enter", bloom_level="understand"),
                LearningObjective(description="Use phrasal verbs correctly", bloom_level="apply"),
            ],
        }
        defaults.update(kwargs)
        return LessonPlan(**defaults)

    def test_valid_minimal(self):
        plan = self._valid_plan()
        assert plan.topic == "Unit 2 Travel"
        assert plan.methodology is None

    def test_duration_bounds(self):
        with pytest.raises(ValidationError):
            self._valid_plan(duration_minutes=5)
        with pytest.raises(ValidationError):
            self._valid_plan(duration_minutes=200)

    def test_requires_at_least_one_objective(self):
        with pytest.raises(ValidationError):
            self._valid_plan(learning_objectives=[])

    def test_methodology_none_by_default(self):
        plan = self._valid_plan()
        assert plan.methodology is None

    def test_methodology_with_tags(self):
        meta = MethodologyMetadata(
            tags=["concept_map", "film_based", "shy_student_1on1"],
            target_skill_area="vocabulary",
        )
        plan = self._valid_plan(methodology=meta)
        assert "concept_map" in plan.methodology.tags
        assert "film_based" in plan.methodology.tags

    def test_methodology_invalid_tag(self):
        with pytest.raises(ValidationError):
            MethodologyMetadata(tags=["invalid_tag"])

    def test_methodology_all_valid_tags(self):
        all_tags = [
            "concept_map", "contrastive_pairs", "film_based",
            "shy_student_1on1", "active_recall", "why_wrong_reasoning",
            "timed_quiz", "roleplay_script",
        ]
        meta = MethodologyMetadata(tags=all_tags)
        assert len(meta.tags) == len(all_tags)

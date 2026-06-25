"""Tests for StudentProfile model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.student_profile import LearningStyle, PersonalityTrait, StudentProfile


class TestLearningStyle:
    """Test suite for LearningStyle model."""

    def test_valid_instantiation(self):
        """LearningStyle requires only the primary field."""
        ls = LearningStyle(primary="visual")
        assert ls.primary == "visual"
        assert ls.media_preference is None
        assert ls.format_preference is None

    def test_missing_primary_raises(self):
        """LearningStyle raises ValidationError when primary is absent."""
        with pytest.raises(ValidationError):
            LearningStyle()

    def test_with_all_fields(self):
        """LearningStyle stores optional fields when provided."""
        ls = LearningStyle(
            primary="auditory",
            media_preference="podcast",
            format_preference="1v1",
        )
        assert ls.primary == "auditory"
        assert ls.media_preference == "podcast"
        assert ls.format_preference == "1v1"

    def test_primary_values(self):
        """LearningStyle accepts exactly the four recognised primary styles."""
        for style in ("visual", "auditory", "kinesthetic", "reading"):
            ls = LearningStyle(primary=style)
            assert ls.primary == style

    def test_rejects_invalid_primary(self):
        """LearningStyle rejects unrecognised primary styles."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            LearningStyle(primary="mixed")


class TestPersonalityTrait:
    """Test suite for PersonalityTrait model."""

    def test_all_fields(self):
        """PersonalityTrait stores trait, vn_name, and teaching_principle."""
        pt = PersonalityTrait(
            trait="introvert",
            vn_name="Hướng nội",
            teaching_principle="Provide written instructions before verbal discussion.",
        )
        assert pt.trait == "introvert"
        assert pt.vn_name == "Hướng nội"
        assert pt.teaching_principle == "Provide written instructions before verbal discussion."

    def test_missing_field_raises(self):
        """PersonalityTrait raises ValidationError when any required field is missing."""
        with pytest.raises(ValidationError):
            PersonalityTrait(trait="introvert", vn_name="Hướng nội")

    def test_various_traits(self):
        """PersonalityTrait accepts any string value for trait."""
        for trait in ("introvert", "extrovert", "intuitive", "sensing"):
            pt = PersonalityTrait(trait=trait, vn_name="test", teaching_principle="test")
            assert pt.trait == trait


class TestStudentProfile:
    """Test suite for StudentProfile model."""

    def _make_learning_style(self) -> LearningStyle:
        return LearningStyle(primary="visual")

    def test_valid_instantiation(self):
        """StudentProfile requires student_id and learning_style; all else defaults."""
        profile = StudentProfile(
            student_id="s-001",
            learning_style=self._make_learning_style(),
        )
        assert profile.student_id == "s-001"
        assert profile.learning_style.primary == "visual"

    def test_list_fields_default_empty(self):
        """personality_traits, weaknesses, strengths, and tools default to []."""
        profile = StudentProfile(
            student_id="s-002",
            learning_style=self._make_learning_style(),
        )
        assert profile.personality_traits == []
        assert profile.weaknesses == []
        assert profile.strengths == []
        assert profile.tools == []

    def test_optional_scalar_fields_default_none(self):
        """target_score and target_exam default to None."""
        profile = StudentProfile(
            student_id="s-003",
            learning_style=self._make_learning_style(),
        )
        assert profile.target_score is None
        assert profile.target_exam is None

    def test_scalar_defaults(self):
        """study_duration_months defaults to 6 and raw_context defaults to empty string."""
        profile = StudentProfile(
            student_id="s-004",
            learning_style=self._make_learning_style(),
        )
        assert profile.study_duration_months == 6
        assert profile.raw_context == ""

    def test_missing_student_id_raises(self):
        """StudentProfile raises ValidationError when student_id is absent."""
        with pytest.raises(ValidationError):
            StudentProfile(learning_style=self._make_learning_style())

    def test_missing_learning_style_raises(self):
        """StudentProfile raises ValidationError when learning_style is absent."""
        with pytest.raises(ValidationError):
            StudentProfile(student_id="s-005")

    def test_with_personality_traits(self):
        """StudentProfile stores a list of PersonalityTrait objects."""
        traits = [
            PersonalityTrait(
                trait="introvert",
                vn_name="Hướng nội",
                teaching_principle="Prefer written materials.",
            ),
            PersonalityTrait(
                trait="intuitive",
                vn_name="Trực giác",
                teaching_principle="Connect concepts to big-picture goals.",
            ),
        ]
        profile = StudentProfile(
            student_id="s-006",
            learning_style=self._make_learning_style(),
            personality_traits=traits,
        )
        assert len(profile.personality_traits) == 2
        assert profile.personality_traits[0].trait == "introvert"

    def test_with_all_fields(self):
        """StudentProfile stores explicit values for all optional fields."""
        profile = StudentProfile(
            student_id="s-007",
            learning_style=LearningStyle(
                primary="kinesthetic",
                media_preference="video",
                format_preference="group",
            ),
            weaknesses=["listening", "pronunciation"],
            strengths=["reading", "grammar"],
            target_score=700,
            target_exam="TOEIC",
            study_duration_months=3,
            tools=["Anki", "Quizlet"],
            raw_context="Student has studied English for 5 years.",
        )
        assert profile.target_score == 700
        assert profile.target_exam == "TOEIC"
        assert profile.study_duration_months == 3
        assert profile.tools == ["Anki", "Quizlet"]
        assert "5 years" in profile.raw_context

    def test_json_roundtrip(self):
        """StudentProfile survives a model_dump / model_validate round-trip."""
        profile = StudentProfile(
            student_id="s-008",
            learning_style=self._make_learning_style(),
            target_exam="IELTS",
            study_duration_months=12,
        )
        data = profile.model_dump()
        restored = StudentProfile.model_validate(data)
        assert restored.student_id == "s-008"
        assert restored.target_exam == "IELTS"
        assert restored.learning_style.primary == "visual"

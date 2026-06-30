from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from common.contracts.student_profile import StudentProfile

ClassProfileSchemaVersion = Literal["class_profile.v1"]
AgeBand = Literal["early_primary", "upper_primary", "lower_secondary", "upper_secondary", "adult"]
ProficiencyLevel = Literal["beginner", "developing", "proficient", "advanced"]
AttentionSpanBand = Literal["short", "medium", "long"]


class LearningPreferences(BaseModel):
    model_config = ConfigDict(frozen=True)

    preferred_modalities: list[str] = Field(default_factory=list, max_length=8)
    preferred_methodologies: list[str] = Field(default_factory=list, max_length=8)
    avoid_methodologies: list[str] = Field(default_factory=list, max_length=8)


class ClassProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: ClassProfileSchemaVersion = "class_profile.v1"
    class_id: str | None = Field(default=None, max_length=64)
    grade: str = Field(min_length=1, max_length=64)
    age_band: AgeBand
    subject_focus: str = Field(min_length=1, max_length=80)
    language: str = Field(min_length=2, max_length=32)
    class_size: int = Field(ge=1, le=80)
    proficiency_level: ProficiencyLevel
    known_misconceptions: list[str] = Field(default_factory=list, max_length=20)
    prior_knowledge_gaps: list[str] = Field(default_factory=list, max_length=20)
    learning_preferences: LearningPreferences = Field(default_factory=LearningPreferences)
    attention_span_band: AttentionSpanBand = "medium"
    differentiation_needs: list[str] = Field(default_factory=list, max_length=20)
    prior_topics_taught: list[str] = Field(default_factory=list, max_length=50)
    students: list[StudentProfile] = Field(default_factory=list, max_length=40)

    @model_validator(mode="before")
    @classmethod
    def map_legacy_class_info(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        if "grade" in value and "subject_focus" in value:
            return value
        legacy = dict(value)
        grade_value = legacy.get("grade_band", legacy.get("grade", "Unknown"))
        subject_value = legacy.get("subject", legacy.get("subject_focus", "general"))
        student_count = legacy.get("student_count", legacy.get("class_size", 1))
        legacy["grade"] = str(grade_value)
        legacy.setdefault("age_band", _age_band_for_grade(grade_value))
        legacy["subject_focus"] = str(subject_value)
        legacy["language"] = str(legacy.get("locale", "en"))[:2]
        legacy.setdefault("class_size", student_count)
        legacy.setdefault("proficiency_level", "developing")
        return legacy


def class_profile_from_class_info(class_info: dict[str, object]) -> ClassProfile:
    return ClassProfile.model_validate(class_info)


def _age_band_for_grade(grade_value: object) -> AgeBand:
    text = str(grade_value).lower()
    digits = "".join(char for char in text if char.isdigit())
    grade = int(digits) if digits else 5
    if grade <= 2:
        return "early_primary"
    if grade <= 5:
        return "upper_primary"
    if grade <= 9:
        return "lower_secondary"
    return "upper_secondary"

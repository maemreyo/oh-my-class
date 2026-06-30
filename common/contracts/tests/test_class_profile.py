from __future__ import annotations

from common.contracts.class_profile import ClassProfile, class_profile_from_class_info
from common.contracts.student_profile import LearningStyle, StudentProfile


def test_valid_aggregate_profile_round_trips() -> None:
    profile = ClassProfile(
        class_id="5a",
        grade="Grade 5",
        age_band="upper_primary",
        subject_focus="math",
        language="vi",
        class_size=32,
        proficiency_level="developing",
        known_misconceptions=["fraction denominator means size, not count"],
        prior_knowledge_gaps=["equivalent fractions"],
    )

    restored = ClassProfile.model_validate(profile.model_dump())

    assert restored == profile
    assert restored.schema_version == "class_profile.v1"


def test_profile_with_students_accepts_small_group_persona() -> None:
    student = StudentProfile(
        student_id="pseudo-student-1",
        learning_style=LearningStyle(primary="visual"),
    )

    profile = ClassProfile(
        grade="Grade 4",
        age_band="upper_primary",
        subject_focus="science",
        language="en",
        class_size=1,
        proficiency_level="proficient",
        students=[student],
    )

    assert profile.students[0].student_id == "pseudo-student-1"


def test_legacy_class_info_maps_to_class_profile() -> None:
    profile = class_profile_from_class_info({
        "grade": 5,
        "subject": "math",
        "student_count": 30,
        "locale": "vi-VN",
    })

    assert profile.grade == "5"
    assert profile.age_band == "upper_primary"
    assert profile.subject_focus == "math"
    assert profile.language == "vi"
    assert profile.class_size == 30

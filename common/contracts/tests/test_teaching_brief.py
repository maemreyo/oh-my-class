from pydantic import ValidationError
import pytest

from common.contracts.teaching_brief import TeachingBrief, materiality_reasons


def test_default_teaching_brief_uses_the_standard_pack_recipe() -> None:
    brief = TeachingBrief(
        raw_request="Teach equivalent fractions.",
        topic="Equivalent fractions",
        grade=5,
        subject="math",
    )

    assert brief.artifact_types == ["lesson", "worksheet", "quiz", "drill", "slide_deck"]
    assert brief.export_formats == ["html"]
    assert brief.education_policy_version == "education_policy.v1"
    assert brief.subject == "math"


def test_rigorous_research_requires_planning_review() -> None:
    brief = TeachingBrief(
        raw_request="Teach equivalent fractions.",
        topic="Equivalent fractions",
        grade=5,
        subject="math",
        research_policy="rigorous",
    )

    assert materiality_reasons(brief) == ["rigorous_research"]


def test_teaching_brief_rejects_empty_request() -> None:
    with pytest.raises(ValidationError):
        TeachingBrief(raw_request="", topic="Fractions", grade=5, subject="math")


def test_teaching_brief_normalizes_language_labels() -> None:
    brief = TeachingBrief(
        raw_request="Teach equivalent fractions.",
        topic="Equivalent fractions",
        grade=5,
        subject="Maths",
        target_language="Vietnamese",
        instruction_language="English",
    )

    assert brief.subject == "math"
    assert brief.target_language == "vi"
    assert brief.instruction_language == "en"

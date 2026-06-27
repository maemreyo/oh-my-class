from __future__ import annotations

import pytest

from common.contracts.artifact import ArtifactContent
from common.contracts.quality import QualityFailureClass
from services.gateway.healing_executors import (
    UnrepairableArtifactError,
    heal_artifact,
    repair_schema,
    try_heal_artifact,
)


def test_repair_schema_fills_required_fields() -> None:
    repaired = repair_schema({"sections": []})

    assert repaired.artifact_type == "lesson"
    assert repaired.theme == "default"
    assert repaired.accessibility["language"] == "en"


def test_answer_key_healing_moves_student_section_to_teacher_only() -> None:
    artifact = _artifact(sections=[{"content": "Question", "answer": "correct: 42"}])

    healed = try_heal_artifact("quiz-1", artifact)

    assert healed is not None
    assert healed.sections[0]["teacher_only"] is True


def test_pii_healing_redacts_nested_student_email() -> None:
    artifact = _artifact(sections=[{"content": "Contact mai@example.com for student email"}])

    healed = heal_artifact(artifact, QualityFailureClass.PII_LEAKAGE)

    assert "mai@example.com" not in str(healed.sections)
    assert "student email" not in str(healed.sections).lower()


def test_accessibility_healing_adds_language() -> None:
    artifact = _artifact(accessibility={})

    healed = heal_artifact(artifact, QualityFailureClass.MISSING_ACCESSIBILITY)

    assert healed.accessibility["language"] == "en"


def test_presentation_healing_escalates_to_regeneration_path() -> None:
    artifact = _artifact()

    with pytest.raises(UnrepairableArtifactError):
        heal_artifact(artifact, QualityFailureClass.EXTERNAL_ASSET)


def _artifact(
    *,
    sections: list[dict] | None = None,
    accessibility: dict | None = None,
) -> ArtifactContent:
    return ArtifactContent(
        artifact_type="quiz",
        title="Quiz Artifact",
        sections=sections or [{"content": "Question"}],
        accessibility=accessibility if accessibility is not None else {"language": "en"},
    )

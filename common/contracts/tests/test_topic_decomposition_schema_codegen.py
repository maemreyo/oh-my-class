from __future__ import annotations

from pathlib import Path

from common.contracts.lesson_sequence import LessonSequence
from common.contracts.artifact_document import ArtifactDocument


GENERATED_DIR = Path("common/schemas/src/generated")


def test_generated_zod_schemas_include_topic_decomposition_contracts() -> None:
    lesson_sequence = GENERATED_DIR.joinpath("lesson_sequence.ts").read_text()
    unit_view = GENERATED_DIR.joinpath("unit_view.ts").read_text()
    run_contract = GENERATED_DIR.joinpath("run_contract.ts").read_text()
    class_profile = GENERATED_DIR.joinpath("class_profile.ts").read_text()

    schema_properties = LessonSequence.model_json_schema()["properties"]
    for field_name in schema_properties:
        assert f'"{field_name}"' in lesson_sequence

    assert "UnitViewSchema" in unit_view
    assert "UnitEventEnvelopeSchema" in unit_view
    assert "DecompositionIntentSchema" in run_contract
    assert "ClassProfileSchema" in class_profile
    assert "LearningPreferencesSchema" in class_profile
    # PipelineMode gained "vocabulary_batch" (ADR-021); assert membership, not exact
    # ordering, so adding a future mode does not re-break this stale-prone assertion.
    for mode in ("generate_pack", "diagnose_then_generate", "plan_unit", "vocabulary_batch"):
        assert f'"{mode}"' in run_contract


def test_generated_zod_schemas_include_artifact_document_contracts() -> None:
    artifact_document = GENERATED_DIR.joinpath("artifact_document.ts").read_text()
    answer_set = GENERATED_DIR.joinpath("answer_set.ts").read_text()

    for field_name in ArtifactDocument.model_json_schema()["properties"]:
        assert f'"{field_name}"' in artifact_document

    assert "ArtifactDocumentSchema" in artifact_document
    assert "AnswerSetSchema" in answer_set

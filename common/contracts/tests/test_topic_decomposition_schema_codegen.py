from __future__ import annotations

from pathlib import Path

from common.contracts.lesson_sequence import LessonSequence


GENERATED_DIR = Path("common/schemas/src/generated")


def test_generated_zod_schemas_include_topic_decomposition_contracts() -> None:
    lesson_sequence = GENERATED_DIR.joinpath("lesson_sequence.ts").read_text()
    unit_view = GENERATED_DIR.joinpath("unit_view.ts").read_text()
    run_contract = GENERATED_DIR.joinpath("run_contract.ts").read_text()

    schema_properties = LessonSequence.model_json_schema()["properties"]
    for field_name in schema_properties:
        assert f'"{field_name}"' in lesson_sequence

    assert "UnitViewSchema" in unit_view
    assert "UnitEventEnvelopeSchema" in unit_view
    assert "DecompositionIntentSchema" in run_contract
    assert 'z.enum(["generate_pack","diagnose_then_generate","plan_unit"])' in run_contract

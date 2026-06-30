from __future__ import annotations

from common.contracts.inverse_thinking import InverseThinkingPack


def test_inverse_thinking_json_schema_exposes_required_fields_for_zod_generation() -> None:
    schema = InverseThinkingPack.model_json_schema()
    required = set(schema["required"])

    assert {
        "methodology",
        "creative_frame",
        "cases",
        "summary_table",
        "student_challenges",
        "teacher_only",
    }.issubset(required)

    case_schema = schema["$defs"]["InverseThinkingCase"]
    assert {
        "id",
        "title",
        "target_concept",
        "foil",
        "disaster",
        "key_clues",
        "safe_zone",
        "filing_note",
        "student_task",
        "teacher_only",
    }.issubset(set(case_schema["required"]))

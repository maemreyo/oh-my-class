from __future__ import annotations

from common.contracts.lesson_plan import MethodologyMetadata


def test_inverse_thinking_tag_does_not_break_existing_methodology_tags() -> None:
    meta = MethodologyMetadata(
        tags=[
            "concept_map",
            "contrastive_pairs",
            "film_based",
            "shy_student_1on1",
            "active_recall",
            "why_wrong_reasoning",
            "timed_quiz",
            "roleplay_script",
            "inverse_thinking",
        ],
    )

    assert meta.tags[-1] == "inverse_thinking"
    assert "concept_map" in meta.tags

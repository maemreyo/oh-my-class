from __future__ import annotations

from services.gateway.observability.inverse_thinking import (
    InverseThinkingEvent,
    build_inverse_thinking_metadata,
)


def test_inverse_thinking_metadata_records_release_dimensions() -> None:
    event = InverseThinkingEvent(
        run_id="run-1",
        methodology="inverse_thinking",
        creative_frame="detective_case",
        projection="lesson",
        feature_flag="inverse_thinking_v1",
        quality_gate="passed",
        repair_attempt=2,
        warning_category="generic_disaster",
        teacher_action="approve",
        export_status="passed",
    )

    metadata = build_inverse_thinking_metadata(event)

    assert metadata == {
        "run_id": "run-1",
        "methodology": "inverse_thinking",
        "creative_frame": "detective_case",
        "projection": "lesson",
        "feature_flag": "inverse_thinking_v1",
        "quality_gate": "passed",
        "repair_attempt": 2,
        "warning_category": "generic_disaster",
        "teacher_action": "approve",
        "export_status": "passed",
    }


def test_inverse_thinking_metadata_omits_absent_optional_dimensions() -> None:
    event = InverseThinkingEvent(
        run_id="run-2",
        methodology="inverse_thinking",
        creative_frame="survival_guide",
        projection="drill",
        feature_flag="inverse_thinking_v1",
        quality_gate="failed",
        repair_attempt=0,
    )

    metadata = build_inverse_thinking_metadata(event)

    assert "teacher_action" not in metadata
    assert "export_status" not in metadata
    assert metadata["quality_gate"] == "failed"

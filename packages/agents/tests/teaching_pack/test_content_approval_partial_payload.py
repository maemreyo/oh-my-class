from __future__ import annotations

from unittest.mock import patch

from packages.agents.teaching_pack.artifact_status import artifact_statuses_for_teacher
from packages.agents.teaching_pack.nodes import TeachingPackState, _teacher_approval


def test_artifact_status_projection_redacts_internal_error_details() -> None:
    state = {
        "run_id": "run-partial",
        "artifact_types": ["lesson", "quiz", "recap"],
        "artifact_references": [{
            "document_id": "run-partial:artifact:1:lesson-1",
            "artifact_id": "lesson-1",
            "artifact_type": "lesson",
            "generation_id": "run-partial:artifact:1",
            "version": 1,
            "title": "Lesson",
        }],
        "artifact_workflow_states": [
            {"artifact_type": "lesson", "artifact_id": "lesson-1", "status": "passed"},
            {
                "artifact_type": "quiz",
                "artifact_id": "quiz-1",
                "status": "failed",
                "error_summary": "Traceback provider stack with api_key=secret",
            },
            {"artifact_type": "recap", "artifact_id": "recap", "status": "skipped"},
        ],
    }

    statuses = artifact_statuses_for_teacher(state)

    assert [item["status"] for item in statuses] == ["passed", "failed", "skipped_due_dependency"]
    assert statuses[1]["summary"] == "Artifact generation failed. Request edits to regenerate this item."
    assert "Traceback" not in str(statuses)
    assert statuses[2]["teacher_action"] == "Fix the failed dependency, then regenerate."


def test_content_approval_gate_payload_includes_partial_artifact_statuses() -> None:
    state = TeachingPackState(
        run_id="run-gate-partial",
        artifact_types=["lesson", "quiz", "recap"],
        artifact_references=[{
            "document_id": "run-gate-partial:artifact:1:lesson-1",
            "artifact_id": "lesson-1",
            "artifact_type": "lesson",
            "generation_id": "run-gate-partial:artifact:1",
            "version": 1,
            "title": "Lesson",
        }],
        artifact_workflow_states=[
            {"artifact_type": "lesson", "artifact_id": "lesson-1", "status": "passed"},
            {"artifact_type": "quiz", "artifact_id": "quiz-1", "status": "failed"},
            {"artifact_type": "recap", "artifact_id": "recap", "status": "skipped"},
        ],
        rendered_snapshots=[{"snapshot_id": "snapshot-lesson"}],
    )

    with patch("langgraph.types.interrupt", return_value={"action": "reject", "feedback": "Fix quiz"}):
        result = _teacher_approval(state)

    approval_gate = result["approval_gate"]
    assert [item["status"] for item in approval_gate["artifact_statuses"]] == [
        "passed",
        "failed",
        "skipped_due_dependency",
    ]
    assert approval_gate["artifacts"][0]["status"] == "passed"
    assert approval_gate["artifacts"][1]["status"] == "failed"

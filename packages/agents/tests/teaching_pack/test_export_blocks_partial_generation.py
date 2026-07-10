from __future__ import annotations

from packages.agents.teaching_pack.nodes import TeachingPackState, _export_finalize


def test_export_finalize_blocks_when_required_artifact_failed() -> None:
    state = TeachingPackState(
        run_id="run-export-block",
        teacher_approved=True,
        contract={"export_formats": ["html"], "artifact_types": ["lesson", "quiz"]},
        artifact_types=["lesson", "quiz"],
        artifact_references=[{
            "document_id": "run-export-block:artifact:1:lesson-1",
            "artifact_id": "lesson-1",
            "artifact_type": "lesson",
            "generation_id": "run-export-block:artifact:1",
            "version": 1,
            "title": "Lesson",
        }],
        artifact_workflow_states=[
            {"artifact_id": "lesson-1", "artifact_type": "lesson", "status": "passed"},
            {"artifact_id": "quiz-1", "artifact_type": "quiz", "status": "failed"},
        ],
        approved_snapshot_ids=["snapshot-lesson"],
        rendered_snapshots=[{"snapshot_id": "snapshot-lesson", "artifact_type": "lesson"}],
    )

    result = _export_finalize(state)

    assert result["exported_files"] == []
    assert result["export_blocked"] is True
    assert result["export_block_reason"] == "Export is blocked until these required artifacts are ready: quiz."
    assert result["artifact_statuses"][0]["status"] == "failed"

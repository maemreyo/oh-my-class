from __future__ import annotations

from services.gateway.routers.teaching_pack_lifecycle import _latest_artifact_statuses
from services.gateway.teaching_pack_store import TeachingPackEventRead
from services.gateway.teaching_pack_models import TeachingPackEventVisibility
from services.gateway.teaching_pack_types import RunId


def test_latest_artifact_statuses_uses_teacher_safe_content_approval_payload() -> None:
    events = [
        TeachingPackEventRead(
            run_id=RunId("run-api"),
            sequence=1,
            event_name="teaching_pack.content_approval.opened",
            visibility=TeachingPackEventVisibility.TEACHER,
            payload={
                "artifact_statuses": [
                    {
                        "artifact_id": "quiz-1",
                        "artifact_type": "quiz",
                        "status": "failed",
                        "summary": "Artifact generation failed. Request edits to regenerate this item.",
                        "teacher_action": "Request edits to regenerate this artifact.",
                    },
                ],
            },
        ),
    ]

    statuses = _latest_artifact_statuses(events)

    assert statuses[0]["status"] == "failed"
    assert "Traceback" not in str(statuses)

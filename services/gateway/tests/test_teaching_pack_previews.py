from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import anyio

from services.gateway.models import RunStatus
from services.gateway.teaching_pack_types import RunId
from services.gateway.tests.teaching_pack_preview_helpers import (
    approved_event_payload,
    create_run_with_snapshot,
    delete_run,
)

if TYPE_CHECKING:
    from starlette.testclient import TestClient

pytest_plugins = ("services.gateway.tests.teaching_pack_preview_fixtures",)


class TestTeachingPackPreviews:
    def test_metadata_returns_snapshot_refs_without_html(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_run_with_snapshot, run_id, snapshot_id)

        response = client.get(f"/teaching-packs/run/{run_id}/snapshots/{snapshot_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["snapshot_id"] == snapshot_id
        assert data["artifact_id"] == "lesson-1"
        assert data["standalone_valid"] is True
        assert data["renderer_version"] == "renderer@test"
        assert data["template_version"] == "template@test"
        assert data["theme_version"] == "theme@test"
        assert "rendered_html" not in data
        assert "student_rendered_html" not in data
        assert "content_hash" in data
        assert "html_hash" in data
        anyio.run(delete_run, run_id)

    def test_student_preview_redacts_teacher_only_content(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_run_with_snapshot, run_id, snapshot_id)

        response = client.get(
            f"/teaching-packs/run/{run_id}/snapshots/{snapshot_id}/preview",
        )

        assert response.status_code == 200
        assert "Student question" in response.text
        assert "&lt;img src=x onerror=alert(1)&gt;" in response.text
        assert "<img src=x onerror=alert(1)>" not in response.text
        assert "Answer Key" not in response.text
        assert "Correct answer" not in response.text
        anyio.run(delete_run, run_id)

    def test_student_preview_preserves_rendered_snapshot_markup(
        self,
        client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(
            create_run_with_snapshot,
            run_id,
            snapshot_id,
            RunStatus.AWAITING_APPROVAL,
            (
                "<!DOCTYPE html><html><body><header>oh-my-class</header>"
                f"<h1>Fractions {snapshot_id}</h1>"
                '<section class="lesson-card"><h2>Inverse-thinking trap</h2>'
                "<p>Student question</p></section>"
                '<section class="teacher-note" data-teacher-only="true">'
                "Answer Key Correct answer</section>"
                "</body></html>"
            ),
        )

        response = client.get(
            f"/teaching-packs/run/{run_id}/snapshots/{snapshot_id}/preview",
        )

        assert response.status_code == 200
        assert 'class="lesson-card"' in response.text
        assert "Inverse-thinking trap" in response.text
        assert "Answer Key" not in response.text
        assert "Correct answer" not in response.text
        anyio.run(delete_run, run_id)

    def test_teacher_preview_includes_answer_keys(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_run_with_snapshot, run_id, snapshot_id)

        response = client.get(
            f"/teaching-packs/run/{run_id}/snapshots/{snapshot_id}/preview?view=teacher",
        )

        assert response.status_code == 200
        assert "Answer Key" in response.text
        assert "Correct answer" in response.text
        anyio.run(delete_run, run_id)

    def test_approve_records_exact_snapshot_ids_and_event(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_run_with_snapshot, run_id, snapshot_id)

        response = client.post(
            f"/teaching-packs/run/{run_id}/approved-snapshots",
            json={"snapshot_ids": [snapshot_id]},
        )
        approved_event = anyio.run(approved_event_payload, run_id)

        assert response.status_code == 200
        assert response.json() == {
            "run_id": run_id,
            "approved_snapshot_ids": [snapshot_id],
        }
        assert approved_event == {"snapshot_ids": [snapshot_id]}
        anyio.run(delete_run, run_id)

    def test_approve_rejects_run_that_is_not_awaiting_approval(
        self,
        client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_run_with_snapshot, run_id, snapshot_id, RunStatus.PENDING)

        response = client.post(
            f"/teaching-packs/run/{run_id}/approved-snapshots",
            json={"snapshot_ids": [snapshot_id]},
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "run_not_awaiting_approval"
        anyio.run(delete_run, run_id)

    def test_approve_rejects_non_standalone_snapshot(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(
            create_run_with_snapshot,
            run_id,
            snapshot_id,
            RunStatus.AWAITING_APPROVAL,
            (
                '<!DOCTYPE html><html><head><link href="/style.css"></head>'
                "<body>oh-my-class</body></html>"
            ),
        )

        response = client.post(
            f"/teaching-packs/run/{run_id}/approved-snapshots",
            json={"snapshot_ids": [snapshot_id]},
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "non_standalone_snapshot"
        anyio.run(delete_run, run_id)

    def test_non_owner_cannot_access_snapshot(
        self,
        other_teacher_client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_run_with_snapshot, run_id, snapshot_id)

        response = other_teacher_client.get(
            f"/teaching-packs/run/{run_id}/snapshots/{snapshot_id}",
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "run_not_found"
        anyio.run(delete_run, run_id)

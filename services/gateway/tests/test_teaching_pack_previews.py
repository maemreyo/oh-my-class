from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import anyio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.contracts.slide_deck import SlideDeckDisplayPreferences
from services.gateway.models import RunStatus
from services.gateway.routers import teaching_pack_previews
from services.gateway.teaching_pack_snapshot_schemas import ArtifactSnapshotRead
from services.gateway.teaching_pack_snapshot_store import ArtifactSnapshotCreate, TeachingPackSnapshotStore
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import JsonObject, RunId, TeacherId
from services.gateway.tests.teaching_pack_preview_db import DATABASE_URL
from services.gateway.tests.teaching_pack_preview_helpers import (
    approved_event_payload,
    create_run_with_snapshot,
    delete_run,
)

if TYPE_CHECKING:
    from starlette.testclient import TestClient

pytest_plugins = ("services.gateway.tests.teaching_pack_preview_fixtures",)

_TRANSLATE_TEST_DECK: JsonObject = {
    "deck_id": "slide-deck-translate-source",
    "title": "Fractions Slide Deck",
    "locale": "en-US",
    "surfaces": {
        "student": {"mode": "presentation", "export_format": "html"},
        "teacher": {"mode": "teacher_guide", "export_format": "html"},
        "print": {"mode": "print", "export_format": "html"},
    },
    "slides": [
        {
            "slide_id": "slide-title",
            "title": "Fractions",
            "layout": "title",
            "progression": {"step_index": 1, "reveal_policy": "all_at_once"},
            "blocks": [{"block_id": "block-title", "block_type": "heading", "body": "Fractions"}],
        },
    ],
    "accessibility": {"reading_level": "Grade 5", "language": "en"},
    "media_policy": {"default_tier": "packaged", "online_optional_allowed": True, "fallback_required": True},
}


async def _create_run_with_slide_deck_snapshot(run_id: RunId, snapshot_id: str) -> None:
    # content_hash dedupes on (content_json, rendered_html) alone, not run/snapshot
    # id -- embed snapshot_id in the deck payload so each test call hashes uniquely.
    deck = {**_TRANSLATE_TEST_DECK, "deck_id": f"slide-deck-{snapshot_id}"}
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(
            TeachingPackRunCreate(
                run_id=run_id,
                teacher_id=TeacherId("teacher-preview"),
                raw_request="Teach a translated deck",
                class_info={"grade": 5},
            )
        )
        await TeachingPackSnapshotStore(session).create_snapshot(
            ArtifactSnapshotCreate(
                snapshot_id=snapshot_id,
                run_id=run_id,
                artifact_id="slide-deck-1",
                artifact_type="slide_deck",
                content_json={
                    "artifact_type": "slide_deck",
                    "title": deck["title"],
                    "sections": [{"title": deck["title"], "slide_deck": deck}],
                    "metadata": {"slide_deck_data": deck},
                },
                rendered_html=f"<!DOCTYPE html><html><body>oh-my-class teacher surface {snapshot_id}</body></html>",
                renderer_version="renderer@test",
                template_version="template@test",
                theme_version="theme@test",
            )
        )
        await session.commit()
    await engine.dispose()


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

    def test_typed_surface_presentation_maps_to_student_safe_html(self, client: TestClient) -> None:
        # SDH-04: the app's Print & sharing panel sends `surface` (the ADR-043
        # typed seam), not the legacy `view` value. `presentation` shares the
        # student-safe content boundary, so it must redact the same way.
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_run_with_snapshot, run_id, snapshot_id)

        response = client.get(
            f"/teaching-packs/run/{run_id}/snapshots/{snapshot_id}/preview?surface=presentation",
        )

        assert response.status_code == 200
        assert "Student question" in response.text
        assert "Answer Key" not in response.text
        assert "Correct answer" not in response.text
        anyio.run(delete_run, run_id)

    def test_typed_surface_review_maps_to_teacher_only_html_and_requires_role(
        self, client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_run_with_snapshot, run_id, snapshot_id)

        response = client.get(
            f"/teaching-packs/run/{run_id}/snapshots/{snapshot_id}/preview?surface=review",
        )

        assert response.status_code == 200
        assert "Answer Key" in response.text
        assert "Correct answer" in response.text
        anyio.run(delete_run, run_id)

    def test_typed_surface_invalid_value_falls_back_to_presentation_default(
        self, client: TestClient,
    ) -> None:
        # ADR-043 resilience: a malformed `surface` never 422s the preview --
        # it resolves to the production-safe default (presentation) instead.
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_run_with_snapshot, run_id, snapshot_id)

        response = client.get(
            f"/teaching-packs/run/{run_id}/snapshots/{snapshot_id}/preview?surface=bogus",
        )

        assert response.status_code == 200
        assert "Answer Key" not in response.text
        anyio.run(delete_run, run_id)

    def test_slide_deck_print_preview_renders_print_surface(self, monkeypatch) -> None:
        calls: list[JsonObject] = []

        async def render_print(content: JsonObject) -> str:
            calls.append(content)
            return "<!DOCTYPE html><html><body>oh-my-class print surface</body></html>"

        monkeypatch.setattr(teaching_pack_previews, "render_artifact_content", render_print)
        snapshot = ArtifactSnapshotRead(
            snapshot_id="snapshot-slide",
            run_id=RunId("run-slide"),
            artifact_id="artifact-slide",
            artifact_type="slide_deck",
            content_hash="content-hash",
            html_hash="html-hash",
            content_json={
                "artifact_type": "slide_deck",
                "metadata": {"slide_deck_data": {"deck_id": "deck-1", "title": "Deck", "slides": []}},
            },
            rendered_html="<!DOCTYPE html><html><body>teacher surface</body></html>",
            student_rendered_html="<!DOCTYPE html><html><body>student surface</body></html>",
            renderer_version="renderer@test",
            template_version="template@test",
            theme_version="theme@test",
            standalone_valid=True,
            approved_at=None,
        )

        html = anyio.run(teaching_pack_previews._print_preview_html, snapshot)

        assert html == "<!DOCTYPE html><html><body>oh-my-class print surface</body></html>"
        assert calls[0]["metadata"]["slide_deck_data"]["render_surface"] == "print"
        # Backward compatibility: this deck predates ADR-043 display preferences
        # (no `display_preferences` key at all), so the effective preferences
        # must resolve to production-safe defaults rather than raise/break.
        assert calls[0]["metadata"]["slide_deck_data"]["display_preferences"] == {
            "surface": "print",
            "print_layout": "paged",
            "slides_per_page": 1,
            "chrome": "hidden",
        }

    def test_slide_deck_print_preview_preserves_existing_preferences_and_overrides_surface(
        self, monkeypatch
    ) -> None:
        calls: list[JsonObject] = []

        async def render_print(content: JsonObject) -> str:
            calls.append(content)
            return "<!DOCTYPE html><html><body>oh-my-class print surface</body></html>"

        monkeypatch.setattr(teaching_pack_previews, "render_artifact_content", render_print)
        snapshot = ArtifactSnapshotRead(
            snapshot_id="snapshot-slide-2",
            run_id=RunId("run-slide-2"),
            artifact_id="artifact-slide-2",
            artifact_type="slide_deck",
            content_hash="content-hash",
            html_hash="html-hash",
            content_json={
                "artifact_type": "slide_deck",
                "metadata": {
                    "slide_deck_data": {
                        "deck_id": "deck-2",
                        "title": "Deck",
                        "slides": [],
                        # Teacher previously chose 4-up continuous layout with
                        # an invalid chrome value that must fall back safely.
                        "display_preferences": {
                            "surface": "student",
                            "print_layout": "continuous",
                            "slides_per_page": 4,
                            "chrome": "very_loud",
                        },
                    }
                },
            },
            rendered_html="<!DOCTYPE html><html><body>teacher surface</body></html>",
            student_rendered_html="<!DOCTYPE html><html><body>student surface</body></html>",
            renderer_version="renderer@test",
            template_version="template@test",
            theme_version="theme@test",
            standalone_valid=True,
            approved_at=None,
        )

        anyio.run(teaching_pack_previews._print_preview_html, snapshot)

        # The print view always wins on `surface`, but other teacher-chosen
        # preferences (layout, slides-per-page) are preserved; the invalid
        # `chrome` value falls back to the safe default instead of breaking.
        assert calls[0]["metadata"]["slide_deck_data"]["display_preferences"] == {
            "surface": "print",
            "print_layout": "continuous",
            "slides_per_page": 4,
            "chrome": "hidden",
        }

    def test_typed_print_request_overrides_deck_stored_preferences_outright(
        self, monkeypatch,
    ) -> None:
        # SDH-04: unlike the legacy `_print_preview_html` merge (which
        # preserves the deck's own stored layout/slides-per-page/chrome), a
        # request through the typed Print & sharing panel seam is the
        # explicit, fully-resolved source of truth and must win outright --
        # even over a deck that already had different preferences stored.
        calls: list[JsonObject] = []

        async def render_print(content: JsonObject) -> str:
            calls.append(content)
            return "<!DOCTYPE html><html><body>oh-my-class print surface</body></html>"

        monkeypatch.setattr(teaching_pack_previews, "render_artifact_content", render_print)
        snapshot = ArtifactSnapshotRead(
            snapshot_id="snapshot-slide-3",
            run_id=RunId("run-slide-3"),
            artifact_id="artifact-slide-3",
            artifact_type="slide_deck",
            content_hash="content-hash",
            html_hash="html-hash",
            content_json={
                "artifact_type": "slide_deck",
                "metadata": {
                    "slide_deck_data": {
                        "deck_id": "deck-3",
                        "title": "Deck",
                        "slides": [],
                        "display_preferences": {
                            "surface": "student",
                            "print_layout": "continuous",
                            "slides_per_page": 6,
                            "chrome": "branded",
                        },
                    }
                },
            },
            rendered_html="<!DOCTYPE html><html><body>teacher surface</body></html>",
            student_rendered_html="<!DOCTYPE html><html><body>student surface</body></html>",
            renderer_version="renderer@test",
            template_version="template@test",
            theme_version="theme@test",
            standalone_valid=True,
            approved_at=None,
        )

        preferences = SlideDeckDisplayPreferences(
            surface="print", print_layout="paged", slides_per_page=2, chrome="minimal",
        )
        html = anyio.run(
            teaching_pack_previews._slide_deck_preview_html_for_preferences,
            snapshot,
            preferences,
        )

        assert html == "<!DOCTYPE html><html><body>oh-my-class print surface</body></html>"
        assert calls[0]["metadata"]["slide_deck_data"]["render_surface"] == "print"
        assert calls[0]["metadata"]["slide_deck_data"]["display_preferences"] == {
            "surface": "print",
            "print_layout": "paged",
            "slides_per_page": 2,
            "chrome": "minimal",
        }

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

    def test_translate_slide_deck_creates_new_snapshot_with_lineage(
        self,
        client: TestClient,
        monkeypatch,
    ) -> None:
        async def fake_render(content: JsonObject, config=None) -> str:
            return "<!DOCTYPE html><html><body>oh-my-class translated deck</body></html>"

        monkeypatch.setattr(
            "services.gateway.artifact_snapshot_service.render_artifact_content",
            fake_render,
        )

        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        response = client.post(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/translate",
            json={"target_language": "vi"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert data["source_snapshot_id"] == snapshot_id
        assert data["snapshot_id"] != snapshot_id
        assert data["deck_id"] == f"slide-deck-{snapshot_id}-vi"
        anyio.run(delete_run, run_id)

    def test_translate_slide_deck_rejects_unsupported_language(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        response = client.post(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/translate",
            json={"target_language": "fr"},
        )

        assert response.status_code == 422
        anyio.run(delete_run, run_id)

    def test_translate_slide_deck_rejects_non_slide_deck_snapshot(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_run_with_snapshot, run_id, snapshot_id)

        response = client.post(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/translate",
            json={"target_language": "vi"},
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "not_a_slide_deck"
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


class TestSlideDeckBlockEdit:
    """SDE-04: standalone scoped block edit -- optimistic locking via
    `base_snapshot_id`, independent of run/gate state. These tests hit the
    real gateway router (`client` fixture wires the actual `teaching_pack_previews.router`
    into a FastAPI app with only `require_teacher`/DB session overridden), so
    they are the "live-path-proof" for this entry point -- not a unit test
    calling the business function directly.
    """

    def test_edit_creates_new_immutable_version_and_preserves_old(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        response = client.patch(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title",
            json={"base_snapshot_id": snapshot_id, "new_content": "Teacher-revised heading."},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["snapshot_id"] != snapshot_id
        assert data["artifact_id"] == "slide-deck-1"
        assert data["block_id"] == "block-title"

        old_snapshot = anyio.run(_get_snapshot, run_id, snapshot_id)
        new_snapshot = anyio.run(_get_snapshot, run_id, data["snapshot_id"])
        assert _block_body(old_snapshot) == "Fractions"  # original, untouched
        assert _block_body(new_snapshot) == "Teacher-revised heading."
        anyio.run(delete_run, run_id)

    def test_edit_returns_409_when_base_snapshot_id_is_stale(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        first = client.patch(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title",
            json={"base_snapshot_id": snapshot_id, "new_content": "First revision."},
        )
        assert first.status_code == 200

        # Same stale base_snapshot_id again -- the head has already moved on.
        second = client.patch(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title",
            json={"base_snapshot_id": snapshot_id, "new_content": "Second revision."},
        )

        assert second.status_code == 409
        assert second.json()["detail"] == "base_snapshot_id_stale"
        anyio.run(delete_run, run_id)

    def test_edit_rejects_unknown_block_id(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        response = client.patch(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-does-not-exist",
            json={"base_snapshot_id": snapshot_id, "new_content": "New body."},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "block_not_found"
        anyio.run(delete_run, run_id)

    def test_edit_rejects_body_over_registry_max_length(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        response = client.patch(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title",
            json={"base_snapshot_id": snapshot_id, "new_content": "x" * 2001},
        )

        assert response.status_code == 422
        anyio.run(delete_run, run_id)

    def test_edit_rejects_non_slide_deck_snapshot(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_run_with_snapshot, run_id, snapshot_id)

        response = client.patch(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title",
            json={"base_snapshot_id": snapshot_id, "new_content": "New body."},
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "not_a_slide_deck"
        anyio.run(delete_run, run_id)

    def test_non_owner_cannot_edit_slide_deck_block(
        self,
        other_teacher_client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        response = other_teacher_client.patch(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title",
            json={"base_snapshot_id": snapshot_id, "new_content": "New body."},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "run_not_found"
        anyio.run(delete_run, run_id)


async def _get_snapshot(run_id: RunId, snapshot_id: str) -> ArtifactSnapshotRead:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        snapshot = await TeachingPackSnapshotStore(session).get_snapshot(run_id, snapshot_id)
    await engine.dispose()
    assert snapshot is not None
    return snapshot


def _block_body(snapshot: ArtifactSnapshotRead) -> str:
    deck = snapshot.content_json["metadata"]["slide_deck_data"]
    return deck["slides"][0]["blocks"][0]["body"]

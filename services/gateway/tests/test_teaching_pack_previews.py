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


class TestSlideDeckBlockRewriteSuggestion:
    """SDE-08: AI-assisted rewrite CANDIDATE endpoint -- returns a before/after
    pair and never persists anything (no new snapshot, no version-history
    row) until the teacher separately calls the existing block-edit endpoint
    with `authority="ai_assisted_edit"` to Apply it.
    """

    def _stub_rewrite(self, monkeypatch, *, returns: str | None = "Shorter heading.") -> None:
        async def fake_rewrite(*, run_id: str, current_body: str, instruction: str) -> str | None:
            return returns

        monkeypatch.setattr(teaching_pack_previews, "generate_slide_deck_block_rewrite", fake_rewrite)

    def _suggestion_url(self, run_id: RunId, snapshot_id: str, block_id: str = "block-title") -> str:
        base = f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}"
        return f"{base}/blocks/{block_id}/rewrite-suggestion"

    def test_preset_returns_a_candidate_without_persisting(
        self, client: TestClient, monkeypatch,
    ) -> None:
        self._stub_rewrite(monkeypatch)
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        response = client.post(self._suggestion_url(run_id, snapshot_id), json={"preset": "shorter"})

        assert response.status_code == 200
        data = response.json()
        expected = {"block_id": "block-title", "before": "Fractions", "after": "Shorter heading."}
        assert data == expected
        # No new version was created -- this is a candidate only.
        versions_url = f"/teaching-packs/runs/{run_id}/artifacts/slide-deck-1/versions"
        versions = client.get(versions_url).json()
        assert versions["total"] == 1
        anyio.run(delete_run, run_id)

    def test_freeform_instruction_routes_through_the_same_endpoint_as_presets(
        self, client: TestClient, monkeypatch,
    ) -> None:
        self._stub_rewrite(monkeypatch, returns="Freeform-rewritten heading.")
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        response = client.post(
            self._suggestion_url(run_id, snapshot_id),
            json={"instruction": "Make it rhyme."},
        )

        assert response.status_code == 200
        assert response.json()["after"] == "Freeform-rewritten heading."
        anyio.run(delete_run, run_id)

    def test_unknown_preset_is_rejected(self, client: TestClient, monkeypatch) -> None:
        self._stub_rewrite(monkeypatch)
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        response = client.post(
            self._suggestion_url(run_id, snapshot_id),
            json={"preset": "not_a_real_preset"},
        )

        assert response.status_code == 422
        anyio.run(delete_run, run_id)

    def test_neither_preset_nor_instruction_is_rejected(
        self, client: TestClient, monkeypatch,
    ) -> None:
        self._stub_rewrite(monkeypatch)
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        response = client.post(self._suggestion_url(run_id, snapshot_id), json={})

        assert response.status_code == 422
        anyio.run(delete_run, run_id)

    def test_unknown_block_id_is_rejected(self, client: TestClient, monkeypatch) -> None:
        self._stub_rewrite(monkeypatch)
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        url = self._suggestion_url(run_id, snapshot_id, "block-does-not-exist")
        response = client.post(url, json={"preset": "shorter"})

        assert response.status_code == 404
        anyio.run(delete_run, run_id)

    def test_llm_unavailable_surfaces_as_502_not_a_silent_no_op_suggestion(
        self, client: TestClient, monkeypatch,
    ) -> None:
        self._stub_rewrite(monkeypatch, returns=None)
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        response = client.post(self._suggestion_url(run_id, snapshot_id), json={"preset": "shorter"})

        assert response.status_code == 502
        anyio.run(delete_run, run_id)

    def test_non_owner_cannot_request_rewrite_suggestion(
        self, other_teacher_client: TestClient, monkeypatch,
    ) -> None:
        self._stub_rewrite(monkeypatch)
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        response = other_teacher_client.post(
            self._suggestion_url(run_id, snapshot_id),
            json={"preset": "shorter"},
        )

        assert response.status_code == 404
        anyio.run(delete_run, run_id)


class TestArtifactVersionHistory:
    """SDE-05: linear, newest-first, paginated version list + restore, built on
    top of SDE-04's immutable snapshot lineage. Live-path-proof against the
    real gateway router, same convention as `TestSlideDeckBlockEdit`.
    """

    def test_version_list_is_newest_first_with_labels(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        manual = client.patch(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title",
            json={"base_snapshot_id": snapshot_id, "new_content": "Manually revised heading."},
        )
        assert manual.status_code == 200
        manual_snapshot_id = manual.json()["snapshot_id"]

        ai_edit = client.patch(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title",
            json={
                "base_snapshot_id": manual_snapshot_id,
                "new_content": "AI-shortened heading.",
                "rationale": "shorter",
                "authority": "ai_assisted_edit",
            },
        )
        assert ai_edit.status_code == 200

        response = client.get(f"/teaching-packs/runs/{run_id}/artifacts/slide-deck-1/versions")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        labels = [version["label"] for version in data["versions"]]
        # newest first: SDE-08's applied AI rewrite (authority="ai_assisted_edit")
        # gets its own "AI rewrite: <rationale>" label, distinct from the plain
        # "Manual edit" (default authority="teacher_edit") beneath it.
        assert labels == ["AI rewrite: shorter", "Manual edit", "Initial version"]
        assert data["versions"][0]["is_current"] is True
        assert data["versions"][0]["snapshot_id"] == ai_edit.json()["snapshot_id"]
        anyio.run(delete_run, run_id)

    def test_version_list_paginates(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)
        base = snapshot_id
        for i in range(4):
            edit = client.patch(
                f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title",
                json={"base_snapshot_id": base, "new_content": f"Revision {i}."},
            )
            assert edit.status_code == 200
            base = edit.json()["snapshot_id"]

        page1 = client.get(
            f"/teaching-packs/runs/{run_id}/artifacts/slide-deck-1/versions",
            params={"limit": 2, "offset": 0},
        ).json()
        page2 = client.get(
            f"/teaching-packs/runs/{run_id}/artifacts/slide-deck-1/versions",
            params={"limit": 2, "offset": 2},
        ).json()

        assert page1["total"] == 5
        assert len(page1["versions"]) == 2
        assert len(page2["versions"]) == 2
        # no overlap between pages, and page1 is strictly newer than page2
        assert {v["snapshot_id"] for v in page1["versions"]}.isdisjoint(
            {v["snapshot_id"] for v in page2["versions"]},
        )
        anyio.run(delete_run, run_id)

    def test_restore_creates_new_version_and_leaves_intervening_versions_untouched(
        self, client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        edit_one = client.patch(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title",
            json={"base_snapshot_id": snapshot_id, "new_content": "First revision."},
        )
        assert edit_one.status_code == 200
        edit_one_id = edit_one.json()["snapshot_id"]

        edit_two = client.patch(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title",
            json={"base_snapshot_id": edit_one_id, "new_content": "Second revision."},
        )
        assert edit_two.status_code == 200
        edit_two_id = edit_two.json()["snapshot_id"]

        before_restore_original = anyio.run(_get_snapshot, run_id, snapshot_id)
        before_restore_edit_one = anyio.run(_get_snapshot, run_id, edit_one_id)

        # Restore the very first (pre-edit) version, currently two versions behind head.
        restore = client.post(
            f"/teaching-packs/runs/{run_id}/artifacts/slide-deck-1/versions/{snapshot_id}/restore",
            json={"base_snapshot_id": edit_two_id},
        )
        assert restore.status_code == 200
        restored_data = restore.json()
        assert restored_data["restored_from_snapshot_id"] == snapshot_id
        restored_snapshot_id = restored_data["snapshot_id"]
        assert restored_snapshot_id not in (snapshot_id, edit_one_id, edit_two_id)

        # Intervening versions (original + edit_one + edit_two) are byte-identical.
        after_restore_original = anyio.run(_get_snapshot, run_id, snapshot_id)
        after_restore_edit_one = anyio.run(_get_snapshot, run_id, edit_one_id)
        assert after_restore_original.rendered_html == before_restore_original.rendered_html
        assert after_restore_original.content_json == before_restore_original.content_json
        assert after_restore_edit_one.rendered_html == before_restore_edit_one.rendered_html
        assert after_restore_edit_one.content_json == before_restore_edit_one.content_json

        # Restored content matches the original's visible content (heading body).
        restored_snapshot = anyio.run(_get_snapshot, run_id, restored_snapshot_id)
        assert _block_body(restored_snapshot) == "Fractions"

        # Restore-then-list shows the new version at the top.
        listing = client.get(f"/teaching-packs/runs/{run_id}/artifacts/slide-deck-1/versions").json()
        assert listing["versions"][0]["snapshot_id"] == restored_snapshot_id
        assert listing["versions"][0]["label"] == "Restored version"
        assert listing["versions"][0]["is_current"] is True
        assert listing["total"] == 4
        anyio.run(delete_run, run_id)

    def test_restore_returns_409_on_stale_base_snapshot_id(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        edit = client.patch(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title",
            json={"base_snapshot_id": snapshot_id, "new_content": "First revision."},
        )
        assert edit.status_code == 200

        # base_snapshot_id still points at the pre-edit head -- stale now.
        restore = client.post(
            f"/teaching-packs/runs/{run_id}/artifacts/slide-deck-1/versions/{snapshot_id}/restore",
            json={"base_snapshot_id": snapshot_id},
        )
        assert restore.status_code == 409
        assert restore.json()["detail"] == "base_snapshot_id_stale"
        anyio.run(delete_run, run_id)

    def test_restore_rejects_unknown_snapshot(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        restore = client.post(
            f"/teaching-packs/runs/{run_id}/artifacts/slide-deck-1/versions/does-not-exist/restore",
            json={"base_snapshot_id": snapshot_id},
        )
        assert restore.status_code == 404
        anyio.run(delete_run, run_id)

    def test_version_list_404s_for_unknown_artifact(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        response = client.get(f"/teaching-packs/runs/{run_id}/artifacts/does-not-exist/versions")
        assert response.status_code == 404
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

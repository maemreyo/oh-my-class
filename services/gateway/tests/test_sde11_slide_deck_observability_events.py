"""SDE-11: lightweight success observability for the slide-deck editor.

Hits the real `teaching_pack_previews.router` (same `client`/`other_teacher_client`
fixtures as `test_teaching_pack_previews.py`) so each new `ObservabilityEventType`
literal is proven reachable from the actual editor request path, not just
unit-tested against `write_observability_event` directly -- the "live-path
proof" ADR-032 requires. Events are read back via `TeachingPackRunStore.replay_events`,
the same durable `RunEvent` table the SDE-08/worker pipeline events persist
into, confirming these are genuinely queryable, not just held in the
in-memory `_event_store` that never gets drained for editor-triggered events.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import anyio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.routers import teaching_pack_previews
from services.gateway.teaching_pack_store import TeachingPackRunStore
from services.gateway.teaching_pack_types import JsonObject, RunId
from services.gateway.tests.teaching_pack_preview_db import DATABASE_URL
from services.gateway.tests.test_teaching_pack_previews import (
    _create_run_with_slide_deck_snapshot as create_slide_deck_run,
)
from services.gateway.tests.teaching_pack_preview_helpers import delete_run

if TYPE_CHECKING:
    from starlette.testclient import TestClient

pytest_plugins = ("services.gateway.tests.teaching_pack_preview_fixtures",)


async def _events_by_name(run_id: RunId) -> dict[str, JsonObject]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        events = await TeachingPackRunStore(session).replay_events(run_id)
    await engine.dispose()
    return {event.event_name: event.payload or {} for event in events}


# Every `payload["payload"]` key any SDE-11 event is allowed to carry --
# artifact/block ids and counts/timestamps only, never raw content or a
# student identifier. Used by the PII audit test below.
_ALLOWED_PAYLOAD_KEYS = frozenset({"artifact_id", "block_id"})


class TestSlideDeckEditObservabilityEvents:
    def test_edit_within_24h_of_generation_emits_event(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_slide_deck_run, run_id, snapshot_id)

        response = client.patch(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title",
            json={"base_snapshot_id": snapshot_id, "new_content": "Teacher-revised heading."},
        )

        assert response.status_code == 200
        events = anyio.run(_events_by_name, run_id)
        assert "slide_deck_edited_within_24h" in events
        payload = events["slide_deck_edited_within_24h"]
        assert payload["teacher_id"] == "teacher-preview"
        assert payload["payload"] == {"artifact_id": "slide-deck-1", "block_id": "block-title"}
        anyio.run(delete_run, run_id)

    def test_second_edit_on_the_same_deck_emits_return_usage_event(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_slide_deck_run, run_id, snapshot_id)

        first = client.patch(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title",
            json={"base_snapshot_id": snapshot_id, "new_content": "First revision."},
        )
        assert first.status_code == 200
        events_after_first = anyio.run(_events_by_name, run_id)
        assert "slide_deck_editor_return_usage" not in events_after_first

        second_base = first.json()["snapshot_id"]
        second = client.patch(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title",
            json={"base_snapshot_id": second_base, "new_content": "Second revision."},
        )
        assert second.status_code == 200

        events_after_second = anyio.run(_events_by_name, run_id)
        assert "slide_deck_editor_return_usage" in events_after_second
        anyio.run(delete_run, run_id)

    def test_ai_assisted_apply_emits_accepted_event(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_slide_deck_run, run_id, snapshot_id)

        response = client.patch(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title",
            json={
                "base_snapshot_id": snapshot_id,
                "new_content": "AI-rewritten heading.",
                "authority": "ai_assisted_edit",
            },
        )

        assert response.status_code == 200
        events = anyio.run(_events_by_name, run_id)
        assert "slide_deck_ai_rewrite_accepted" in events
        anyio.run(delete_run, run_id)

    def test_manual_edit_does_not_emit_accepted_event(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_slide_deck_run, run_id, snapshot_id)

        response = client.patch(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title",
            json={"base_snapshot_id": snapshot_id, "new_content": "Manual edit."},
        )

        assert response.status_code == 200
        events = anyio.run(_events_by_name, run_id)
        assert "slide_deck_ai_rewrite_accepted" not in events
        anyio.run(delete_run, run_id)

    def test_rewrite_suggestion_emits_suggested_event(self, client: TestClient, monkeypatch) -> None:
        async def fake_rewrite(*, run_id: str, current_body: str, instruction: str) -> str:
            return "Shorter heading."

        monkeypatch.setattr(teaching_pack_previews, "generate_slide_deck_block_rewrite", fake_rewrite)

        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_slide_deck_run, run_id, snapshot_id)

        response = client.post(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title/rewrite-suggestion",
            json={"preset": "shorter"},
        )

        assert response.status_code == 200
        events = anyio.run(_events_by_name, run_id)
        assert "slide_deck_ai_rewrite_suggested" in events
        anyio.run(delete_run, run_id)

    def test_cancel_endpoint_emits_cancelled_event(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_slide_deck_run, run_id, snapshot_id)

        response = client.post(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title/rewrite-suggestion/cancelled",
        )

        assert response.status_code == 200
        assert response.json() == {"acknowledged": True}
        events = anyio.run(_events_by_name, run_id)
        assert "slide_deck_ai_rewrite_cancelled" in events
        anyio.run(delete_run, run_id)

    def test_cancel_endpoint_rejects_non_owner(self, other_teacher_client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_slide_deck_run, run_id, snapshot_id)

        response = other_teacher_client.post(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title/rewrite-suggestion/cancelled",
        )

        assert response.status_code == 404
        anyio.run(delete_run, run_id)

    def test_cancel_endpoint_rejects_unknown_snapshot(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_slide_deck_run, run_id, snapshot_id)

        response = client.post(
            f"/teaching-packs/runs/{run_id}/snapshots/does-not-exist/blocks/block-title/rewrite-suggestion/cancelled",
        )

        assert response.status_code == 404
        anyio.run(delete_run, run_id)

    def test_no_sde11_event_payload_carries_student_pii_or_free_text(
        self, client: TestClient, monkeypatch,
    ) -> None:
        """AC4: every SDE-11 event is teacher/deck/session-scoped counts and
        timestamps only -- audits the actual persisted rows across every
        SDE-11 code path in one pass, not just a schema-shape assertion."""

        async def fake_rewrite(*, run_id: str, current_body: str, instruction: str) -> str:
            return "Shorter heading."

        monkeypatch.setattr(teaching_pack_previews, "generate_slide_deck_block_rewrite", fake_rewrite)

        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(create_slide_deck_run, run_id, snapshot_id)

        client.patch(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title",
            json={
                "base_snapshot_id": snapshot_id,
                "new_content": "A very student-specific rationale should never end up here.",
                "authority": "ai_assisted_edit",
                "rationale": "Jane Doe (student) requested this exact wording change",
            },
        )
        client.post(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title/rewrite-suggestion",
            json={"preset": "shorter"},
        )
        client.post(
            f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/block-title/rewrite-suggestion/cancelled",
        )

        events = anyio.run(_events_by_name, run_id)
        sde11_event_names = {
            "slide_deck_edited_within_24h",
            "slide_deck_ai_rewrite_suggested",
            "slide_deck_ai_rewrite_accepted",
            "slide_deck_ai_rewrite_cancelled",
        }
        checked = 0
        for event_name in sde11_event_names:
            row = events.get(event_name)
            if row is None:
                continue
            checked += 1
            inner_payload = row.get("payload")
            assert isinstance(inner_payload, dict)
            assert set(inner_payload).issubset(_ALLOWED_PAYLOAD_KEYS)
            serialized = str(row)
            assert "Jane Doe" not in serialized
            assert "rationale" not in inner_payload
            assert "new_content" not in inner_payload
            assert "body" not in inner_payload
        assert checked >= 3  # 24h + suggested + accepted + cancelled all fired above
        anyio.run(delete_run, run_id)

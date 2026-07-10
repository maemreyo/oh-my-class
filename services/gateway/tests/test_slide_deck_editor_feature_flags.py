"""SDE-10: independent feature flags for manual edit / AI rewrite, and the
per-teacher call-count rate limit on AI rewrite.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import anyio
import pytest

from packages.agents.config.features import reset_features
from services.gateway.routers import teaching_pack_previews
from services.gateway.teaching_pack_types import RunId
from services.gateway.tests.teaching_pack_preview_helpers import delete_run
from services.gateway.tests.test_teaching_pack_previews import _create_run_with_slide_deck_snapshot

if TYPE_CHECKING:
    from starlette.testclient import TestClient

pytest_plugins = ("services.gateway.tests.teaching_pack_preview_fixtures",)


def _stub_rewrite(monkeypatch: pytest.MonkeyPatch, *, returns: str | None = "Shorter heading.") -> None:
    async def fake_rewrite(*, run_id: str, current_body: str, instruction: str) -> str | None:
        return returns

    monkeypatch.setattr(teaching_pack_previews, "generate_slide_deck_block_rewrite", fake_rewrite)


def _edit_url(run_id: RunId, snapshot_id: str, block_id: str = "block-title") -> str:
    return f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/{block_id}"


def _suggestion_url(run_id: RunId, snapshot_id: str, block_id: str = "block-title") -> str:
    return f"{_edit_url(run_id, snapshot_id, block_id)}/rewrite-suggestion"


class TestIndependentFeatureFlags:
    def test_manual_edit_is_gated_off_when_editor_flag_disabled(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        monkeypatch.setenv("FEATURE_SLIDE_DECK_EDITOR_V1", "false")
        reset_features()

        response = client.patch(
            _edit_url(run_id, snapshot_id),
            json={"base_snapshot_id": snapshot_id, "new_content": "New body."},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "slide_deck_editor_disabled"
        anyio.run(delete_run, run_id)

    def test_manual_edit_still_works_when_only_ai_rewrite_flag_disabled(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        monkeypatch.setenv("FEATURE_SLIDE_DECK_AI_REWRITE_V1", "false")
        reset_features()

        response = client.patch(
            _edit_url(run_id, snapshot_id),
            json={"base_snapshot_id": snapshot_id, "new_content": "New body."},
        )

        assert response.status_code == 200
        anyio.run(delete_run, run_id)

    def test_applying_an_ai_rewrite_is_gated_off_when_ai_rewrite_flag_disabled(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        monkeypatch.setenv("FEATURE_SLIDE_DECK_AI_REWRITE_V1", "false")
        reset_features()

        response = client.patch(
            _edit_url(run_id, snapshot_id),
            json={
                "base_snapshot_id": snapshot_id,
                "new_content": "AI-suggested body.",
                "authority": "ai_assisted_edit",
            },
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "slide_deck_ai_rewrite_disabled"
        anyio.run(delete_run, run_id)

    def test_rewrite_suggestion_is_gated_off_when_ai_rewrite_flag_disabled(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _stub_rewrite(monkeypatch)
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        monkeypatch.setenv("FEATURE_SLIDE_DECK_AI_REWRITE_V1", "false")
        reset_features()

        response = client.post(_suggestion_url(run_id, snapshot_id), json={"preset": "shorter"})

        assert response.status_code == 403
        assert response.json()["detail"] == "slide_deck_ai_rewrite_disabled"
        anyio.run(delete_run, run_id)

    def test_rewrite_suggestion_is_gated_off_when_editor_flag_disabled(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The editor flag being off gates AI rewrite too (compositional: you
        can't AI-rewrite if the editor itself is disabled), even though the
        AI-rewrite flag alone is still on."""
        _stub_rewrite(monkeypatch)
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        monkeypatch.setenv("FEATURE_SLIDE_DECK_EDITOR_V1", "false")
        reset_features()

        response = client.post(_suggestion_url(run_id, snapshot_id), json={"preset": "shorter"})

        assert response.status_code == 403
        assert response.json()["detail"] == "slide_deck_ai_rewrite_disabled"
        anyio.run(delete_run, run_id)


class TestAiRewriteRateLimit:
    def test_exceeding_the_call_count_limit_returns_a_teacher_safe_429(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _stub_rewrite(monkeypatch)
        monkeypatch.setenv("SLIDE_DECK_AI_REWRITE_RATE_LIMIT_COUNT", "1")
        monkeypatch.setenv("SLIDE_DECK_AI_REWRITE_RATE_LIMIT_WINDOW_SECONDS", "3600")
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_slide_deck_snapshot, run_id, snapshot_id)

        first = client.post(_suggestion_url(run_id, snapshot_id), json={"preset": "shorter"})
        second = client.post(_suggestion_url(run_id, snapshot_id), json={"preset": "shorter"})

        assert first.status_code == 200
        assert second.status_code == 429
        # Teacher-safe: a plain classification code, never a raw exception/stack trace.
        detail = second.json()["detail"]
        assert detail == "ai_rewrite_rate_limited"
        assert "Traceback" not in detail
        anyio.run(delete_run, run_id)

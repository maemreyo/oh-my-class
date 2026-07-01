"""Tests for GET /units/{parent_run_id}/status SSE endpoint (td-011).

Tests use mocked event bus so no real DB or LLM required.
Run: uv run pytest services/gateway/tests/test_unit_stream.py -v
"""
from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import anyio
from fastapi import FastAPI
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.routers.unit_runs import router
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_models import TeachingPackEventVisibility

_TEACHER_ID = "teacher-stream-001"
_PARENT_RUN_ID = str(uuid4())


def _mock_teacher() -> User:
    return User(user_id=_TEACHER_ID, username="teacher-stream", email="teacher@test.com", role=Role.TEACHER)


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/teaching-packs")
    return app


class TestSSEHeartbeat:
    def test_sse_sends_heartbeat_comment(self) -> None:
        """SSE endpoint must emit heartbeat comments (": heartbeat") periodically."""
        from services.gateway.teaching_pack_types import RunId
        from services.gateway.routers.teaching_pack_stream import (
            TeachingPackStreamRequest,
            stream_visible_run_events,
        )

        class EmptyStore:
            async def replay_events(self, _run_id: RunId, after_sequence: int = 0):
                assert after_sequence == 0
                return []

        async def _fake_wait_for_run_event(
            _run_id: RunId,
            _observed_version: int,
            timeout_seconds: float,
        ) -> bool:
            assert timeout_seconds == 15.0
            await anyio.sleep(0)
            return False

        async def _read_first_event() -> str:
            with (
                patch("services.gateway.routers.teaching_pack_stream.current_run_event_version", return_value=0),
                patch("services.gateway.routers.teaching_pack_stream.wait_for_run_event", _fake_wait_for_run_event),
            ):
                stream = stream_visible_run_events(
                    EmptyStore(),
                    TeachingPackStreamRequest(
                        run_id=RunId(_PARENT_RUN_ID),
                        after_sequence=0,
                        replay_only=False,
                    ),
                )
                return await anext(stream)

        assert anyio.run(_read_first_event) == ": heartbeat\n\n"


class TestSSECursorFilter:
    def test_stale_events_not_emitted(self) -> None:
        """When wait_for_run_event returns an event with cursor <= query cursor, it is suppressed."""
        app = _build_app()
        mock_session = AsyncMock()

        async def _fake_get_parent_run_owned(_parent_run_id, _user, _session):
            return MagicMock()

        @dataclass(frozen=True, slots=True)
        class Event:
            run_id: str
            sequence: int
            event_name: str
            visibility: TeachingPackEventVisibility
            payload: dict[str, str]

        class ReplayStore:
            async def replay_events(self, run_id, after_sequence: int = 0):
                assert after_sequence == 5
                return [Event(
                    run_id=str(run_id),
                    sequence=6,
                    event_name="unit.session.spawned",
                    visibility=TeachingPackEventVisibility.TEACHER,
                    payload={"event_type": "unit.progress"},
                )]

        async def _stream_visible_run_events(store, request):
            assert isinstance(store, ReplayStore)
            assert request.after_sequence == 5
            yield "event: unit.session.spawned\ndata: {}\n\n"

        class _FakeTeachingPackRunStore:
            def __new__(cls, session):
                return ReplayStore()

        async def _override_session():
            yield mock_session

        with (
            patch("services.gateway.routers.unit_runs._get_parent_run_owned", _fake_get_parent_run_owned),
            patch("services.gateway.routers.unit_runs.TeachingPackRunStore", _FakeTeachingPackRunStore),
            patch("services.gateway.routers.unit_runs.stream_visible_run_events", _stream_visible_run_events),
        ):
            app.dependency_overrides[get_teaching_pack_session] = _override_session
            app.dependency_overrides[require_teacher] = lambda: _mock_teacher()

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get(
                f"/teaching-packs/units/{_PARENT_RUN_ID}/status",
                params={"cursor": 5},
            )
            assert resp.status_code == 200
            assert resp.text == "event: unit.session.spawned\ndata: {}\n\n"


class TestSSEOwnership:
    def test_sse_returns_404_for_unknown_run(self) -> None:
        app = _build_app()
        mock_session = AsyncMock()

        async def _raise_not_found(_parent_run_id, _user, _session):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Run not found")

        async def _override_session():
            yield mock_session

        with patch("services.gateway.routers.unit_runs._get_parent_run_owned", _raise_not_found):
            app.dependency_overrides[get_teaching_pack_session] = _override_session
            app.dependency_overrides[require_teacher] = lambda: _mock_teacher()

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get(f"/teaching-packs/units/nonexistent-id/status")
            assert resp.status_code == 404

    def test_sse_returns_403_for_wrong_owner(self) -> None:
        app = _build_app()
        mock_session = AsyncMock()

        async def _raise_forbidden(_parent_run_id, _user, _session):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Forbidden")

        async def _override_session():
            yield mock_session

        with patch("services.gateway.routers.unit_runs._get_parent_run_owned", _raise_forbidden):
            app.dependency_overrides[get_teaching_pack_session] = _override_session
            app.dependency_overrides[require_teacher] = lambda: _mock_teacher()

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get(f"/teaching-packs/units/{_PARENT_RUN_ID}/status")
            assert resp.status_code in (403, 404)

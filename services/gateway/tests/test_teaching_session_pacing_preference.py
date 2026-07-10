"""TSP-04 amendment #2: the pacing-nudge preference is opt-in, never default-on.

Unlike `test_teaching_session_live_router.py` (which needs real Postgres/
Redis for the session-token-gated routes), these two routes are gated by the
plain teacher account JWT and read/write an in-memory `BaseStore` -- no DB
needed, so this stays a fast unit test.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from langgraph.store.memory import InMemoryStore
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.routers.teaching_session_live import router

if TYPE_CHECKING:
    from collections.abc import Iterator

TEACHER = User(user_id="teacher-1", username="teacher-1", role=Role.TEACHER)
OTHER_TEACHER = User(user_id="teacher-2", username="teacher-2", role=Role.TEACHER)


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(router, prefix="/teaching-sessions")
    app.state.store = InMemoryStore()
    app.dependency_overrides[require_teacher] = lambda: TEACHER
    with TestClient(app) as test_client:
        yield test_client


def test_pacing_nudge_defaults_disabled(client: TestClient) -> None:
    response = client.get("/teaching-sessions/preferences/pacing-nudge")
    assert response.status_code == 200
    assert response.json() == {"enabled": False}


def test_pacing_nudge_opt_in_roundtrips(client: TestClient) -> None:
    put_response = client.put("/teaching-sessions/preferences/pacing-nudge", json={"enabled": True})
    assert put_response.status_code == 200
    assert put_response.json() == {"enabled": True}

    get_response = client.get("/teaching-sessions/preferences/pacing-nudge")
    assert get_response.json() == {"enabled": True}


def test_pacing_nudge_preference_is_per_teacher(client: TestClient) -> None:
    client.put("/teaching-sessions/preferences/pacing-nudge", json={"enabled": True})

    client.app.dependency_overrides[require_teacher] = lambda: OTHER_TEACHER  # type: ignore[attr-defined]
    response = client.get("/teaching-sessions/preferences/pacing-nudge")
    assert response.json() == {"enabled": False}

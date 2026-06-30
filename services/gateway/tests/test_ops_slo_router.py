from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import require_admin
from services.gateway.auth.models import Role, User
from services.gateway.routers.ops import router
from services.gateway.slo_metrics import SloDimension, SloSnapshot
from services.gateway.teaching_pack_db import get_teaching_pack_session

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(router)

    async def fake_snapshot(_session) -> SloSnapshot:
        now = datetime(2026, 6, 30, 8, tzinfo=UTC)
        return SloSnapshot(
            generated_at=now,
            window_started_at=now - timedelta(hours=24),
            global_dimension=SloDimension(
                name="global",
                teacher_id=None,
                run_count=1,
                success_rate=1.0,
                run_latency_p95_seconds=12.0,
                stage_latency_p95_seconds={},
                gate_backlog=0,
                queue_depth=0,
                cost_usd_today=0.25,
            ),
        )

    async def fake_session() -> None:
        return None

    monkeypatch.setattr("services.gateway.routers.ops.compute_slo_snapshot", fake_snapshot)
    app.dependency_overrides[require_admin] = lambda: User(
        user_id="admin-slo",
        username="admin-slo",
        role=Role.SYSTEM_ADMIN,
    )
    app.dependency_overrides[get_teaching_pack_session] = fake_session
    with TestClient(app) as test_client:
        yield test_client


class TestOpsSloRouter:
    def test_admin_can_read_slo_dashboard_payload(self, client: TestClient) -> None:
        response = client.get("/ops/slo")

        assert response.status_code == 200
        body = response.json()
        assert body["global_dimension"]["success_rate"] == 1.0
        assert body["global_dimension"]["run_latency_p95_seconds"] == 12.0
        assert body["global_dimension"]["cost_usd_today"] == 0.25

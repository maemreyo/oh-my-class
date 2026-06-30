from __future__ import annotations

import importlib.util

from fastapi import FastAPI
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.routers import approvals, runs


def _legacy_client() -> TestClient:
    app = FastAPI()
    app.state.runs = {}
    app.include_router(runs.router, prefix="/run")
    app.include_router(approvals.router, prefix="/run")
    app.dependency_overrides[require_teacher] = lambda: User(
        user_id="teacher-legacy",
        username="teacher-legacy",
        role=Role.TEACHER,
    )
    return TestClient(app)


class TestNoLegacyRuntime:
    def test_legacy_graph_module_is_removed(self) -> None:
        assert importlib.util.find_spec("packages.agents.graph") is None

    def test_legacy_create_run_returns_410(self) -> None:
        response = _legacy_client().post("/run", json={
            "raw_request": "Teach fractions",
            "class_info": {"grade": 5},
            "teacher_id": "ignored",
        })

        assert response.status_code == 410
        assert "decommissioned" in response.json()["detail"]

    def test_legacy_approval_routes_return_410(self) -> None:
        client = _legacy_client()

        approve = client.post("/run/run-1/approve", json={"action": "approve"})
        reject = client.post("/run/run-1/reject", json={"action": "reject", "feedback": "No"})

        assert approve.status_code == 410
        assert reject.status_code == 410

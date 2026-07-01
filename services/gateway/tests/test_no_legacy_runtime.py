from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi import FastAPI
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.routers import approvals, runs


ROOT = Path(__file__).resolve().parents[3]
LIVE_PYTHON_ROOTS = (ROOT / "packages", ROOT / "services")
LEGACY_GRAPH_PATTERNS = (
    "build_oh_my_class_graph",
    "packages.agents.graph",
    "app.state.graph",
    "state.graph",
)


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

    def test_live_code_does_not_reference_legacy_graph_runtime(self) -> None:
        offenders: list[str] = []
        for root in LIVE_PYTHON_ROOTS:
            for file_path in root.rglob("*.py"):
                if "__pycache__" in file_path.parts or "tests" in file_path.parts:
                    continue
                source = file_path.read_text(encoding="utf-8")
                for pattern in LEGACY_GRAPH_PATTERNS:
                    if pattern in source:
                        offenders.append(f"{file_path.relative_to(ROOT)} references {pattern}")

        assert offenders == []

    def test_gateway_app_exposes_only_teaching_pack_graph(self) -> None:
        from services.gateway.main import app

        assert not hasattr(app.state, "graph")
        assert not hasattr(app.state, "legacy_graph")

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

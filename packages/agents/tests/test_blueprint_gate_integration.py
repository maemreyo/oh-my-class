"""Integration tests for pipeline graph → reaching blueprint approval gate.

Validates that preflight + quickstart + planner reach `gate_01_blueprint_approval`
with a schema-valid LessonPlan, and that preflight failures bubble to a
structured PipelineError via the gateway.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# jwt is not installed in the test environment — inject before gateway imports
if "jwt" not in sys.modules:
    sys.modules["jwt"] = MagicMock()

from services.gateway.auth.models import Role, User  # noqa: E402
from services.gateway.middleware.error_handler import register_exception_handlers  # noqa: E402
from services.gateway.routers.runs import (  # noqa: E402
    _derive_status,
    router,
)

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState

VALID_PLAN = json.dumps({
    "topic": "Photosynthesis",
    "grade_level": "Grade 5",
    "subject": "science",
    "duration_minutes": 45,
    "learning_objectives": [
        {"description": "Understand photosynthesis", "bloom_level": "understand"},
        {"description": "Apply knowledge", "bloom_level": "apply"},
    ],
})


def _make_llm_mock(content: str) -> AsyncMock:
    return AsyncMock(return_value=content)


def _build_real_graph():
    """Compile the real LangGraph with the shared LLM helper mocked."""
    mock_llm = _make_llm_mock(VALID_PLAN)
    with (
        patch("packages.agents.llm.compiled_chat.complete_json_chat", mock_llm),
        patch("packages.agents.llm.complete_json_chat", mock_llm),
    ):
        from packages.agents.graph import build_oh_my_class_graph
        return build_oh_my_class_graph()


def _initial_state(raw_request: str = "Teach photosynthesis to Grade 5") -> dict[str, Any]:
    return {
        "raw_request": raw_request,
        "teacher_id": "t-001",
        "class_info": {"grade": 5, "subject": "science"},
        "run_id": "run-test-001",
        "blueprint_approved": False,
        "research_policy": "standard",
        "artifact_types": [],
        "theme": "default",
        "artifacts": [],
        "quality_passed": False,
        "teacher_approved": False,
        "revision_count": 0,
        "export_formats": ["html"],
        "exported_files": [],
        "current_step": 1,
        "tokens_used": 0,
        "cost_usd": 0.0,
    }


# ── Graph-level integration ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_graph_reaches_blueprint_approval_with_lesson_plan():
    """Full preflight → quickstart → planner → gate_01 sequence."""
    mock_llm = _make_llm_mock(VALID_PLAN)
    with (
        patch("packages.agents.llm.compiled_chat.complete_json_chat", mock_llm),
        patch("packages.agents.llm.complete_json_chat", mock_llm),
    ):
        from packages.agents.graph import build_oh_my_class_graph

        graph = build_oh_my_class_graph()
        # LangGraph interrupt() halts at gate_01 — ainvoke returns the state at halt
        state = await graph.ainvoke(
            _initial_state(),
            config={"configurable": {"thread_id": "test-thread"}},
        )

    # Planner succeeded
    assert state.get("lesson_plan") is not None
    assert state["lesson_plan"]["topic"] == "Photosynthesis"

    # Quickstart populated defaults
    assert state.get("artifact_types") == ["lesson", "worksheet", "quiz"]
    assert state.get("theme") == "default"
    assert state.get("research_policy") == "standard"

    # Status mapping: lesson_plan present → awaiting_approval
    assert _derive_status(state) == "awaiting_approval"


@pytest.mark.asyncio
async def test_preflight_node_rejects_short_request_in_graph():
    """Preflight raises ValueError before planner runs."""
    from packages.agents.nodes.preflight import step_01_preflight

    short_state = _initial_state(raw_request="hi")
    with pytest.raises(ValueError, match="at least 10 characters"):
        step_01_preflight(cast("OhMyClassState", short_state))


@pytest.mark.asyncio
async def test_preflight_node_rejects_empty_request_in_graph():
    from packages.agents.nodes.preflight import step_01_preflight

    empty_state = _initial_state(raw_request="")
    with pytest.raises(ValueError, match="raw_request is required"):
        step_01_preflight(cast("OhMyClassState", empty_state))


# ── Gateway-level integration ─────────────────────────────────────────────────


def _make_teacher() -> User:
    return User(user_id="t-001", username="teacher1", role=Role.TEACHER)


def _make_app_with_graph(graph: Any) -> TestClient:
    from services.gateway.auth.dependencies import require_teacher

    app = FastAPI()
    app.include_router(router, prefix="/run")
    register_exception_handlers(app)
    app.state.graph = graph
    app.state.runs = {}
    app.dependency_overrides[require_teacher] = lambda: _make_teacher()
    return TestClient(app)


def test_create_run_reaches_blueprint_approval_via_gateway():
    """POST /run with mocked LLM → 200 + status 'awaiting_approval' + lesson_plan in state."""
    mock_llm = _make_llm_mock(VALID_PLAN)
    with (
        patch("packages.agents.llm.compiled_chat.complete_json_chat", mock_llm),
        patch("packages.agents.llm.complete_json_chat", mock_llm),
    ):
        from packages.agents.graph import build_oh_my_class_graph

        graph = build_oh_my_class_graph()
        client = _make_app_with_graph(graph)

        response = client.post("/run", json={
            "raw_request": "Teach photosynthesis to Grade 5",
            "class_info": {"grade": 5, "subject": "science"},
            "teacher_id": "t-001",
        })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "awaiting_approval"
    assert data["state"]["lesson_plan"]["topic"] == "Photosynthesis"


def test_create_run_preflight_rejects_empty_request():
    """POST /run with empty raw_request → preflight ValueError → 500 PIPELINE_ERROR."""
    # Use a simple mock graph that mimics preflight's ValueError
    failing_graph = MagicMock()

    async def _raise_preflight(state: dict[str, Any], config: Any = None) -> dict[str, Any]:
        raise ValueError("raw_request is required and cannot be empty")

    failing_graph.ainvoke = AsyncMock(side_effect=_raise_preflight)

    client = _make_app_with_graph(failing_graph)
    response = client.post("/run", json={
        "raw_request": "",
        "class_info": {"grade": 5},
        "teacher_id": "t-001",
    })
    assert response.status_code == 500
    data = response.json()
    assert data["error_code"] == "PIPELINE_ERROR"

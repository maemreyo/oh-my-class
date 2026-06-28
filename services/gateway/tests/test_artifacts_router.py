"""Tests for artifacts_router — artifact retrieval endpoints."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from fastapi import FastAPI
from starlette.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# jwt is not installed in the test environment — inject before gateway imports
if "jwt" not in sys.modules:
    sys.modules["jwt"] = MagicMock()

from services.gateway.auth.models import Role, User  # noqa: E402
from services.gateway.middleware.error_handler import register_exception_handlers  # noqa: E402
from services.gateway.routers.artifacts import (  # noqa: E402
    ArtifactResponse,
    _extract_artifacts_from_state,
    _redact_teacher_only,
    router,
)

# ── helpers ───────────────────────────────────────────────────────────────────

SAMPLE_ARTIFACT: dict[str, Any] = {
    "artifact_type": "lesson",
    "title": "Photosynthesis Basics",
    "theme": "default",
    "sections": [
        {"heading": "Introduction", "content": "What is photosynthesis?"},
        {"heading": "Key Terms", "content": "Chlorophyll, sunlight, CO2"},
    ],
    "metadata": {"grade": 5, "subject": "science"},
    "accessibility": {"reading_level": "grade 5", "language": "en"},
}

TEACHER_ONLY_ARTIFACT: dict[str, Any] = {
    "artifact_type": "quiz",
    "title": "Photosynthesis Quiz",
    "theme": "ocean",
    "sections": [
        {"heading": "Question 1", "content": "What captures sunlight?"},
        {"heading": "Answer Key", "content": "Chlorophyll", "teacher_only": True},
    ],
    "metadata": {"grade": 5, "subject": "science"},
    "accessibility": {"reading_level": "grade 5", "language": "en"},
}


def _make_teacher(user_id: str = "t-001", username: str = "teacher1") -> User:
    return User(user_id=user_id, username=username, role=Role.TEACHER)


def _make_app_with_auth() -> TestClient:
    from services.gateway.auth.dependencies import require_teacher

    app = FastAPI()
    app.include_router(router, prefix="/run")
    register_exception_handlers(app)
    app.state.runs = {}

    teacher = _make_teacher()
    app.dependency_overrides[require_teacher] = lambda: teacher
    return TestClient(app)


def _seed_run(
    client: TestClient,
    run_id: str,
    artifacts: list[dict[str, Any]],
) -> None:
    """Insert a run into the app state with given artifacts."""
    app: FastAPI = client.app  # type: ignore[assignment]
    app.state.runs[run_id] = {
        "run_id": run_id,
        "status": "completed",
        "state": {"artifacts": artifacts, "current_step": 13},
        "teacher_id": "t-001",
        "created_at": "2026-01-01T00:00:00",
    }


# ── list_artifacts ────────────────────────────────────────────────────────────


class TestListArtifacts:
    def test_list_artifacts_returns_empty_when_no_artifacts(self) -> None:
        """Run with no artifacts → empty list."""
        client = _make_app_with_auth()
        _seed_run(client, "run-empty", [])
        response = client.get("/run/run-empty/artifacts")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_artifacts_returns_artifacts(self) -> None:
        """Run with artifacts → list of artifact responses."""
        client = _make_app_with_auth()
        _seed_run(client, "run-arts", [SAMPLE_ARTIFACT])
        response = client.get("/run/run-arts/artifacts")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Photosynthesis Basics"
        assert data[0]["artifact_type"] == "lesson"
        assert data[0]["artifact_id"] == "artifact-0"

    def test_list_artifacts_not_found_returns_404(self) -> None:
        """Unknown run → 404."""
        client = _make_app_with_auth()
        response = client.get("/run/nonexistent-run/artifacts")
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "NOT_FOUND"

    def test_list_artifacts_generates_sequential_ids(self) -> None:
        """Artifacts without IDs get auto-generated sequential IDs."""
        client = _make_app_with_auth()
        _seed_run(client, "run-multi", [SAMPLE_ARTIFACT, SAMPLE_ARTIFACT])
        response = client.get("/run/run-multi/artifacts")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["artifact_id"] == "artifact-0"
        assert data[1]["artifact_id"] == "artifact-1"


# ── get_artifact ──────────────────────────────────────────────────────────────


class TestGetArtifact:
    def test_get_artifact_returns_artifact(self) -> None:
        """Fetch specific artifact by ID → artifact response."""
        client = _make_app_with_auth()
        _seed_run(client, "run-one", [SAMPLE_ARTIFACT])
        response = client.get("/run/run-one/artifacts/artifact-0")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Photosynthesis Basics"
        assert data["artifact_id"] == "artifact-0"
        assert data["artifact_type"] == "lesson"

    def test_get_artifact_not_found_returns_404(self) -> None:
        """Unknown artifact → 404."""
        client = _make_app_with_auth()
        _seed_run(client, "run-one", [SAMPLE_ARTIFACT])
        response = client.get("/run/run-one/artifacts/artifact-99")
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "NOT_FOUND"
        assert "artifact-99" in data["message"]

    def test_get_artifact_run_not_found_returns_404(self) -> None:
        """Unknown run → 404."""
        client = _make_app_with_auth()
        response = client.get("/run/nonexistent/artifacts/artifact-0")
        assert response.status_code == 404


# ── schema ────────────────────────────────────────────────────────────────────


class TestArtifactSchema:
    def test_artifact_response_has_required_fields(self) -> None:
        """Verify ArtifactResponse schema has all required fields."""
        response = ArtifactResponse(
            artifact_id="a-1",
            artifact_type="lesson",
            title="Test Lesson",
            theme="default",
            sections=[],
            metadata={},
            accessibility={},
        )
        assert response.artifact_id == "a-1"
        assert response.artifact_type == "lesson"
        assert response.title == "Test Lesson"
        assert response.theme == "default"
        assert response.rendered_html is None  # optional field defaults to None

    def test_artifact_response_renders_html_optional(self) -> None:
        """rendered_html is optional."""
        response = ArtifactResponse(
            artifact_id="a-2",
            artifact_type="quiz",
            title="Quiz",
            theme="ocean",
            sections=[],
            metadata={},
            accessibility={},
            rendered_html="<html>...</html>",
        )
        assert response.rendered_html == "<html>...</html>"


# ── teacher-only redaction ───────────────────────────────────────────────────


class TestTeacherOnlyRedaction:
    def test_teacher_only_sections_are_redacted(self) -> None:
        """Artifact with teacher_only section → filtered out."""
        client = _make_app_with_auth()
        _seed_run(client, "run-quiz", [TEACHER_ONLY_ARTIFACT])
        response = client.get("/run/run-quiz/artifacts/artifact-0")
        assert response.status_code == 200
        data = response.json()
        # Answer Key section should be removed
        section_headings = [s["heading"] for s in data["sections"]]
        assert "Answer Key" not in section_headings
        assert len(data["sections"]) == 1
        assert data["sections"][0]["heading"] == "Question 1"

    def test_teacher_only_in_list_redacted(self) -> None:
        """Teacher-only sections also redacted in list endpoint."""
        client = _make_app_with_auth()
        _seed_run(client, "run-list-quiz", [TEACHER_ONLY_ARTIFACT])
        response = client.get("/run/run-list-quiz/artifacts")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        section_headings = [s["heading"] for s in data[0]["sections"]]
        assert "Answer Key" not in section_headings


# ── unit tests for helpers ────────────────────────────────────────────────────


class TestExtractArtifactsFromState:
    def test_returns_empty_for_no_artifacts(self) -> None:
        assert _extract_artifacts_from_state({}) == []

    def test_preserves_existing_ids(self) -> None:
        state = {"artifacts": [{"artifact_id": "custom-1", "title": "T"}]}
        result = _extract_artifacts_from_state(state)
        assert result[0]["artifact_id"] == "custom-1"
        assert result[0]["id"] == "custom-1"

    def test_generates_ids_when_missing(self) -> None:
        state = {"artifacts": [{"title": "A"}, {"title": "B"}]}
        result = _extract_artifacts_from_state(state)
        assert result[0]["artifact_id"] == "artifact-0"
        assert result[1]["artifact_id"] == "artifact-1"
        assert result[0]["id"] == "artifact-0"


class TestRedactTeacherOnly:
    def test_removes_teacher_only_sections(self) -> None:
        artifact = {
            "sections": [
                {"heading": "Q1", "content": "..."},
                {"heading": "Answers", "content": "...", "teacher_only": True},
            ]
        }
        result = _redact_teacher_only(artifact)
        assert len(result["sections"]) == 1
        assert result["sections"][0]["heading"] == "Q1"

    def test_keeps_all_when_no_teacher_only(self) -> None:
        artifact = {
            "sections": [
                {"heading": "Intro", "content": "..."},
                {"heading": "Body", "content": "..."},
            ]
        }
        result = _redact_teacher_only(artifact)
        assert len(result["sections"]) == 2

    def test_does_not_mutate_original(self) -> None:
        original_sections = [
            {"heading": "Q1", "content": "..."},
            {"heading": "Answers", "content": "...", "teacher_only": True},
        ]
        artifact = {"sections": original_sections}
        _redact_teacher_only(artifact)
        assert len(original_sections) == 2  # original unchanged


# ── Ownership guard ─────────────────────────────────────────────────────────


def _make_teacher2() -> User:
    return User(user_id="t-002", username="teacher2", role=Role.TEACHER)


def _make_admin_user() -> User:
    return User(user_id="admin-001", username="admin1", role=Role.ADMIN)


def _make_app_with_user(user: User) -> TestClient:
    from services.gateway.auth.dependencies import require_teacher

    app = FastAPI()
    app.include_router(router, prefix="/run")
    register_exception_handlers(app)
    app.state.runs = {}
    app.dependency_overrides[require_teacher] = lambda: user
    return TestClient(app)


def _seed_run_for_user(
    client: TestClient,
    run_id: str,
    artifacts: list[dict[str, Any]],
    teacher_id: str,
) -> None:
    app: FastAPI = client.app  # type: ignore[assignment]
    app.state.runs[run_id] = {
        "run_id": run_id,
        "status": "completed",
        "state": {"artifacts": artifacts, "current_step": 13},
        "teacher_id": teacher_id,
        "created_at": "2026-01-01T00:00:00",
    }


class TestOwnershipGuard:
    def test_list_artifacts_denied_for_other_teacher(self) -> None:
        teacher1_client = _make_app_with_auth()
        _seed_run_for_user(teacher1_client, "run-own", [SAMPLE_ARTIFACT], "t-001")

        teacher2_client = _make_app_with_user(_make_teacher2())
        teacher2_client.app.state.runs = teacher1_client.app.state.runs

        response = teacher2_client.get("/run/run-own/artifacts")
        assert response.status_code == 403
        assert response.json()["error_code"] == "AUTHORIZATION_ERROR"

    def test_get_artifact_denied_for_other_teacher(self) -> None:
        teacher1_client = _make_app_with_auth()
        _seed_run_for_user(teacher1_client, "run-own2", [SAMPLE_ARTIFACT], "t-001")

        teacher2_client = _make_app_with_user(_make_teacher2())
        teacher2_client.app.state.runs = teacher1_client.app.state.runs

        response = teacher2_client.get("/run/run-own2/artifacts/artifact-0")
        assert response.status_code == 403

    def test_list_artifacts_allowed_for_admin(self) -> None:
        teacher1_client = _make_app_with_auth()
        _seed_run_for_user(teacher1_client, "run-admin", [SAMPLE_ARTIFACT], "t-001")

        admin_client = _make_app_with_user(_make_admin_user())
        admin_client.app.state.runs = teacher1_client.app.state.runs

        response = admin_client.get("/run/run-admin/artifacts")
        assert response.status_code == 200
        assert len(response.json()) == 1

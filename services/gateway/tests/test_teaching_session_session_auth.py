from __future__ import annotations

from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.jwt_handler import create_access_token
from services.gateway.auth.models import Role, User
from services.gateway.teaching_session.models import RetentionTier, TeachingSession
from services.gateway.teaching_session.session_auth import require_controller, require_session_role
from services.gateway.teaching_session.tokens import (
    SessionRole,
    SessionTokenPayload,
    mint_session_token,
)

OWNER = User(user_id="teacher-1", username="teacher-1", role=Role.TEACHER)
JWT_SECRET = "test-secret-minimum-32-characters"


def _session() -> TeachingSession:
    return TeachingSession(
        session_id="session-1",
        teacher_id="teacher-1",
        deck_id="deck-1",
        snapshot_id="snap-1",
        retention_tier=RetentionTier.AGGREGATE,
        room_code="123456",
    )


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/controller-only")
    async def controller_only(
        claims: Annotated[SessionTokenPayload, Depends(require_controller)],
    ) -> dict[str, str]:
        return {"role": claims.role}

    @app.get("/student-or-observer")
    async def student_or_observer(
        claims: Annotated[
            SessionTokenPayload,
            Depends(require_session_role(SessionRole.STUDENT, SessionRole.OBSERVER)),
        ],
    ) -> dict[str, str]:
        return {"role": claims.role}

    @app.get("/teacher-only")
    async def teacher_only(user: Annotated[User, Depends(require_teacher)]) -> dict[str, str]:
        return {"user_id": user.user_id}

    return app


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestControllerOnlyRoute:
    """base AC5: student/display/observer tokens cannot reach controller actions."""

    def test_missing_token_is_401(self) -> None:
        response = TestClient(_app()).get("/controller-only")
        assert response.status_code == 401

    @pytest.mark.parametrize(
        "role", [SessionRole.STUDENT, SessionRole.DISPLAY, SessionRole.OBSERVER],
    )
    def test_non_controller_token_is_403(
        self, monkeypatch: pytest.MonkeyPatch, role: SessionRole,
    ) -> None:
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        minted_by = None if role == SessionRole.STUDENT else OWNER
        token = mint_session_token(_session(), role=role, minted_by=minted_by)

        response = TestClient(_app()).get("/controller-only", headers=_bearer(token))

        assert response.status_code == 403

    def test_controller_token_is_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        token = mint_session_token(_session(), role=SessionRole.CONTROLLER, minted_by=OWNER)

        response = TestClient(_app()).get("/controller-only", headers=_bearer(token))

        assert response.status_code == 200
        assert response.json()["role"] == "controller"

    def test_account_jwt_cannot_reach_session_role_route(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A teacher's own account token is not a session role token."""
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        account_token = create_access_token(OWNER).access_token

        response = TestClient(_app()).get("/controller-only", headers=_bearer(account_token))

        assert response.status_code == 401


class TestSessionTokenCannotReachTeacherOnlyRoute:
    """base AC5: student/display/observer tokens cannot reach teacher-only routes."""

    @pytest.mark.parametrize(
        "role", [SessionRole.STUDENT, SessionRole.DISPLAY, SessionRole.OBSERVER],
    )
    def test_rejected_by_require_teacher(
        self, monkeypatch: pytest.MonkeyPatch, role: SessionRole,
    ) -> None:
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        minted_by = None if role == SessionRole.STUDENT else OWNER
        session_token = mint_session_token(_session(), role=role, minted_by=minted_by)

        response = TestClient(_app()).get("/teacher-only", headers=_bearer(session_token))

        assert response.status_code == 401


class TestParticipantRoute:
    def test_student_can_reach_a_participant_route(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        token = mint_session_token(_session(), role=SessionRole.STUDENT)

        response = TestClient(_app()).get("/student-or-observer", headers=_bearer(token))

        assert response.status_code == 200

    def test_controller_cannot_reach_participant_only_route(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        token = mint_session_token(_session(), role=SessionRole.CONTROLLER, minted_by=OWNER)

        response = TestClient(_app()).get("/student-or-observer", headers=_bearer(token))

        assert response.status_code == 403

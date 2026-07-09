from __future__ import annotations

import time

import pytest

from services.gateway.auth.jwt_handler import create_access_token, verify_token
from services.gateway.auth.models import Role, User
from services.gateway.exceptions import AuthorizationError
from services.gateway.teaching_session.models import RetentionTier, TeachingSession
from services.gateway.teaching_session.tokens import (
    PARTICIPANT_ROLES,
    TEACHER_MINTED_ROLES,
    IdentityMode,
    SessionRole,
    mint_session_token,
    verify_session_token,
)

OWNER = User(user_id="teacher-1", username="teacher-1", role=Role.TEACHER)
OTHER_TEACHER = User(user_id="teacher-2", username="teacher-2", role=Role.TEACHER)

JWT_SECRET = "test-secret-minimum-32-characters"


def _session(**overrides: object) -> TeachingSession:
    defaults: dict[str, object] = {
        "session_id": "session-1",
        "teacher_id": "teacher-1",
        "deck_id": "deck-1",
        "snapshot_id": "snap-1",
        "retention_tier": RetentionTier.AGGREGATE,
        "room_code": "123456",
    }
    defaults.update(overrides)
    return TeachingSession(**defaults)


class TestRoleModel:
    """Amendment #1: STUDENT is a session-scoped claim, never a `users.role` value."""

    def test_student_role_exists_but_is_not_a_users_role(self) -> None:
        assert SessionRole.STUDENT == "student"
        assert "STUDENT" not in Role.__members__

    def test_teacher_minted_roles_are_everything_but_student(self) -> None:
        expected = {SessionRole.CONTROLLER, SessionRole.DISPLAY, SessionRole.OBSERVER}
        assert SessionRole.STUDENT not in TEACHER_MINTED_ROLES
        assert expected == TEACHER_MINTED_ROLES

    def test_participant_roles_exclude_controller(self) -> None:
        expected = {SessionRole.STUDENT, SessionRole.DISPLAY, SessionRole.OBSERVER}
        assert SessionRole.CONTROLLER not in PARTICIPANT_ROLES
        assert expected == PARTICIPANT_ROLES


class TestMintSessionTokenOwnership:
    """base AC3: teacher ownership/auth is required to mint controller tokens."""

    def test_controller_requires_a_minting_teacher(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        with pytest.raises(AuthorizationError):
            mint_session_token(_session(), role=SessionRole.CONTROLLER, minted_by=None)

    def test_controller_rejects_a_non_owning_teacher(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        with pytest.raises(AuthorizationError):
            mint_session_token(_session(), role=SessionRole.CONTROLLER, minted_by=OTHER_TEACHER)

    def test_controller_accepted_for_owning_teacher(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        token = mint_session_token(_session(), role=SessionRole.CONTROLLER, minted_by=OWNER)
        assert verify_session_token(token).role == SessionRole.CONTROLLER

    @pytest.mark.parametrize("role", [SessionRole.DISPLAY, SessionRole.OBSERVER])
    def test_display_and_observer_also_require_owning_teacher(
        self, monkeypatch: pytest.MonkeyPatch, role: SessionRole,
    ) -> None:
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        with pytest.raises(AuthorizationError):
            mint_session_token(_session(), role=role, minted_by=None)
        with pytest.raises(AuthorizationError):
            mint_session_token(_session(), role=role, minted_by=OTHER_TEACHER)
        token = mint_session_token(_session(), role=role, minted_by=OWNER)
        assert verify_session_token(token).role == role

    def test_student_token_needs_no_teacher(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        token = mint_session_token(_session(), role=SessionRole.STUDENT)
        claims = verify_session_token(token)
        assert claims.role == SessionRole.STUDENT
        assert claims.identity_mode == IdentityMode.ANONYMOUS


class TestTokenScoping:
    """base AC4: role tokens are scoped to session, role, expiry, and policy."""

    def test_scoped_to_session_role_expiry_and_policy(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        session = _session(retention_tier=RetentionTier.PSEUDONYMOUS, class_id="class-5a")
        before = int(time.time())

        token = mint_session_token(session, role=SessionRole.STUDENT, ttl_seconds=60)
        claims = verify_session_token(token)

        assert claims.session_id == session.session_id
        assert claims.room_code == session.room_code
        assert claims.role == SessionRole.STUDENT
        assert claims.retention_tier == RetentionTier.PSEUDONYMOUS
        assert before <= claims.iat <= claims.exp
        assert claims.exp - claims.iat == 60

    def test_expired_token_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        token = mint_session_token(_session(), role=SessionRole.STUDENT, ttl_seconds=-10)
        with pytest.raises(ValueError, match="expired"):
            verify_session_token(token)

    def test_default_ttl_is_far_shorter_than_the_account_token_default(self) -> None:
        from services.gateway.teaching_session.tokens import DEFAULT_SESSION_TOKEN_TTL_SECONDS

        assert DEFAULT_SESSION_TOKEN_TTL_SECONDS < 24 * 3600


class TestCrossTokenTypeRejection:
    """A session token must never satisfy account auth, and vice versa."""

    def test_account_token_is_not_a_valid_session_token(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        account_token = create_access_token(OWNER).access_token
        with pytest.raises(ValueError):
            verify_session_token(account_token)

    def test_session_token_is_not_a_valid_account_token(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        session_token = mint_session_token(_session(), role=SessionRole.STUDENT)
        with pytest.raises(ValueError):
            verify_token(session_token)

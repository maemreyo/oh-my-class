"""Scoped, short-lived TeachingSession role tokens (TSP-02, ADR-046).

Mints/verifies JWTs for session roles (controller/display/student/observer)
via the *same signing path* as `services.gateway.auth.jwt_handler` (same
secret/algorithm/`jwt.encode`/`jwt.decode` helpers) -- but a completely
separate payload shape and role enum. `SessionRole` is never
`services.gateway.auth.models.Role` (the persisted `users.role` column):
`STUDENT` in particular must never become a `Role` member or a `users` row --
there is no persistent identity to revoke or leak (amendment #1). Only
`CONTROLLER`/`DISPLAY`/`OBSERVER` require an owning teacher to mint; `STUDENT`
tokens come exclusively from the anonymous/pseudonymous/roster join flow in
`teaching_session.join`. Co-teacher is deliberately not a role here yet (the
parent issue defers it).
"""

from __future__ import annotations

import time
from enum import StrEnum
from typing import TYPE_CHECKING

import jwt
from pydantic import BaseModel, ValidationError

from services.gateway.auth.jwt_handler import get_jwt_algorithm, get_jwt_secret
from services.gateway.auth.models import TEACHER_ROLES
from services.gateway.exceptions import AuthorizationError
from services.gateway.teaching_session.models import (
    RetentionTier,  # noqa: TC001  pydantic runtime need
)

if TYPE_CHECKING:
    from services.gateway.auth.models import User
    from services.gateway.teaching_session.models import TeachingSession

# Session tokens are deliberately far shorter-lived than the 24h default
# account JWT (`services.gateway.auth.config.JWTConfig.expiry_hours`) -- a
# forgotten/leaked student join link should go stale fast (amendment #1).
DEFAULT_SESSION_TOKEN_TTL_SECONDS = 4 * 3600


class SessionRole(StrEnum):
    """A TeachingSession-scoped JWT claim -- never a `users.role` value."""

    CONTROLLER = "controller"
    DISPLAY = "display"
    STUDENT = "student"
    OBSERVER = "observer"


# Every role except STUDENT is a teacher-side surface: minting requires the
# session's own teacher (ownership-checked in `mint_session_token`). STUDENT
# is the only role reachable through the unauthenticated, rate-limited join
# flow -- gating DISPLAY/OBSERVER the same way CONTROLLER is gated closes an
# otherwise-open "mint yourself an observer token" hole.
TEACHER_MINTED_ROLES: frozenset[SessionRole] = frozenset(SessionRole) - {SessionRole.STUDENT}

# Roles with no access to teacher-only surfaces (exports, answer keys,
# controller actions, retention settings) -- everything except CONTROLLER.
PARTICIPANT_ROLES: frozenset[SessionRole] = frozenset(SessionRole) - {SessionRole.CONTROLLER}


class IdentityMode(StrEnum):
    """How a participant identified at join (base AC7) -- labels evidence/
    analytics without storing more PII than the retention tier allows."""

    ANONYMOUS = "anonymous"
    PSEUDONYMOUS = "pseudonymous"
    ROSTER = "roster"


class SessionTokenPayload(BaseModel):
    """Decoded session-role token claims: scoped to session, role, expiry, and policy."""

    session_id: str
    room_code: str
    role: SessionRole
    exp: int  # unix timestamp
    iat: int  # issued at
    retention_tier: RetentionTier | None = None
    identity_mode: IdentityMode = IdentityMode.ANONYMOUS
    alias: str | None = None
    roster_student_id: str | None = None


def mint_session_token(
    session: TeachingSession,
    *,
    role: SessionRole,
    identity_mode: IdentityMode = IdentityMode.ANONYMOUS,
    alias: str | None = None,
    roster_student_id: str | None = None,
    ttl_seconds: int = DEFAULT_SESSION_TOKEN_TTL_SECONDS,
    minted_by: User | None = None,
) -> str:
    """Mint a session-role JWT scoped to `{session_id, role, expiry, policy}`.

    Raises:
        AuthorizationError: `role` is teacher-minted (`TEACHER_MINTED_ROLES`)
            and `minted_by` is missing, not a teacher, or not this session's
            own teacher (base AC3).
    """
    if role in TEACHER_MINTED_ROLES:
        _require_owning_teacher(session, minted_by)

    now = int(time.time())
    payload = SessionTokenPayload(
        session_id=session.session_id,
        room_code=session.room_code or "",
        role=role,
        exp=now + ttl_seconds,
        iat=now,
        retention_tier=session.retention_tier,
        identity_mode=identity_mode,
        alias=alias,
        roster_student_id=roster_student_id,
    )
    return jwt.encode(
        payload.model_dump(mode="json"), get_jwt_secret(), algorithm=get_jwt_algorithm(),
    )


def verify_session_token(token: str) -> SessionTokenPayload:
    """Verify and decode a session-role token. Raises `ValueError` on invalid/expired.

    An account JWT (`services.gateway.auth.jwt_handler.create_access_token`)
    always fails here too -- it carries no `session_id`/`room_code` claims,
    so `SessionTokenPayload` validation rejects it even though it shares a
    signing secret.
    """
    try:
        decoded = jwt.decode(token, get_jwt_secret(), algorithms=[get_jwt_algorithm()])
        return SessionTokenPayload(**decoded)
    except jwt.ExpiredSignatureError:
        raise ValueError("Session token has expired") from None
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid session token: {e}") from e
    except ValidationError as e:
        raise ValueError(f"Invalid session token claims: {e}") from e


def _require_owning_teacher(session: TeachingSession, minted_by: User | None) -> None:
    if minted_by is None or minted_by.role not in TEACHER_ROLES:
        raise AuthorizationError(message="Teacher auth is required to mint this session role token")
    if minted_by.user_id != session.teacher_id:
        raise AuthorizationError(message="Only the session's own teacher can mint this role token")

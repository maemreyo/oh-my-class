"""Anonymous-first join: room codes, join-rate-limiting, role-token issuance
(TSP-02 base ACs 1/6 + amendment #2/#3).

Join affordance is QR-code-primary -- `room_code_join_payload()` is the
opaque string a frontend QR library encodes into an image the teacher
projects (no QR-rendering library exists in this stack yet; rendering the
actual QR image is a frontend concern, not this backend slice's -- see
`.claude` ponytail rung 4/5). The 6-digit numeric `room_code` itself is the
camera-less fallback a student can type by hand.

Rate limiting mirrors `services.gateway.routers.webhooks`'s sliding-window
shape (`WebhookProcessingState` + `_allow_request`): a dict of recent
timestamps per key, trimmed to a trailing window, capped at a count -- just
keyed by `(client_ip, room_code)` instead of a single `source` string, since
amendment #3 rate-limits both dimensions together.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import select

from services.gateway.teaching_session.models import (
    ClassRosterEntry,
    SessionStatus,
    TeachingSession,
)
from services.gateway.teaching_session.tokens import IdentityMode, SessionRole, mint_session_token

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession

# Only a session that hasn't ended yet is joinable -- once ended/archived/
# expired, its room code is dead even if a stale QR/link is still floating
# around a classroom (amendment #3: "room code validity bounded to the
# session's lifetime").
JOINABLE_STATUSES: frozenset[SessionStatus] = frozenset({
    SessionStatus.SCHEDULED, SessionStatus.LIVE,
})


class JoinRateLimitConfig(BaseSettings):
    """Env prefix: TEACHING_SESSION_JOIN_. Mirrors `webhooks/config.py`'s shape."""

    model_config = SettingsConfigDict(
        env_prefix="TEACHING_SESSION_JOIN_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    rate_limit_count: int = 10
    rate_limit_window_seconds: int = 60


def join_rate_limit_config() -> JoinRateLimitConfig:
    # ponytail: uncached, same reasoning as auth/config.py's jwt_config().
    return JoinRateLimitConfig()


def generate_room_code() -> str:
    """A 6-digit numeric room code -- the camera-less join fallback."""
    return f"{secrets.randbelow(1_000_000):06d}"


def room_code_join_payload(session: TeachingSession) -> str:
    """Opaque payload a frontend QR library encodes into the projected QR code."""
    return f"omc-join:{session.session_id}:{session.room_code}"


def is_room_code_valid(session: TeachingSession) -> bool:
    """Room code validity is bounded to the session's lifetime (amendment #3)."""
    return session.room_code is not None and session.status in JOINABLE_STATUSES


async def find_joinable_session_by_room_code(
    db: AsyncSession, room_code: str,
) -> TeachingSession | None:
    """Look up a session by room code, scoped to currently-joinable sessions only."""
    result = await db.execute(
        select(TeachingSession).where(
            TeachingSession.room_code == room_code,
            TeachingSession.status.in_(JOINABLE_STATUSES),
        ),
    )
    return result.scalar_one_or_none()


@dataclass(slots=True)
class JoinRateLimitState:
    """In-memory sliding-window state, one instance per gateway process.

    Mirrors `services.gateway.routers.webhooks.WebhookProcessingState`.
    """

    request_times: dict[tuple[str, str], list[datetime]] = field(default_factory=dict)


def allow_join_attempt(
    state: JoinRateLimitState,
    *,
    client_ip: str,
    room_code: str,
    now: datetime,
    limit: int | None = None,
    window_seconds: int | None = None,
) -> bool:
    """Sliding-window rate limit on join attempts, keyed by IP + room code.

    Same algorithm as `webhooks.py::_allow_request`: count recent hits in a
    trailing window, evict stale ones, deny once at capacity.
    """
    config = join_rate_limit_config()
    if window_seconds is None:
        window_seconds = config.rate_limit_window_seconds
    window = timedelta(seconds=window_seconds)
    cap = limit if limit is not None else config.rate_limit_count
    key = (client_ip, room_code)
    recent = [seen_at for seen_at in state.request_times.get(key, []) if now - seen_at <= window]
    if len(recent) >= cap:
        state.request_times[key] = recent
        return False
    recent.append(now)
    state.request_times[key] = recent
    return True


@dataclass(frozen=True, slots=True)
class JoinAccepted:
    token: str
    role: SessionRole
    identity_mode: IdentityMode


@dataclass(frozen=True, slots=True)
class JoinRejected:
    reason: str
    # "rate_limited" | "invalid_room_code" | "session_not_joinable" | "roster_entry_not_in_class"


type JoinResult = JoinAccepted | JoinRejected


def join_session(
    session: TeachingSession | None,
    *,
    client_ip: str,
    room_code: str,
    now: datetime,
    rate_limit_state: JoinRateLimitState,
    alias: str | None = None,
    roster_entry: ClassRosterEntry | None = None,
) -> JoinResult:
    """Anonymous/pseudonymous/authenticated-roster join (base AC1), minting `STUDENT`.

    No email is ever required or accepted (base AC6 -- there is no email
    parameter at all). `alias` is free-text pseudonymous labeling.
    `roster_entry` is what makes the roster mode *authenticated* rather than
    another flavor of free text (base AC1): it must be a `ClassRosterEntry`
    the caller already looked up via `teaching_session.roster.get_roster_entry`
    (scoped to `class_id`) -- a raw client-supplied name/ID string is never
    accepted directly. Neither mode persists anything new here -- no `users`
    row, no join-event record (that is a future TSP-03 event-log concern) --
    the only output is a short-lived `STUDENT` token.
    """
    if not allow_join_attempt(rate_limit_state, client_ip=client_ip, room_code=room_code, now=now):
        return JoinRejected(reason="rate_limited")
    if session is None or session.room_code != room_code:
        return JoinRejected(reason="invalid_room_code")
    if not is_room_code_valid(session):
        return JoinRejected(reason="session_not_joinable")
    if roster_entry is not None and roster_entry.class_id != session.class_id:
        return JoinRejected(reason="roster_entry_not_in_class")

    if roster_entry is not None:
        identity_mode = IdentityMode.ROSTER
        alias = roster_entry.name
        roster_student_id = roster_entry.student_id or roster_entry.roster_entry_id
    elif alias:
        identity_mode = IdentityMode.PSEUDONYMOUS
        roster_student_id = None
    else:
        identity_mode = IdentityMode.ANONYMOUS
        roster_student_id = None

    token = mint_session_token(
        session,
        role=SessionRole.STUDENT,
        identity_mode=identity_mode,
        alias=alias,
        roster_student_id=roster_student_id,
    )
    return JoinAccepted(token=token, role=SessionRole.STUDENT, identity_mode=identity_mode)

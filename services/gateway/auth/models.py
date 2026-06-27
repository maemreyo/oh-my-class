"""Auth models for JWT-based authentication."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Role(StrEnum):
    """User roles for authorization.

    ``ADMIN`` is kept for backward-compatible tokens issued before
    school/system admin roles were introduced.
    """

    TEACHER = "teacher"
    ADMIN = "admin"  # legacy — kept for old tokens
    SCHOOL_ADMIN = "school_admin"
    SYSTEM_ADMIN = "system_admin"


# ── Helpers for role-based access checks ──────────────────────────────

TEACHER_ROLES: frozenset[Role] = frozenset({
    Role.TEACHER,
    Role.ADMIN,       # legacy backward compat
    Role.SCHOOL_ADMIN,
    Role.SYSTEM_ADMIN,
})

ADMIN_ROLES: frozenset[Role] = frozenset({
    Role.ADMIN,       # legacy backward compat
    Role.SYSTEM_ADMIN,
})


class User(BaseModel):
    """Authenticated user."""

    user_id: str
    username: str
    role: Role
    email: str | None = None
    organization_id: str | None = None
    class_id: str | None = None


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Seconds until expiry")


class TokenPayload(BaseModel):
    """JWT token payload (decoded).

    ``organization_id`` and ``class_id`` are optional for backward
    compatibility with tokens issued before Pipeline V2 tenant auth.
    """

    sub: str  # user_id
    role: Role
    exp: int  # unix timestamp
    iat: int  # issued at
    organization_id: str | None = None
    class_id: str | None = None


class LoginRequest(BaseModel):
    """Login request body."""

    username: str
    password: str


class WebhookSecret(BaseModel):
    """Webhook signature verification config."""

    telegram_secret: str | None = None
    zalo_secret: str | None = None

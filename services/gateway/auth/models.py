"""Auth models for JWT-based authentication."""

from enum import StrEnum

from pydantic import BaseModel, Field


class Role(StrEnum):
    TEACHER = "teacher"
    ADMIN = "admin"


class User(BaseModel):
    """Authenticated user."""
    user_id: str
    username: str
    role: Role
    email: str | None = None


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Seconds until expiry")


class TokenPayload(BaseModel):
    """JWT token payload (decoded)."""
    sub: str  # user_id
    role: Role
    exp: int  # unix timestamp
    iat: int  # issued at


class LoginRequest(BaseModel):
    """Login request body."""
    username: str
    password: str


class WebhookSecret(BaseModel):
    """Webhook signature verification config."""
    telegram_secret: str | None = None
    zalo_secret: str | None = None

"""Auth-related Pydantic models shared between gateway and web app."""

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

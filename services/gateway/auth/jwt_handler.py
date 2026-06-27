"""JWT token creation and verification."""

import os
import time

import jwt

from .models import Token, TokenPayload, User


def get_jwt_secret() -> str:
    """Get JWT secret from environment."""
    secret = os.environ.get("JWT_SECRET", "")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET environment variable is required. "
            "Generate one with: openssl rand -base64 32"
        )
    return secret


def get_jwt_algorithm() -> str:
    return os.environ.get("JWT_ALGORITHM", "HS256")


def get_jwt_expiry_hours() -> int:
    return int(os.environ.get("JWT_EXPIRY_HOURS", "24"))


def create_access_token(user: User) -> Token:
    """Create a JWT access token for a user."""
    secret = get_jwt_secret()
    algorithm = get_jwt_algorithm()
    expiry_hours = get_jwt_expiry_hours()

    now = int(time.time())
    expires_at = now + (expiry_hours * 3600)

    payload = TokenPayload(
        sub=user.user_id,
        role=user.role,
        exp=expires_at,
        iat=now,
        organization_id=user.organization_id,
        class_id=user.class_id,
    )

    token = jwt.encode(payload.model_dump(), secret, algorithm=algorithm)

    return Token(
        access_token=token,
        token_type="bearer",
        expires_in=expiry_hours * 3600,
    )


def verify_token(token: str) -> TokenPayload:
    """Verify and decode a JWT token. Raises on invalid/expired."""
    secret = get_jwt_secret()
    algorithm = get_jwt_algorithm()

    try:
        decoded = jwt.decode(token, secret, algorithms=[algorithm])
        return TokenPayload(**decoded)
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired") from None
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}") from e


def user_from_payload(payload: TokenPayload) -> User:
    """Convert token payload to User object."""
    return User(
        user_id=payload.sub,
        username=payload.sub,  # In real app, look up from DB
        role=payload.role,
        organization_id=payload.organization_id,
        class_id=payload.class_id,
    )

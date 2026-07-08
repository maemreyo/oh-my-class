"""Auth configuration — pydantic-settings, not bare os.environ (LGH-06).

Bare os.environ.get() only sees .env's contents if something else already
loaded it into the process environment. A subprocess or bare script gets
neither and silently sees defaults instead of failing loudly.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class JWTConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="JWT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    secret: str = ""
    algorithm: str = "HS256"
    expiry_hours: int = 24


def jwt_config() -> JWTConfig:
    # ponytail: uncached — reads env fresh every call, matching the pre-migration
    # os.environ.get() behavior exactly (JWT ops aren't a hot enough path to need
    # caching, and caching would break monkeypatch.setenv-based test isolation).
    return JWTConfig()

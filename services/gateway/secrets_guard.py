"""Production startup guard for deployment secrets."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

PRODUCTION_ENVIRONMENTS = frozenset({"production", "prod"})


@dataclass(frozen=True, slots=True)
class SecretRule:
    name: str
    defaults: frozenset[str]


SECRET_RULES: tuple[SecretRule, ...] = (
    SecretRule("POSTGRES_PASSWORD", frozenset({"omc_dev", "changeme-in-production"})),
    SecretRule("REDIS_AUTH", frozenset({"omc_redis_secret"})),
    SecretRule("LANGFUSE_ENCRYPTION_KEY", frozenset({"0" * 64, "00000000000000000000000000000000"})),
    SecretRule("LANGFUSE_NEXTAUTH_SECRET", frozenset({"changeme", "nextauth_secret"})),
    SecretRule("CLICKHOUSE_PASSWORD", frozenset({"clickhouse", "omc_clickhouse"})),
    SecretRule("MINIO_ROOT_PASSWORD", frozenset({"minioadmin", "omc_minio_secret"})),
)


class ProductionSecretsError(RuntimeError):
    def __init__(self, offenders: tuple[str, ...]) -> None:
        joined = ", ".join(offenders)
        super().__init__(f"Production startup refused: insecure secret values for {joined}")
        self.offenders = offenders


def validate_production_secrets(environ: Mapping[str, str] | None = None) -> None:
    values = environ or os.environ
    environment = values.get("ENV", values.get("OMC_ENVIRONMENT", "development")).lower()
    if environment not in PRODUCTION_ENVIRONMENTS:
        return
    offenders = tuple(rule.name for rule in SECRET_RULES if _is_insecure_secret(values.get(rule.name, ""), rule))
    if offenders:
        raise ProductionSecretsError(offenders)


def _is_insecure_secret(value: str, rule: SecretRule) -> bool:
    stripped = value.strip()
    if not stripped:
        return True
    if stripped in rule.defaults:
        return True
    return set(stripped) == {"0"}

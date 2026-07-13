"""Tenant and privacy contracts for Content Factory V2.

The contract is intentionally small enough to cross package boundaries.  It
contains no gateway or persistence imports, so agents, quality gates, workers,
and storage adapters can all require the same scope object instead of passing
bare organization/teacher strings independently.
"""

from __future__ import annotations

import hashlib
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ResourceScope = Literal["system", "organization", "teacher", "class", "run"]
PrincipalRole = Literal["teacher", "reviewer", "school_admin", "system_admin", "worker"]

_SENSITIVE_KEYS = frozenset({
    "answer",
    "answers",
    "content",
    "excerpt",
    "prompt",
    "raw_request",
    "response",
    "student_evidence",
    "student_response",
    "teacher_notes",
})


class TenantAccessDeniedError(PermissionError):
    def __init__(self, organization_id: str, resource_organization_id: str) -> None:
        self.organization_id = organization_id
        self.resource_organization_id = resource_organization_id
        super().__init__(
            f"tenant {organization_id!r} cannot access resource owned by "
            f"{resource_organization_id!r}",
        )


class TenantContext(BaseModel):
    """Mandatory authority carried across every content boundary."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    organization_id: str = Field(min_length=1, max_length=80)
    principal_id: str = Field(min_length=1, max_length=80)
    principal_role: PrincipalRole
    teacher_id: str | None = Field(default=None, max_length=80)
    class_id: str | None = Field(default=None, max_length=80)

    def require_organization(self, resource_organization_id: str) -> None:
        if self.organization_id != resource_organization_id:
            raise TenantAccessDeniedError(self.organization_id, resource_organization_id)

    def storage_key(self, resource_kind: str, *parts: str) -> str:
        """Build a tenant-scoped, traversal-safe cache/object/storage key."""
        safe_parts = [_safe_key_part(value) for value in parts]
        return "/".join(("organizations", _safe_key_part(self.organization_id), resource_kind, *safe_parts))

    @property
    def audit_fingerprint(self) -> str:
        digest = hashlib.sha256(
            f"{self.organization_id}|{self.principal_id}|{self.principal_role}".encode(),
        ).hexdigest()
        return digest[:20]


def personal_tenant_context(
    *,
    teacher_id: str,
    principal_id: str | None = None,
    principal_role: PrincipalRole = "teacher",
) -> TenantContext:
    """Backward-compatible personal tenant for installations without schools.

    This is an explicit tenant, not an unscoped fallback: every personal
    teacher receives a stable organization namespace of ``teacher:<id>``.
    """
    return TenantContext(
        organization_id=f"teacher:{teacher_id}",
        principal_id=principal_id or teacher_id,
        principal_role=principal_role,
        teacher_id=teacher_id,
    )


def privacy_safe_metadata(value: Any) -> Any:
    """Return telemetry metadata with raw content and PII-bearing fields removed.

    IDs, counts, status flags, hashes, versions, and classifications are kept.
    Raw prompts, excerpts, answers, student evidence, and generated content are
    replaced by a deterministic descriptor so operations remain debuggable
    without retaining the content itself.
    """
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for raw_key, nested in value.items():
            key = str(raw_key)
            if key.casefold() in _SENSITIVE_KEYS:
                redacted[key] = _redaction_descriptor(nested)
            else:
                redacted[key] = privacy_safe_metadata(nested)
        return redacted
    if isinstance(value, list):
        return [privacy_safe_metadata(item) for item in value]
    if isinstance(value, tuple):
        return tuple(privacy_safe_metadata(item) for item in value)
    return value


def _redaction_descriptor(value: Any) -> dict[str, Any]:
    serialized = repr(value).encode("utf-8", errors="replace")
    return {
        "redacted": True,
        "sha256": hashlib.sha256(serialized).hexdigest(),
        "size_bytes": len(serialized),
    }


def _safe_key_part(value: str) -> str:
    stripped = value.strip()
    if not stripped or stripped in {".", ".."} or "/" in stripped or "\\" in stripped:
        raise ValueError(f"unsafe tenant storage key part: {value!r}")
    return stripped

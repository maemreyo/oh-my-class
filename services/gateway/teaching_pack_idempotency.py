from __future__ import annotations

from hashlib import sha256
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.gateway.teaching_pack_types import RunId, TeacherId


def scoped_create_idempotency_key(teacher_id: TeacherId, idempotency_key: str) -> str:
    return _scoped_idempotency_key("create", teacher_id, idempotency_key)


def scoped_resume_idempotency_key(
    run_id: RunId,
    teacher_id: TeacherId,
    idempotency_key: str,
) -> str:
    return _scoped_idempotency_key("resume", teacher_id, f"{run_id}:{idempotency_key}")


def _scoped_idempotency_key(namespace: str, teacher_id: TeacherId, value: str) -> str:
    digest = sha256(f"{namespace}:{teacher_id}:{value}".encode()).hexdigest()
    return f"idem:{namespace}:{digest}"

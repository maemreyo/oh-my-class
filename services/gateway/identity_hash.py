"""Identity hashing for privacy-conscious metadata."""

import hashlib


def hash_identity(raw: str, salt: str = "") -> str:
    """Hash an identity string with optional salt.
    
    Returns first 16 chars of SHA-256 hex for compactness.
    """
    return hashlib.sha256(f"{salt}:{raw}".encode()).hexdigest()[:16]


def hash_teacher_id(teacher_id: str) -> str:
    """Hash teacher_id for Langfuse metadata."""
    return hash_identity(teacher_id)


def hash_email(email: str) -> str:
    """Hash email for metadata (never include raw email)."""
    return hash_identity(email)


def hash_class_id(class_id: str) -> str:
    """Hash class_id for metadata."""
    return hash_identity(class_id)


def langfuse_safe_metadata(
    teacher_id: str,
    email: str | None = None,
    class_id: str | None = None,
    org_id: str | None = None,
) -> dict[str, str]:
    """Build metadata dict with hashed identities for Langfuse.
    
    Returns dict with hashed_id, hashed_class, hashed_org keys.
    Never includes raw PII.
    """
    result = {"hashed_id": hash_teacher_id(teacher_id)}
    if email:
        result["hashed_email"] = hash_email(email)
    if class_id:
        result["hashed_class"] = hash_class_id(class_id)
    if org_id:
        result["hashed_org"] = hash_identity(org_id)
    return result
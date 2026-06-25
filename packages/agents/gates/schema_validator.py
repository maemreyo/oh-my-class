"""Layer 1: JSON Schema validation with circuit breaker."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState

REQUIRED_ARTIFACT_KEYS = {"type", "content"}


def step_09_schema_validate(state: OhMyClassState) -> dict[str, Any]:
    """Layer 1: Validate artifacts against required schema.

    Checks each artifact has required keys and non-empty content.
    Writes fail signal on failure, schema_valid=True on success.
    """
    artifacts = state.get("artifacts") or []
    errors = []

    if not artifacts:
        errors.append("No artifacts to validate")

    for i, artifact in enumerate(artifacts):
        missing = REQUIRED_ARTIFACT_KEYS - set(artifact.keys())
        if missing:
            errors.append(f"Artifact[{i}] missing keys: {sorted(missing)}")
        content = artifact.get("content", "")
        if not content or not content.strip():
            errors.append(f"Artifact[{i}] has empty content")

    if errors:
        return {
            "schema_valid": False,
            "fail_layer": "schema",
            "fail_type": "validation",
            "fail_count": state.get("fail_count", 0),
            "fail_context": {"errors": errors},
        }

    return {"schema_valid": True}

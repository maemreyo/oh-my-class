"""Layer 1: JSON Schema validation with circuit breaker.

Validates artifacts against the ArtifactContent contract defined in
common/contracts/artifact.py.  Required keys: artifact_type, title, sections.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState

REQUIRED_ARTIFACT_KEYS = {"artifact_type", "title", "sections"}

_VALID_ARTIFACT_TYPES = frozenset({
    "lesson", "worksheet", "quiz", "drill", "recap", "infographic",
    "answer_key", "roadmap",
})


def _extract_text_content(artifact: dict[str, Any]) -> str:
    """Extract concatenated text from an artifact's sections list."""
    sections = artifact.get("sections") or []
    parts: list[str] = []
    for section in sections:
        text = section.get("content", "")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    return "\n".join(parts)


def _section_has_payload(section: dict[str, Any]) -> bool:
    content = section.get("content", "")
    components = section.get("components")
    return (isinstance(content, str) and bool(content.strip())) or (
        isinstance(components, list) and bool(components)
    )


def step_09_schema_validate(state: OhMyClassState) -> dict[str, Any]:
    """Layer 1: Validate artifacts against ArtifactContent contract.

    Checks each artifact has required keys (artifact_type, title, sections),
    a valid artifact_type, non-empty title, and non-empty sections.
    Writes fail signal on failure, schema_valid=True on success.
    """
    artifacts = state.get("artifacts") or []
    errors: list[str] = []

    if not artifacts:
        errors.append("No artifacts to validate")

    for i, artifact in enumerate(artifacts):
        missing = REQUIRED_ARTIFACT_KEYS - set(artifact.keys())
        if missing:
            errors.append(f"Artifact[{i}] missing keys: {sorted(missing)}")
            continue

        artifact_type = artifact.get("artifact_type", "")
        if artifact_type not in _VALID_ARTIFACT_TYPES:
            errors.append(
                f"Artifact[{i}] invalid artifact_type: {artifact_type!r}"
            )

        title = artifact.get("title", "")
        if not isinstance(title, str) or not title.strip():
            errors.append(f"Artifact[{i}] has empty title")
        elif len(title.strip()) > 200:
            errors.append(f"Artifact[{i}] title exceeds 200 chars")

        sections = artifact.get("sections")
        if not isinstance(sections, list) or len(sections) == 0:
            errors.append(f"Artifact[{i}] has empty or missing sections")
        else:
            for j, section in enumerate(sections):
                if not isinstance(section, dict):
                    errors.append(
                        f"Artifact[{i}].sections[{j}] is not a dict"
                    )
                elif not _section_has_payload(section):
                    errors.append(
                        f"Artifact[{i}].sections[{j}] has empty content and components"
                    )

    if errors:
        return {
            "schema_valid": False,
            "fail_layer": "schema",
            "fail_type": "validation",
            "fail_count": state.get("fail_count", 0),
            "fail_context": {"errors": errors},
        }

    return {"schema_valid": True}

"""Layer 1 — Component minimums hard gate.

Counts typed-dict components in artifact sections and validates that
each artifact type meets its minimum component count.  Flat-text
artifacts (all paragraphs/headings, no real content) are rejected.

No dependencies beyond stdlib and common.contracts.components.registry.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

_SKIP_ARTIFACT_TYPES: Final[frozenset[str]] = frozenset({"answer_key", "roadmap"})

# Structural / text-only component types that do NOT count for lessons
_TEXT_OR_STRUCTURAL: Final[frozenset[str]] = frozenset({
    "heading",
    "paragraph",
    "callout",
    "ordered_list",
    "unordered_list",
})

# Visual / data-display types that count for infographics
_VISUAL_DATA_DISPLAY: Final[frozenset[str]] = frozenset({
    "stat_grid",
    "pattern_grid",
    "trait_grid",
    "taxonomy_grid",
    "concept_map",
    "timeline",
})

# Minimums per artifact type
_MINIMUMS: Final[dict[str, int]] = {
    "lesson": 2,
    "quiz": 8,
    "worksheet": 3,
    "drill": 5,
    "recap": 3,
    "infographic": 1,
}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ComponentGateError(Exception):
    """Raised when component minimums are not met."""

    def __init__(self, artifact_type: str, issues: list[str]) -> None:
        self.artifact_type = artifact_type
        self.issues = issues
        super().__init__(
            f"Component gate failed for {artifact_type!r}: {issues}"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_component(obj: object) -> bool:
    """Return True if *obj* is a dict with a string ``type`` field."""
    return isinstance(obj, Mapping) and isinstance(obj.get("type"), str)


def extract_components(sections: list[object]) -> list[Mapping[str, object]]:
    components: list[Mapping[str, object]] = []
    for section in sections:
        if _is_component(section):
            components.append(section)  # type: ignore[arg-type]
        if not isinstance(section, Mapping):
            continue
        nested = section.get("components")
        if not isinstance(nested, list):
            continue
        components.extend(item for item in nested if _is_component(item))
    return components


def _count_question_components(components: list[Mapping[str, object]]) -> int:
    """Count question components: ``question_card`` + items inside ``question_list``."""
    total = 0
    for comp in components:
        comp_type = str(comp.get("type", ""))
        if comp_type == "question_card":
            total += 1
        elif comp_type == "question_list":
            questions = comp.get("questions", [])
            if isinstance(questions, list):
                total += len(questions)
    return total


def _count_lesson_non_structural(components: list[Mapping[str, object]]) -> int:
    """Count components that are NOT text/structural for lesson artifacts."""
    return sum(
        1
        for c in components
        if str(c.get("type", "")) not in _TEXT_OR_STRUCTURAL
    )


def _count_infographic_visual(components: list[Mapping[str, object]]) -> int:
    """Count visual / data-display components for infographics."""
    return sum(
        1
        for c in components
        if str(c.get("type", "")) in _VISUAL_DATA_DISPLAY
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_component_minimums(artifact: Mapping[str, object]) -> list[str]:
    """Validate that an artifact meets minimum component counts.

    Args:
        artifact: Artifact dict with at least ``artifact_type`` and ``sections``.

    Returns:
        List of issue strings.  Empty list means the artifact passes.
    """
    artifact_type = str(artifact.get("artifact_type", ""))
    sections_raw = artifact.get("sections", [])

    # Always skip answer_key and roadmap
    if artifact_type in _SKIP_ARTIFACT_TYPES:
        return []

    # No known minimum → nothing to check
    if artifact_type not in _MINIMUMS:
        return []

    # Sections must be a list (graceful on malformed data)
    if not isinstance(sections_raw, list):
        return [
            f"{artifact_type}: 'sections' is not a list — cannot count components"
        ]

    components = extract_components(sections_raw)

    if not components:
        return [f"{artifact_type}: no typed components found in sections"]

    minimum = _MINIMUMS[artifact_type]

    if artifact_type == "lesson":
        count = _count_lesson_non_structural(components)
        label = "non-structural components"
    elif artifact_type == "infographic":
        count = _count_infographic_visual(components)
        label = "visual/data-display components"
    else:
        # quiz, worksheet, drill, recap
        count = _count_question_components(components)
        label = "question components"

    if count < minimum:
        return [
            f"{artifact_type}: found {count} {label}, need ≥{minimum}"
        ]
    return []


def assert_component_minimums(artifact: Mapping[str, object]) -> None:
    """Raise ``ComponentGateError`` if the artifact fails component minimums.

    Convenience wrapper around :func:`validate_component_minimums` for use
    in gate nodes that should abort on failure.
    """
    issues = validate_component_minimums(artifact)
    if issues:
        artifact_type = str(artifact.get("artifact_type", ""))
        raise ComponentGateError(artifact_type=artifact_type, issues=issues)

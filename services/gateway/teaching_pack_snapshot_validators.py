"""Validators for answer-key isolation and snapshot version consistency.

INVARIANT-05 enforcer: answer keys must be isolated in teacher_only markers.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from common.contracts.slide_deck import resolve_slide_deck_display_preferences

if TYPE_CHECKING:
    from services.gateway.teaching_pack_snapshot_models import ArtifactSnapshot
    from services.gateway.teaching_pack_snapshot_schemas import ArtifactSnapshotCreate
    from services.gateway.teaching_pack_types import JsonObject


_TEACHER_ONLY_KEYS = frozenset({
    "answer",
    "answer_set",
    "accepted_answers",
    "correct_option_ids",
    "explain",
    "rationale",
    "wrong_reasons",
    "rubric_solution",
})


def teacher_only_value_paths(value: JsonObject) -> list[str]:
    """Return recursive paths that would leak answers from a student projection."""
    return _teacher_only_value_paths(value, "content_json")


def _teacher_only_value_paths(value: object, path: str) -> list[str]:
    if isinstance(value, list):
        return [
            leaked_path
            for index, item in enumerate(value)
            for leaked_path in _teacher_only_value_paths(item, f"{path}[{index}]")
        ]
    if not isinstance(value, dict):
        return []
    paths: list[str] = []
    for key, item in value.items():
        child_path = f"{path}.{key}"
        if key in _TEACHER_ONLY_KEYS:
            paths.append(child_path)
        paths.extend(_teacher_only_value_paths(item, child_path))
    return paths


def _contains_answer_key_patterns(text: str) -> bool:
    """Check if text contains answer-key patterns.

    Matches: "Answer Key", "Answer:", "Correct Answer", "Correct:", "Solution:"
    Case-insensitive.
    """
    pattern = r'(?:Answer\s*(?:Key|:)|Correct\s*(?:Answer|:)|Solution\s*:|Đáp\s*án\s*)'
    return bool(re.search(pattern, text, re.IGNORECASE))


def validate_answer_key_isolation(rendered_html: str) -> list[str]:
    """Validate that answer-key patterns only appear in marked teacher-only sections.

    Returns a list of issues found. Empty list means validation passed.
    INVARIANT-05 enforcer: answer keys must be isolated in teacher_only markers.
    """
    issues: list[str] = []

    html_without_marked = re.sub(
        r'<section[^>]*(?:data-answer-key="true"|data-teacher-only="true")[^>]*>.*?</section>',
        '',
        rendered_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    html_without_marked = re.sub(
        r'<div[^>]*(?:data-answer-key="true"|data-teacher-only="true")[^>]*>.*?</div>',
        '',
        html_without_marked,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if _contains_answer_key_patterns(html_without_marked):
        issues.append(
            "answer_key_patterns_found_outside_marked_sections: "
            "Answer key patterns detected in student-facing content outside teacher_only markers"
        )

    return issues


def remove_answer_keys_from_html(rendered_html: str) -> str:
    """Remove answer key sections and answer-key-marked content from HTML.

    Scans the HTML for sections tagged with `data-answer-key="true"` or
    `data-teacher-only="true"` and removes them. Also sanitizes text patterns
    like "Answer:", "Correct:", "Solution:" from student-visible content.

    Returns the cleaned HTML; if no answer keys found, returns the input unchanged.
    """
    # Remove sections with data-answer-key or data-teacher-only attributes
    html = re.sub(
        r'<section[^>]*(?:data-answer-key="true"|data-teacher-only="true")[^>]*>.*?</section>',
        '',
        rendered_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    html = re.sub(
        r'<div[^>]*(?:data-answer-key="true"|data-teacher-only="true")[^>]*>.*?</div>',
        '',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Remove common answer-key text patterns
    html = re.sub(
        r'(?:Answer\s*(?:Key|:)|Correct\s*(?:Answer|:)|Solution\s*:|Đáp\s*án\s*)[^\n]*',
        '',
        html,
        flags=re.IGNORECASE,
    )

    return html


def bake_effective_slide_deck_display_preferences(
    artifact_type: str,
    content_json: JsonObject,
) -> JsonObject:
    """Freeze resolved ADR-043 display preferences into a slide-deck snapshot.

    `TeachingPackSnapshotStore.create_snapshot` is the single boundary every
    snapshot-persistence path (production export, content-approval gate,
    teacher-triggered re-export) routes through. Resolving preferences once
    here -- instead of leaving `display_preferences` missing/partial in the
    stored `content_json` -- means a later replay of *this exact snapshot*
    reproduces the surface/layout/chrome that was actually in effect at
    export time, even if the deck predates ADR-043 or a future release
    changes the resolver's defaults.

    No-op (returns `content_json` unchanged) for non-slide-deck artifacts or
    a slide deck with no recognizable `metadata.slide_deck_data` payload.
    """
    if artifact_type != "slide_deck":
        return content_json
    metadata = content_json.get("metadata")
    if not isinstance(metadata, dict):
        return content_json
    deck = metadata.get("slide_deck_data")
    if not isinstance(deck, dict):
        return content_json
    raw_preferences = deck.get("display_preferences")
    effective = resolve_slide_deck_display_preferences(
        raw_preferences if isinstance(raw_preferences, dict) else None,
    )
    updated_deck = {**deck, "display_preferences": effective.model_dump()}
    updated_metadata = {**metadata, "slide_deck_data": updated_deck}
    return {**content_json, "metadata": updated_metadata}


def _validate_snapshot_versions(
    payload: ArtifactSnapshotCreate,
    snapshot: ArtifactSnapshot,
) -> None:
    """Validate snapshot versions match expected versions per policy.

    Raises SnapshotVersionMismatchError if mismatch detected with block policy.
    """
    from services.gateway.teaching_pack_snapshot_errors import SnapshotVersionMismatchError

    if payload.version_mismatch_policy == "warn":
        return
    if (
        snapshot.renderer_version != payload.renderer_version
        or snapshot.template_version != payload.template_version
        or snapshot.theme_version != payload.theme_version
    ):
        raise SnapshotVersionMismatchError(snapshot.snapshot_id)

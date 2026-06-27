"""Validators for answer-key isolation and snapshot version consistency.

INVARIANT-05 enforcer: answer keys must be isolated in teacher_only markers.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.gateway.pipeline_v2_snapshot_models import ArtifactSnapshot
    from services.gateway.pipeline_v2_snapshot_schemas import ArtifactSnapshotCreate


def _contains_answer_key_patterns(text: str) -> bool:
    """Check if text contains answer-key patterns.

    Matches: "Answer Key", "Answer:", "Correct Answer", "Correct:", "Solution:"
    Case-insensitive.
    """
    pattern = r'(?:Answer\s*(?:Key|:)|Correct\s*(?:Answer|:)|Solution\s*:)'
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
        r'(?:Answer\s*(?:Key|:)|Correct\s*(?:Answer|:)|Solution\s*:)[^\n]*',
        '',
        html,
        flags=re.IGNORECASE,
    )

    return html


def _validate_snapshot_versions(
    payload: ArtifactSnapshotCreate,
    snapshot: ArtifactSnapshot,
) -> None:
    """Validate snapshot versions match expected versions per policy.

    Raises SnapshotVersionMismatchError if mismatch detected with block policy.
    """
    from services.gateway.pipeline_v2_snapshot_errors import SnapshotVersionMismatchError

    if payload.version_mismatch_policy == "warn":
        return
    if (
        snapshot.renderer_version != payload.renderer_version
        or snapshot.template_version != payload.template_version
        or snapshot.theme_version != payload.theme_version
    ):
        raise SnapshotVersionMismatchError(snapshot.snapshot_id)

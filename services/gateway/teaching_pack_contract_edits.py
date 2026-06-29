from __future__ import annotations

from typing import Final

EDITABLE_CONTRACT_FIELDS: Final[frozenset[str]] = frozenset({
    "artifact_types",
    "citation_locale",
    "curriculum",
    "export_formats",
    "grade_band",
    "instruction_language",
    "locale",
    "research_policy",
    "subject",
    "topic",
})

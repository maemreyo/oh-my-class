"""Diagnostician Agent tools — Bloom taxonomy lookup and question classifier."""

from __future__ import annotations

from typing import Any

_BLOOM_MAP: dict[str, dict[str, Any]] = {
    "remember": {
        "vn_name": "Nhận biết",
        "description": "Recall facts, terminology, definitions",
        "typical_verbs": ["define", "list", "name", "recall", "identify"],
    },
    "understand": {
        "vn_name": "Thông hiểu",
        "description": "Interpret, classify, summarise meaning",
        "typical_verbs": ["explain", "describe", "classify", "summarise", "infer"],
    },
    "apply": {
        "vn_name": "Vận dụng",
        "description": "Use knowledge in new situations",
        "typical_verbs": ["solve", "use", "execute", "implement", "demonstrate"],
    },
    "analyze": {
        "vn_name": "Phân tích",
        "description": "Break down information into parts",
        "typical_verbs": ["differentiate", "organise", "attribute", "compare", "distinguish"],
    },
    "evaluate": {
        "vn_name": "Đánh giá",
        "description": "Make judgements based on criteria",
        "typical_verbs": ["critique", "judge", "justify", "assess", "defend"],
    },
    "create": {
        "vn_name": "Sáng tạo",
        "description": "Produce new or original work",
        "typical_verbs": ["design", "construct", "produce", "devise", "formulate"],
    },
}


def bloom_taxonomy_lookup(bloom_level: str) -> dict[str, Any]:
    """Return Vietnamese name and characteristics for a Bloom taxonomy level."""
    key = bloom_level.lower().strip()
    if key not in _BLOOM_MAP:
        return {
            "bloom_level": bloom_level,
            "vn_name": bloom_level,
            "description": "Unknown Bloom level",
            "typical_verbs": [],
        }
    return {"bloom_level": bloom_level, **_BLOOM_MAP[key]}


def question_type_classifier(
    question_ids: list[str | int],
    section_map: dict[str, str],
) -> dict[str, list[str | int]]:
    """Group question IDs by their section/type using the provided mapping.

    Args:
        question_ids: List of question IDs to classify.
        section_map: Mapping from question_id (str) to section name.

    Returns:
        Dict of section_name → [question_ids].
    """
    result: dict[str, list[str | int]] = {}
    for qid in question_ids:
        section = section_map.get(str(qid), "unknown")
        result.setdefault(section, []).append(qid)
    return result

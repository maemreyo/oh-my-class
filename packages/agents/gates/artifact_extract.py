"""Shared artifact text/URL extraction helpers for component-first content.

LLM output often uses ``section.components`` exclusively (no ``section.content``).
These helpers recursively extract student-facing text and external URLs from any
artifact structure — covering both ``section.content`` strings and nested component
dicts (heading, paragraph, callout, question_card, question_list, and ad-hoc dicts).

Usage from other gates/nodes::

    from packages.agents.gates.artifact_extract import (
        extract_student_text,
        extract_external_urls,
    )
"""
from __future__ import annotations

import re

_URL_PATTERN = re.compile(r"https?://[^\s'\"<>]+")

# Component types that carry text in a ``text`` key.
_TEXT_FIELD_TYPES = frozenset({
    "heading", "paragraph", "question_card",
    "ordered_list", "unordered_list",
    "stat_grid", "pattern_grid", "trait_grid", "taxonomy_grid",
    "flow_step",
    "concept_map", "timeline_component", "vocab_cluster",
    "contrastive_pairs", "phrasal_verb_cluster",
    "film_clip_activity", "roleplay_script", "active_recall_prompt",
})


def _extract_text_from_component(component: object) -> str:
    """Extract visible text from a single component dict."""
    if not isinstance(component, dict):
        return ""

    comp_type = component.get("type", "")

    if comp_type == "callout":
        return str(component.get("body", ""))

    if comp_type == "question_card":
        parts = [component.get("text", ""), component.get("explain", "")]
        return " ".join(p for p in parts if isinstance(p, str) and p.strip())

    if comp_type == "question_list":
        parts: list[str] = []
        for q in component.get("questions", []):
            if isinstance(q, dict):
                parts.append(q.get("text", ""))
                parts.append(q.get("explain", ""))
        return " ".join(p for p in parts if isinstance(p, str) and p.strip())

    if comp_type == "ordered_list" or comp_type == "unordered_list":
        items = component.get("items", [])
        return " ".join(str(i) for i in items if i)

    if comp_type in _TEXT_FIELD_TYPES:
        return str(component.get("text", ""))

    # Fallback: any dict with text/body keys, or str repr for unknown types.
    for key in ("text", "body", "content", "label", "title"):
        val = component.get(key)
        if isinstance(val, str) and val.strip():
            return val

    return ""


def extract_student_text_from_sections(sections: list[dict[str, object]]) -> str:
    """Extract concatenated student-facing text from a list of section dicts.

    Skips sections where ``teacher_only`` is truthy.
    Pulls text from both ``section.content`` (string) and ``section.components``
    (list of typed component dicts).
    """
    parts: list[str] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        if section.get("teacher_only"):
            continue

        # 1. Plain content string.
        content = section.get("content")
        if isinstance(content, str) and content.strip():
            parts.append(content.strip())

        # 2. Components list.
        components = section.get("components")
        if isinstance(components, list):
            for comp in components:
                text = _extract_text_from_component(comp)
                if text.strip():
                    parts.append(text.strip())

    return "\n".join(parts)


def extract_student_text(artifact: dict[str, object]) -> str:
    """Extract concatenated student-facing text from an artifact dict.

    The artifact must have a ``"sections"`` key containing a list of section dicts.
    Sections marked ``teacher_only=True`` are excluded.
    """
    sections = artifact.get("sections")
    if not isinstance(sections, list):
        return ""
    return extract_student_text_from_sections(sections)


def extract_urls_from_sections(sections: list[dict[str, object]]) -> list[str]:
    """Return all ``http://`` / ``https://`` URLs found in student-facing section text.

    Extracts URLs from both ``section.content`` strings and nested component text.
    Deduplicates while preserving first-seen order.
    """
    text = extract_student_text_from_sections(sections)
    return list(dict.fromkeys(_URL_PATTERN.findall(text)))


def extract_external_urls(artifact: dict[str, object]) -> list[str]:
    """Return all ``http://`` / ``https://`` URLs in student-facing artifact content.

    Extracts from both ``section.content`` strings and nested component text.
    Deduplicates while preserving first-seen order.
    """
    sections = artifact.get("sections")
    if not isinstance(sections, list):
        return []
    return extract_urls_from_sections(sections)

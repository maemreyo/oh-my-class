"""Layer 2 — Component usage intelligence scorer (soft gate).

Scores whether component usage is diverse, pedagogically aligned, and
not merely stuffed.  Baseline ~5/10; rewards diversity and methodology
alignment; penalises overuse and stuffing.

Reuses ``_extract_components`` from ``layer1_schema.component_gate``
so nested ``section.components`` is handled consistently.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Final

from common.contracts.components.registry import PedagogicalIntent, get_entry
from packages.quality.layer1_schema.component_gate import extract_components

# ── Methodology keyword → component type matching ────────────────────────────
# Keywords that a methodology-aligned lesson should surface via its components.
_METHODLOGY_KEYWORDS: Final[dict[str, list[str]]] = {
    "vocab": ["vocab_cluster", "phrasal_verb_cluster"],
    "concept_map": ["concept_map", "vocab_cluster", "contrastive_pairs"],
    "contrastive_pairs": ["contrastive_pairs"],
    "film_based": ["film_clip_activity"],
    "roleplay": ["roleplay_script"],
    "active_recall": ["active_recall_prompt"],
    "why_wrong_reasoning": ["question_card"],
}

_INTENTS_TOTAL: Final[int] = len(PedagogicalIntent)


@dataclass(frozen=True, slots=True)
class ComponentScoringResult:
    """Immutable result of component usage scoring."""

    score: float
    base_score: float
    diversity_ratio: float
    overuse_penalty: float
    stuffing_penalty: float
    methodology_bonus: float
    component_count: int
    unique_intents: int
    overused_types: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _count_type(
    components: list[Mapping[str, object]],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for comp in components:
        t = str(comp.get("type", ""))
        if t:
            counts[t] = counts.get(t, 0) + 1
    return counts


def _intents_present(
    components: list[Mapping[str, object]],
) -> set[PedagogicalIntent]:
    intents: set[PedagogicalIntent] = set()
    for comp in components:
        t = str(comp.get("type", ""))
        try:
            intents.add(get_entry(t).intent)
        except KeyError:
            continue
    return intents


def _methodology_tags(
    lesson_plan: Mapping[str, object] | None,
) -> list[str]:
    if lesson_plan is None:
        return []
    methodology = lesson_plan.get("methodology")
    if isinstance(methodology, Mapping):
        tags = methodology.get("tags")
        if isinstance(tags, list):
            return [str(t) for t in tags]
    tags = lesson_plan.get("methodology_tags")
    if isinstance(tags, list):
        return [str(t) for t in tags]
    return []


def score_component_usage(
    artifact: Mapping[str, object],
    lesson_plan: Mapping[str, object] | None = None,
) -> ComponentScoringResult:
    """Score component usage quality for a single artifact.

    Scoring model (0–10):

    - base = 5.0 (neutral)
    - + diversity bonus: up to +2.5 for intent spread across all 8 intents
    - − stuffing penalty: −1.0 to −3.0 when many components but low diversity
    - − overuse penalty: −0.5 per type exceeding ``max_per_artifact``
    - + methodology alignment bonus: up to +2.0 for matching lesson-plan tags
    - Clamped to [0.0, 10.0].
    """
    sections_raw = artifact.get("sections", [])
    if not isinstance(sections_raw, list):
        sections_raw = []

    components = extract_components(sections_raw)
    comp_count = len(components)
    type_counts = _count_type(components)
    intents = _intents_present(components)
    intent_count = len(intents)

    notes: list[str] = []
    base_score = 5.0

    # ── Diversity bonus (0–2.5) ──────────────────────────────────────────────
    diversity_ratio = intent_count / _INTENTS_TOTAL
    diversity_bonus = diversity_ratio * 2.5

    # ── Stuffing penalty ─────────────────────────────────────────────────────
    stuffing_penalty = 0.0
    if comp_count >= 4 and intent_count <= 1:
        stuffing_penalty = min(3.0, comp_count * 0.3)
        notes.append(
            f"stuffing: {comp_count} components but only {intent_count} intent(s)"
        )
    elif comp_count >= 6 and intent_count <= 2:
        stuffing_penalty = min(2.0, (comp_count - intent_count) * 0.2)
        notes.append(
            f"near-stuffing: {comp_count} components, {intent_count} intents"
        )

    # ── Overuse penalty ──────────────────────────────────────────────────────
    overuse_penalty = 0.0
    overused: list[str] = []
    for comp_type, count in type_counts.items():
        try:
            entry = get_entry(comp_type)
        except KeyError:
            continue
        if entry.max_per_artifact is not None and count > entry.max_per_artifact:
            excess = count - entry.max_per_artifact
            overuse_penalty += excess * 0.5
            overused.append(comp_type)
            notes.append(
                f"overuse: {comp_type} ×{count} exceeds max {entry.max_per_artifact}"
            )

    # ── Methodology alignment bonus (0–2.0) ──────────────────────────────────
    methodology_bonus = 0.0
    tags = _methodology_tags(lesson_plan)
    if tags:
        matched = 0
        for tag in tags:
            required_types = _METHODLOGY_KEYWORDS.get(tag)
            if required_types is None:
                continue
            if any(t in type_counts for t in required_types):
                matched += 1
                notes.append(f"methodology matched: {tag}")
        methodology_bonus = min(2.0, (matched / len(tags)) * 2.0)

    # ── Compose ──────────────────────────────────────────────────────────────
    raw = (
        base_score
        + diversity_bonus
        - stuffing_penalty
        - overuse_penalty
        + methodology_bonus
    )
    final = max(0.0, min(10.0, round(raw, 2)))

    return ComponentScoringResult(
        score=final,
        base_score=base_score,
        diversity_ratio=round(diversity_ratio, 3),
        overuse_penalty=round(overuse_penalty, 2),
        stuffing_penalty=round(stuffing_penalty, 2),
        methodology_bonus=round(methodology_bonus, 2),
        component_count=comp_count,
        unique_intents=intent_count,
        overused_types=overused,
        notes=notes,
    )

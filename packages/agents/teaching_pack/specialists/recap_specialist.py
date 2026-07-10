"""Synthesis specialist: grounded compression for the Recap artifact (ADR-053/054, #439).

Deterministic and extractive by design -- every retained concept is a
verbatim (lightly trimmed) sentence from an approved learning objective or
a research finding with a fetched excerpt, never freely generated prose.
"Every retained concept traces to approved context" is therefore
structural: each concept's `source_ref` points at the exact input item it
came from, carried in `metadata.retained_concept_traces` for downstream
inspection (mirrors the existing `_stamp_research_sources`/
`_stamp_pedagogy_context` metadata pattern in generate_one_artifact.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

MAX_RETAINED_CONCEPTS = 6


class NoGroundedConceptsError(ValueError):
    """Raised when neither approved objectives nor fetched research findings
    exist to compress -- there is nothing grounded to retain, so this fails
    closed rather than fabricating a recap from nothing."""


@dataclass(frozen=True, slots=True)
class RetainedConcept:
    entity_id: str
    text: str
    source_type: Literal["objective", "research_finding"]
    source_ref: str


@dataclass(frozen=True, slots=True)
class RecapScorecard:
    """The four dimensions #439 asks for. Each is independently meaningful:
    compression and coverage can diverge (a recap can retain few *items* but
    long ones, or many short ones); recall_utility isolates objective
    coverage specifically, since findings are supporting detail, not the
    lesson's stated goals."""

    compression_ratio: float
    recall_utility: float
    coverage: float
    consistency: bool


def _objectives(lesson_plan: dict[str, Any]) -> list[str]:
    """`learning_objectives` is canonically `list[LearningObjective]`
    (`common/contracts/lesson_plan.py`) -- each item a dict with a
    `description` field -- but a bare `list[str]` is tolerated too, since
    some seams (e.g. `common/contracts/lesson_sequence.py`) use that shape."""
    objectives = lesson_plan.get("learning_objectives")
    if not isinstance(objectives, list):
        return []
    texts: list[str] = []
    for item in objectives:
        if isinstance(item, str) and (text := item.strip()):
            texts.append(text)
        elif isinstance(item, dict) and isinstance(item.get("description"), str):
            text = item["description"].strip()
            if text:
                texts.append(text)
    return texts


def _findings(research_brief: dict[str, Any]) -> list[tuple[str, str]]:
    """(text, source_ref) pairs -- only sources with a fetched excerpt are
    grounded; a source description alone is not approved context."""
    sources = research_brief.get("sources")
    if not isinstance(sources, list):
        return []
    findings: list[tuple[str, str]] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        excerpt = source.get("excerpt")
        if not isinstance(excerpt, str) or not excerpt.strip():
            continue
        first_sentence = excerpt.strip().split(". ")[0].strip().rstrip(".") + "."
        source_ref = str(source.get("title") or source.get("url") or "source").strip()
        findings.append((first_sentence, source_ref))
    return findings


def compress_recap(
    lesson_plan: dict[str, Any],
    research_brief: dict[str, Any],
    *,
    max_concepts: int = MAX_RETAINED_CONCEPTS,
) -> list[RetainedConcept]:
    """Select the concepts a recap retains -- objectives first (the lesson's
    stated goals), then research findings, bounded to `max_concepts`."""
    concepts: list[RetainedConcept] = [
        RetainedConcept(
            entity_id=f"concept-objective-{index}",
            text=objective,
            source_type="objective",
            source_ref=f"objective-{index}",
        )
        for index, objective in enumerate(_objectives(lesson_plan))
    ]
    concepts.extend(
        RetainedConcept(
            entity_id=f"concept-finding-{index}",
            text=text,
            source_type="research_finding",
            source_ref=source_ref,
        )
        for index, (text, source_ref) in enumerate(_findings(research_brief))
    )
    return concepts[:max_concepts]


def score_recap(
    lesson_plan: dict[str, Any],
    research_brief: dict[str, Any],
    concepts: list[RetainedConcept],
) -> RecapScorecard:
    objectives = _objectives(lesson_plan)
    findings = _findings(research_brief)
    total_chars_available = sum(len(o) for o in objectives) + sum(len(t) for t, _ in findings)
    total_chars_retained = sum(len(c.text) for c in concepts)
    compression_ratio = (
        round(total_chars_retained / total_chars_available, 3) if total_chars_available else 0.0
    )
    retained_objective_refs = {c.source_ref for c in concepts if c.source_type == "objective"}
    recall_utility = round(len(retained_objective_refs) / len(objectives), 3) if objectives else 0.0
    total_items = len(objectives) + len(findings)
    retained_refs = {c.source_ref for c in concepts}
    coverage = round(len(retained_refs) / total_items, 3) if total_items else 0.0
    entity_ids = [c.entity_id for c in concepts]
    consistency = len(entity_ids) == len(set(entity_ids))
    return RecapScorecard(
        compression_ratio=compression_ratio,
        recall_utility=recall_utility,
        coverage=coverage,
        consistency=consistency,
    )


_LABEL_MAX_WORDS = 6


def _concept_label(text: str) -> str:
    """A short "concept" label for the renderer's card heading -- the first
    few words of the retained text, since the full text is the card body."""
    words = text.split()
    label = " ".join(words[:_LABEL_MAX_WORDS])
    return label if len(words) <= _LABEL_MAX_WORDS else f"{label}…"


def generate_recap_artifact(
    lesson_plan: dict[str, Any],
    research_brief: dict[str, Any],
    *,
    theme: str = "default",
) -> dict[str, Any]:
    """Produce an `ArtifactContent`-shaped dict (common/contracts/artifact.py) for
    a `recap` artifact -- the Synthesis specialist's real output, not a
    generic LLM prompt loop's guess at "recap"."""
    concepts = compress_recap(lesson_plan, research_brief)
    if not concepts:
        raise NoGroundedConceptsError(
            "no approved learning objectives or fetched research findings to compress",
        )
    scorecard = score_recap(lesson_plan, research_brief, concepts)
    topic = str(lesson_plan.get("topic") or lesson_plan.get("title") or "the lesson").strip()
    return {
        "artifact_type": "recap",
        "theme": theme,
        "title": f"Recap: {topic}",
        # One section per retained concept -- `packages/renderer/src/agent-renderer.ts`'s
        # `recapData()` flattens one section into one recap card (`section.title` ->
        # `concept`, `section.content` -> `summary`); it has no notion of a
        # per-section items list, so nesting concepts under one section would
        # silently drop every concept but the section title itself.
        "sections": [
            {
                "id": concept.entity_id,
                "title": _concept_label(concept.text),
                "content": concept.text,
            }
            for concept in concepts
        ],
        "metadata": {
            "retained_concept_traces": [
                {"entity_id": c.entity_id, "source_type": c.source_type, "source_ref": c.source_ref}
                for c in concepts
            ],
            "recap_scorecard": {
                "compression_ratio": scorecard.compression_ratio,
                "recall_utility": scorecard.recall_utility,
                "coverage": scorecard.coverage,
                "consistency": scorecard.consistency,
            },
        },
    }

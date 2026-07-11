"""Registry-driven specialist for the Flashcard Deck artifact (ADR-053, #441).

Deterministic and extractive, same discipline as `recap_specialist.py`:
every card's front/back pair is built from an approved learning objective
or a research finding with a fetched excerpt, never freely generated
prose. Card ids are derived from the source item's stable position
(`objective-{i}`/`finding-{i}`), not a counter reset per run, so
regenerating from the same approved context reproduces the same ids
(#441 AC1: "identity semantics survive compatible edits and restoration").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from common.contracts.grade_band import FlashcardGradeBand

MAX_CARDS = 12
_GRADE_WORD_BAND: dict[FlashcardGradeBand, tuple[int, int]] = {
    # (min_words, max_words) a card's back is expected to fall within for
    # the grade band to count as a comfortable read -- a coarse, real
    # heuristic, not a readability-formula replacement.
    FlashcardGradeBand.ELEMENTARY: (2, 12),
    FlashcardGradeBand.MIDDLE: (3, 20),
    FlashcardGradeBand.HIGH: (4, 30),
}


class NoGroundedTermsError(ValueError):
    """Raised when neither approved objectives nor fetched research findings
    exist to build cards from -- there is nothing grounded to test, so this
    fails closed rather than fabricating flashcards from nothing."""


@dataclass(frozen=True, slots=True)
class FlashcardEntry:
    entity_id: str
    front: str
    back: str
    source_type: str
    source_ref: str


@dataclass(frozen=True, slots=True)
class FlashcardScorecard:
    """The four dimensions #441 asks for."""

    recall_value: float
    ambiguity: float
    duplication: float
    grade_fit: float


def _objectives(lesson_plan: dict[str, Any]) -> list[str]:
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


def _front_label(text: str, *, max_words: int = 6) -> str:
    words = text.split()
    label = " ".join(words[:max_words])
    return label if len(words) <= max_words else f"{label}…"


def build_flashcards(
    lesson_plan: dict[str, Any],
    research_brief: dict[str, Any],
    *,
    max_cards: int = MAX_CARDS,
) -> list[FlashcardEntry]:
    """Front = a short label naming the concept; back = the full grounded text --
    the pair a student actually studies from, never an invented definition."""
    entries: list[FlashcardEntry] = [
        FlashcardEntry(
            entity_id=f"card-objective-{index}",
            front=_front_label(objective),
            back=objective,
            source_type="objective",
            source_ref=f"objective-{index}",
        )
        for index, objective in enumerate(_objectives(lesson_plan))
    ]
    entries.extend(
        FlashcardEntry(
            entity_id=f"card-finding-{index}",
            front=_front_label(text),
            back=text,
            source_type="research_finding",
            source_ref=source_ref,
        )
        for index, (text, source_ref) in enumerate(_findings(research_brief))
    )
    return entries[:max_cards]


def score_flashcards(
    entries: list[FlashcardEntry],
    *,
    grade_band: FlashcardGradeBand | None = None,
) -> FlashcardScorecard:
    if not entries:
        return FlashcardScorecard(recall_value=0.0, ambiguity=0.0, duplication=0.0, grade_fit=0.0)
    substantive = sum(1 for e in entries if len(e.back.split()) >= 2)
    recall_value = round(substantive / len(entries), 3)
    fronts = [e.front.casefold() for e in entries]
    unique_fronts = len(set(fronts))
    ambiguity = round(1 - (unique_fronts / len(fronts)), 3)  # 0 = no ambiguous duplicates
    backs = [e.back.casefold() for e in entries]
    unique_backs = len(set(backs))
    duplication = round(1 - (unique_backs / len(backs)), 3)  # 0 = no duplicate answers
    band = _GRADE_WORD_BAND.get(grade_band)
    if band is None:
        grade_fit = 1.0  # no declared band to check against -- not penalized
    else:
        low, high = band
        in_band = sum(1 for e in entries if low <= len(e.back.split()) <= high)
        grade_fit = round(in_band / len(entries), 3)
    return FlashcardScorecard(
        recall_value=recall_value,
        ambiguity=ambiguity,
        duplication=duplication,
        grade_fit=grade_fit,
    )


def generate_flashcard_deck_artifact(
    lesson_plan: dict[str, Any],
    research_brief: dict[str, Any],
    *,
    theme: str = "default",
    subject: str = "General",
    grade_band: FlashcardGradeBand | None = None,
) -> dict[str, Any]:
    """Produce an `ArtifactContent`-shaped dict for a `flashcard_deck` artifact.

    Cards live at `sections[0]["cards"]` -- the shape
    `packages/exporters/src/cli.ts::buildDeck` and the flashcard-deck
    renderer plugin actually consume (verified against those, not just
    against the loosely-typed `ArtifactContent.sections` contract, per the
    lesson learned generalizing the Recap specialist: contract validation
    passing is not proof the renderer/exporter can read the shape).
    """
    entries = build_flashcards(lesson_plan, research_brief)
    if not entries:
        raise NoGroundedTermsError(
            "no approved learning objectives or fetched research findings to build cards from",
        )
    scorecard = score_flashcards(entries, grade_band=grade_band)
    topic = str(lesson_plan.get("topic") or lesson_plan.get("title") or "the lesson").strip()
    grade_level = str(lesson_plan.get("grade_level") or lesson_plan.get("grade") or "").strip()
    return {
        "artifact_type": "flashcard_deck",
        "theme": theme,
        "title": f"Flashcards: {topic}",
        "sections": [{
            "heading": "Key Terms",
            "cards": [
                {"id": entry.entity_id, "front": entry.front, "back": entry.back}
                for entry in entries
            ],
        }],
        "metadata": {
            "subject": subject,
            "gradeLevel": grade_level,
            "card_traces": [
                {"entity_id": e.entity_id, "source_type": e.source_type, "source_ref": e.source_ref}
                for e in entries
            ],
            "flashcard_scorecard": {
                "recall_value": scorecard.recall_value,
                "ambiguity": scorecard.ambiguity,
                "duplication": scorecard.duplication,
                "grade_fit": scorecard.grade_fit,
            },
        },
    }

"""#464: typed, three-way capability resolution for artifact generation.

Production resolution must return supported, degraded-with-explicit-policy,
or unsupported -- never a silent generic fallback. This module is the one
place that decision gets made; `generate_one_artifact.py` consumes its
result instead of re-deriving the same registry/native-dispatch/flag checks
inline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from packages.agents.teaching_pack.specialist_registry import SPECIALIST_REGISTRY, get_specialist

CapabilityStatus = Literal["supported", "degraded", "unsupported"]
PayloadKind = Literal["assessment_document", "rich_document", "slide_deck_document"]

NATIVELY_DISPATCHED_ARTIFACT_TYPES = frozenset({"answer_key", "slide_deck"})

# Single source of truth for which artifact types get a separate AnswerSet
# derived by `generate_one_artifact.derive_answer_set` -- referenced there
# directly (not duplicated) so the two can never drift.
ANSWER_SET_ARTIFACT_TYPES = frozenset({"quiz", "drill", "exit_ticket"})


@dataclass(frozen=True, slots=True)
class SpecialistCapabilityDeclaration:
    """#464: "declared ... payload ... capabilities" for one artifact type.

    Deliberately narrow to mechanically verifiable properties -- `payload_kind`
    (which `ArtifactPayload` variant `artifact_projection_mapper.py` produces)
    and `answer_bearing` (whether a separate `AnswerSet` is derived). Declaring
    subject/grade/language specificity per specialist would be fabricated: the
    ten registered specialists are subject/grade-general (no specialist rejects
    or branches on subject or grade band today), so a "certified for Grade 5
    Math" claim here would be untrue. `subject_capability_pack.py` is the real,
    honest source for subject/grade-scoped claims.
    """

    artifact_type: str
    payload_kind: PayloadKind
    # True iff generated content for this type carries teacher-only answer
    # material that must be separated before a student sees it -- via a
    # derived `AnswerSet` (quiz/drill/exit_ticket, `ANSWER_SET_ARTIFACT_TYPES`)
    # or via the slide deck's own `teacher_only`/`teacher_notes` stripping
    # (#463, `artifact_projection_mapper._student_safe_slide_deck`).
    answer_bearing: bool


# Payload kind per common.contracts.artifact_projection_mapper's dispatch:
# `_ASSESSMENT_TYPES = {"quiz", "drill", "exit_ticket"}` -> assessment_document;
# `"slide_deck"` -> slide_deck_document; everything else -> rich_document.
SPECIALIST_CAPABILITIES: dict[str, SpecialistCapabilityDeclaration] = {
    "lesson": SpecialistCapabilityDeclaration("lesson", "rich_document", False),
    "worksheet": SpecialistCapabilityDeclaration("worksheet", "rich_document", False),
    "quiz": SpecialistCapabilityDeclaration("quiz", "assessment_document", True),
    "drill": SpecialistCapabilityDeclaration("drill", "assessment_document", True),
    "roadmap": SpecialistCapabilityDeclaration("roadmap", "rich_document", False),
    "reading_passage": SpecialistCapabilityDeclaration("reading_passage", "rich_document", False),
    "infographic": SpecialistCapabilityDeclaration("infographic", "rich_document", False),
    "exit_ticket": SpecialistCapabilityDeclaration("exit_ticket", "assessment_document", True),
    "recap": SpecialistCapabilityDeclaration("recap", "rich_document", False),
    "flashcard_deck": SpecialistCapabilityDeclaration("flashcard_deck", "rich_document", False),
    "answer_key": SpecialistCapabilityDeclaration("answer_key", "rich_document", False),
    "slide_deck": SpecialistCapabilityDeclaration("slide_deck", "slide_deck_document", True),
}


def capability_declaration_for(artifact_type: str) -> SpecialistCapabilityDeclaration | None:
    return SPECIALIST_CAPABILITIES.get(artifact_type)


SpecialistFamily = Literal["lesson_design", "assessment", "practice", "synthesis", "presentation"]

# #464: "Register five specialist families" -- the exact grouping ADR-053
# names (decision section "Five Artifact Specialist families", lines 36-40):
# 1. Lesson Design -- lesson
# 2. Assessment -- quiz, exit_ticket, and the derived answer_key
# 3. Practice -- worksheet, drill, flashcard_deck
# 4. Synthesis -- recap, infographic, roadmap, reading_passage
# 5. Presentation -- slide_deck
SPECIALIST_FAMILIES: dict[str, SpecialistFamily] = {
    "lesson": "lesson_design",
    "quiz": "assessment",
    "exit_ticket": "assessment",
    "answer_key": "assessment",
    "worksheet": "practice",
    "drill": "practice",
    "flashcard_deck": "practice",
    "recap": "synthesis",
    "infographic": "synthesis",
    "roadmap": "synthesis",
    "reading_passage": "synthesis",
    "slide_deck": "presentation",
}


def family_for(artifact_type: str) -> SpecialistFamily | None:
    return SPECIALIST_FAMILIES.get(artifact_type)


@dataclass(frozen=True, slots=True)
class CapabilityResolution:
    """The outcome of resolving one artifact type's generation capability."""

    artifact_type: str
    status: CapabilityStatus
    specialist_id: str | None = None
    policy_note: str | None = None
    supported_alternatives: tuple[str, ...] = ()


def resolve_specialist_capability(
    artifact_type: str,
    *,
    generic_fallback_enabled: bool,
) -> CapabilityResolution:
    """Resolve `artifact_type` before any LLM call.

    - `supported`: a registered specialist or native dispatch branch exists.
    - `degraded`: no specialist exists, but the caller has explicitly opted
      into the experimental generic content-creator path
      (`generic_content_creator_fallback_v1`) -- `policy_note` names the
      explicit policy this reach falls under; never labeled certified.
    - `unsupported`: fails closed, naming the artifact types that ARE
      supported so the caller has an actionable alternative.
    """
    if artifact_type in NATIVELY_DISPATCHED_ARTIFACT_TYPES:
        return CapabilityResolution(
            artifact_type=artifact_type,
            status="supported",
            specialist_id=f"native:{artifact_type}",
        )
    if get_specialist(artifact_type) is not None:
        return CapabilityResolution(
            artifact_type=artifact_type,
            status="supported",
            specialist_id=f"registry:{artifact_type}",
        )
    supported_alternatives = tuple(sorted({*SPECIALIST_REGISTRY, *NATIVELY_DISPATCHED_ARTIFACT_TYPES}))
    if generic_fallback_enabled:
        return CapabilityResolution(
            artifact_type=artifact_type,
            status="degraded",
            policy_note=(
                "generic_content_creator_fallback_v1: experimental/development-only "
                "reach for an undeclared artifact type; output is never certified"
            ),
            supported_alternatives=supported_alternatives,
        )
    return CapabilityResolution(
        artifact_type=artifact_type,
        status="unsupported",
        supported_alternatives=supported_alternatives,
    )

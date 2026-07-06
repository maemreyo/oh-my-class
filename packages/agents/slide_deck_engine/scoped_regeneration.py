from __future__ import annotations

from typing import assert_never

from common.contracts.slide_deck import SlideDeckData, SlideDeckInteraction, SlideDeckSlide, SlideDeckTeacherOnly

from packages.agents.slide_deck_engine.models import (
    SlideDeckEngineRequest,
    SlideDeckFeedbackTarget,
    SlideDeckHealingScope,
    SlideDeckScopedRepairReport,
)
from packages.agents.slide_deck_engine.quality import redact_trace_text


def feedback_target_from_request(request: SlideDeckEngineRequest) -> SlideDeckFeedbackTarget:
    feedback = request.teacher_constraints.get("slide_deck_feedback")
    if isinstance(feedback, dict):
        return SlideDeckFeedbackTarget.model_validate(feedback)
    if request.revision_feedback:
        return SlideDeckFeedbackTarget(scope="deck", reason=request.revision_feedback)
    return SlideDeckFeedbackTarget()


def apply_scoped_feedback(deck: SlideDeckData, target: SlideDeckFeedbackTarget) -> tuple[SlideDeckData, SlideDeckScopedRepairReport]:
    preserved_slide_ids = [slide.slide_id for slide in deck.slides]
    match target.scope:
        case "none":
            return deck, SlideDeckScopedRepairReport(preserved_slide_ids=preserved_slide_ids)
        case "deck":
            return _apply_deck_feedback(deck, target, preserved_slide_ids)
        case "slide":
            return _apply_slide_feedback(deck, target, preserved_slide_ids)
        case "block":
            return _apply_block_feedback(deck, target)
        case "interaction":
            return _apply_interaction_feedback(deck, target)
        case unreachable:
            assert_never(unreachable)


def _apply_deck_feedback(
    deck: SlideDeckData,
    target: SlideDeckFeedbackTarget,
    preserved_slide_ids: list[str],
) -> tuple[SlideDeckData, SlideDeckScopedRepairReport]:
    next_deck = deck.model_copy(update={"theme": target.theme}) if target.theme else deck
    return next_deck, SlideDeckScopedRepairReport(
        requested_scope="deck",
        applied_scope="deck",
        target_id=target.deck_id or deck.deck_id,
        reason=redact_trace_text(target.reason),
        preserved_slide_ids=preserved_slide_ids,
    )


def _apply_slide_feedback(
    deck: SlideDeckData,
    target: SlideDeckFeedbackTarget,
    preserved_slide_ids: list[str],
) -> tuple[SlideDeckData, SlideDeckScopedRepairReport]:
    if _requires_plan_scope(target.reason):
        return deck, _escalated_report(target, "plan", "feedback affects objective coverage or pacing", preserved_slide_ids)
    slides = [_repair_slide(slide, target) for slide in deck.slides]
    return deck.model_copy(update={"slides": slides}), SlideDeckScopedRepairReport(
        requested_scope="slide",
        applied_scope="slide",
        target_id=target.slide_id,
        reason=redact_trace_text(target.reason),
        preserved_slide_ids=[slide_id for slide_id in preserved_slide_ids if slide_id != target.slide_id],
    )


def _apply_block_feedback(
    deck: SlideDeckData,
    target: SlideDeckFeedbackTarget,
) -> tuple[SlideDeckData, SlideDeckScopedRepairReport]:
    slides = [_repair_block_in_slide(slide, target) for slide in deck.slides]
    return deck.model_copy(update={"slides": slides}), SlideDeckScopedRepairReport(
        requested_scope="block",
        applied_scope="block",
        target_id=target.block_id,
        reason=redact_trace_text(target.reason),
        preserved_slide_ids=[slide.slide_id for slide in deck.slides if not _slide_has_block(slide, target.block_id)],
    )


def _apply_interaction_feedback(
    deck: SlideDeckData,
    target: SlideDeckFeedbackTarget,
) -> tuple[SlideDeckData, SlideDeckScopedRepairReport]:
    slides = [_repair_interaction_in_slide(slide, target) for slide in deck.slides]
    return deck.model_copy(update={"slides": slides}), SlideDeckScopedRepairReport(
        requested_scope="interaction",
        applied_scope="block",
        target_id=target.interaction_id,
        reason=redact_trace_text(target.reason),
        preserved_slide_ids=[slide.slide_id for slide in deck.slides if not _slide_has_interaction(slide, target.interaction_id)],
    )


def _repair_slide(slide: SlideDeckSlide, target: SlideDeckFeedbackTarget) -> SlideDeckSlide:
    if slide.slide_id != target.slide_id:
        return slide
    repaired_blocks = slide.blocks[:4]
    repaired_interactions = slide.interactions[:2]
    note = redact_trace_text(target.reason or "Scoped slide feedback applied.")
    teacher_notes = slide.teacher_notes or SlideDeckTeacherOnly()
    return slide.model_copy(update={
        "blocks": repaired_blocks,
        "interactions": repaired_interactions,
        "teacher_notes": teacher_notes.model_copy(update={
            "facilitation_notes": [*teacher_notes.facilitation_notes, note],
        }),
    })


def _repair_block_in_slide(slide: SlideDeckSlide, target: SlideDeckFeedbackTarget) -> SlideDeckSlide:
    blocks = [block.model_copy(update={"body": target.replacement_text}) if block.block_id == target.block_id and target.replacement_text else block for block in slide.blocks]
    return slide.model_copy(update={"blocks": blocks})


def _repair_interaction_in_slide(slide: SlideDeckSlide, target: SlideDeckFeedbackTarget) -> SlideDeckSlide:
    interactions = [_repair_interaction(interaction, target) for interaction in slide.interactions]
    return slide.model_copy(update={"interactions": interactions})


def _repair_interaction(interaction: SlideDeckInteraction, target: SlideDeckFeedbackTarget) -> SlideDeckInteraction:
    if interaction.interaction_id != target.interaction_id:
        return interaction
    if interaction.teacher_only is None:
        return interaction
    return interaction.model_copy(update={
        "teacher_only": interaction.teacher_only.model_copy(update={
            "rationale": "Answer remains in teacher-only projection after scoped feedback.",
        }),
    })


def _escalated_report(
    target: SlideDeckFeedbackTarget,
    applied_scope: SlideDeckHealingScope,
    escalation_reason: str,
    preserved_slide_ids: list[str],
) -> SlideDeckScopedRepairReport:
    return SlideDeckScopedRepairReport(
        requested_scope=target.scope,
        applied_scope=applied_scope,
        target_id=target.slide_id or target.block_id or target.interaction_id or target.deck_id,
        reason=redact_trace_text(target.reason),
        escalated=True,
        escalation_reason=escalation_reason,
        preserved_slide_ids=preserved_slide_ids,
    )


def _requires_plan_scope(reason: str) -> bool:
    normalized = reason.lower()
    return "objective" in normalized or "pacing" in normalized


def _slide_has_block(slide: SlideDeckSlide, block_id: str) -> bool:
    return any(block.block_id == block_id for block in slide.blocks)


def _slide_has_interaction(slide: SlideDeckSlide, interaction_id: str) -> bool:
    return any(interaction.interaction_id == interaction_id for interaction in slide.interactions)

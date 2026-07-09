"""Deck-wide bilingual (EN<->VI) translation pass (SDX-01).

ADR-047 decision 4's exception: translation is a 1:1 text substitution across
every block with no layout/structure change, so unlike the block-scoped
AI-rewrite action it is allowed to run at deck scope. Produces a new,
independent `SlideDeckData` (own `deck_id`, fresh slide/block/interaction
IDs) that references its source via `SlideDeckSnapshotLineage` — it never
mutates the source deck.

Scope decisions (keep the "1:1 text substitution" promise honest and small):
- `SlideDeckSourceRef.title`/`citation` (bibliographic citations) and
  `SlideDeckRelatedArtifactRef.relationship_label` are left untranslated —
  citations should read the same regardless of deck language, and
  related-artifact refs point at same-run artifacts that don't change
  language either. Revisit if a real deck exercises this.
- `SlideDeckMedia` is copied verbatim (including `media_id`) — media assets
  themselves are unaffected by translation.
- On any translation failure (LLM error, invalid schema, or the translated
  text failing registry/density/accessibility validation), the whole pass
  falls back to the original, untranslated text — never a placeholder,
  matching `content_materialization.py`'s existing all-or-nothing precedent.
"""

from __future__ import annotations

from typing import Final, Literal

from pydantic import ValidationError

from common.contracts.slide_deck import SlideDeckData

from packages.agents.slide_deck_engine.phases.content_materialization_llm import translate_slide_deck_wording
from packages.agents.slide_deck_engine.phases.density_accessibility_audit import audit_density_and_accessibility
from packages.agents.slide_deck_engine.quality import validate_registry_membership, validate_teacher_only_separation

SlideDeckTranslationLanguage = Literal["en", "vi"]
SUPPORTED_TRANSLATION_LANGUAGES: Final[tuple[SlideDeckTranslationLanguage, ...]] = ("en", "vi")


class UnsupportedTranslationLanguageError(ValueError):
    """Raised for any target language outside EN<->VI — no generic language framework."""

    def __init__(self, target_language: str) -> None:
        self.target_language = target_language
        super().__init__(
            f"unsupported slide deck translation target language: {target_language!r} "
            f"(only {SUPPORTED_TRANSLATION_LANGUAGES!r} are supported)",
        )


async def translate_slide_deck(
    deck: SlideDeckData,
    *,
    run_id: str,
    target_language: SlideDeckTranslationLanguage,
    source_snapshot_id: str,
) -> SlideDeckData:
    """Return a new, independent deck translated 1:1 into `target_language`.

    Never mutates `deck`. Always returns a deck that passes registry/density/
    accessibility validation the same way any other `ContentMaterializer`
    output does: if the fully-translated text fails one of those gates (or
    the LLM call fails/returns an invalid schema), falls back to the
    untranslated source text for the whole pass — the new deck still gets a
    fresh `deck_id`/IDs and a lineage reference even when translation itself
    fails.
    """
    if target_language not in SUPPORTED_TRANSLATION_LANGUAGES:
        raise UnsupportedTranslationLanguageError(target_language)

    texts = _collect_translatable_texts(deck)
    translations = await translate_slide_deck_wording(
        run_id=run_id,
        texts=texts,
        source_language=deck.accessibility.language[:2],
        target_language=target_language,
    )
    try:
        translated_deck = _build_deck(deck, translations or {}, target_language, source_snapshot_id)
    except ValidationError:
        return _build_deck(deck, {}, target_language, source_snapshot_id)
    if _passes_content_gates(translated_deck):
        return translated_deck
    # ponytail: all-or-nothing fallback (mirrors content_materialization.py) —
    # translated text broke a downstream gate (e.g. density bounds); keep the
    # new deck_id/IDs/lineage but discard the translation itself rather than
    # trying to salvage individual fields.
    return _build_deck(deck, {}, target_language, source_snapshot_id)


def _passes_content_gates(deck: SlideDeckData) -> bool:
    reports = [
        *validate_registry_membership(deck),
        *audit_density_and_accessibility(deck, {}, deck.accessibility.reading_level),
        validate_teacher_only_separation(deck),
    ]
    return all(report.passed for report in reports)


def _collect_translatable_texts(deck: SlideDeckData) -> dict[str, str]:
    """Extract every reader/teacher-facing string the deck exposes, keyed stably.

    Keys are content-addressed off the *source* deck's own IDs so they stay
    stable across a call regardless of translation outcome. `SlideDeckSourceRef`
    citations and `SlideDeckRelatedArtifactRef` labels are deliberately excluded
    — see the module docstring.
    """
    texts: dict[str, str] = {"deck.title": deck.title}
    for slide in deck.slides:
        texts[f"slide.{slide.slide_id}.title"] = slide.title
        for block in slide.blocks:
            texts[f"block.{block.block_id}.body"] = block.body
        for interaction in slide.interactions:
            key_prefix = f"interaction.{interaction.interaction_id}"
            texts[f"{key_prefix}.prompt"] = interaction.prompt
            texts[f"{key_prefix}.no_js_fallback"] = interaction.no_js_fallback
            texts[f"{key_prefix}.accessibility_label"] = interaction.accessibility_label
            for option in interaction.options:
                texts[f"{key_prefix}.option.{option.option_id}"] = option.label
            if interaction.teacher_only is not None:
                texts[f"{key_prefix}.teacher_only.rationale"] = interaction.teacher_only.rationale
                for index, answer in enumerate(interaction.teacher_only.acceptable_answers):
                    texts[f"{key_prefix}.teacher_only.acceptable_answer.{index}"] = answer
        if slide.teacher_notes is not None:
            notes_prefix = f"slide.{slide.slide_id}.teacher_notes"
            for index, note in enumerate(slide.teacher_notes.facilitation_notes):
                texts[f"{notes_prefix}.facilitation.{index}"] = note
            for index, note in enumerate(slide.teacher_notes.answer_key_notes):
                texts[f"{notes_prefix}.answer_key.{index}"] = note
    return texts


def _translated(translations: dict[str, str], key: str, original: str) -> str:
    value = translations.get(key)
    return value if value else original


def _build_deck(
    deck: SlideDeckData,
    translations: dict[str, str],
    target_language: SlideDeckTranslationLanguage,
    source_snapshot_id: str,
) -> SlideDeckData:
    payload = deck.model_dump(mode="json")
    payload["deck_id"] = f"{deck.deck_id}-{target_language}"
    payload["title"] = _translated(translations, "deck.title", deck.title)
    payload["locale"] = target_language
    payload["accessibility"] = {**payload["accessibility"], "language": target_language}
    payload["lineage"] = {"remix_of_snapshot_id": source_snapshot_id}

    for slide_payload, slide in zip(payload["slides"], deck.slides, strict=True):
        slide_payload["slide_id"] = f"{slide.slide_id}-{target_language}"
        slide_payload["title"] = _translated(translations, f"slide.{slide.slide_id}.title", slide.title)
        for block_payload, block in zip(slide_payload["blocks"], slide.blocks, strict=True):
            block_payload["block_id"] = f"{block.block_id}-{target_language}"
            block_payload["body"] = _translated(translations, f"block.{block.block_id}.body", block.body)
        for interaction_payload, interaction in zip(slide_payload["interactions"], slide.interactions, strict=True):
            key_prefix = f"interaction.{interaction.interaction_id}"
            interaction_payload["interaction_id"] = f"{interaction.interaction_id}-{target_language}"
            interaction_payload["prompt"] = _translated(translations, f"{key_prefix}.prompt", interaction.prompt)
            interaction_payload["no_js_fallback"] = _translated(
                translations, f"{key_prefix}.no_js_fallback", interaction.no_js_fallback,
            )
            interaction_payload["accessibility_label"] = _translated(
                translations, f"{key_prefix}.accessibility_label", interaction.accessibility_label,
            )
            for option_payload, option in zip(interaction_payload["options"], interaction.options, strict=True):
                option_payload["label"] = _translated(translations, f"{key_prefix}.option.{option.option_id}", option.label)
            if interaction.teacher_only is not None:
                teacher_only_payload = interaction_payload["teacher_only"]
                teacher_only_payload["rationale"] = _translated(
                    translations, f"{key_prefix}.teacher_only.rationale", interaction.teacher_only.rationale,
                )
                for index, answer in enumerate(interaction.teacher_only.acceptable_answers):
                    teacher_only_payload["acceptable_answers"][index] = _translated(
                        translations, f"{key_prefix}.teacher_only.acceptable_answer.{index}", answer,
                    )
        if slide.teacher_notes is not None:
            notes_payload = slide_payload["teacher_notes"]
            notes_prefix = f"slide.{slide.slide_id}.teacher_notes"
            for index, note in enumerate(slide.teacher_notes.facilitation_notes):
                notes_payload["facilitation_notes"][index] = _translated(translations, f"{notes_prefix}.facilitation.{index}", note)
            for index, note in enumerate(slide.teacher_notes.answer_key_notes):
                notes_payload["answer_key_notes"][index] = _translated(translations, f"{notes_prefix}.answer_key.{index}", note)

    return SlideDeckData.model_validate(payload)

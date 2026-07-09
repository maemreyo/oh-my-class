from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from packages.agents.slide_deck_engine import (
    SUPPORTED_TRANSLATION_LANGUAGES,
    SlideDeckEngine,
    SlideDeckEngineRequest,
    UnsupportedTranslationLanguageError,
    translate_slide_deck,
)
from packages.agents.slide_deck_engine.phases.density_accessibility_audit import audit_density_and_accessibility
from packages.agents.slide_deck_engine.quality import validate_registry_membership, validate_teacher_only_separation

if TYPE_CHECKING:
    from common.contracts.slide_deck import SlideDeckData

# SDX-01: deck-wide EN<->VI translation. `_stub_slide_deck_wording_llm` (autouse,
# conftest.py in this package) already stubs `llm.complete_json_chat` to return
# `{}`, which `translate_slide_deck_wording`'s schema tolerates as "no
# translations" -- so the default fixture deck below exercises the
# no-LLM-response fallback path unless a test overrides the stub itself.


def _request() -> SlideDeckEngineRequest:
    return SlideDeckEngineRequest(
        run_id="run-translation",
        lesson_blueprint={
            "topic": "Equivalent fractions",
            "grade_level": "Grade 5",
            "learning_objectives": [
                {"description": "Explain why two fractions are equivalent."},
            ],
        },
        research_brief={
            "sources": [
                {"id": "src-fractions", "title": "Grade 5 Fractions Standard", "citation": "CCSS 5.NF.A"},
            ],
        },
        dependency_artifacts=[],
        teacher_constraints={"locale": "en-US", "theme": "default"},
        revision_feedback="",
    )


async def _source_deck() -> SlideDeckData:
    result = await SlideDeckEngine().generate(_request())
    return result.deck


async def test_translate_slide_deck_produces_new_independent_deck_with_lineage() -> None:
    source = await _source_deck()

    translated = await translate_slide_deck(
        source, run_id="run-translation", target_language="vi", source_snapshot_id="snapshot-source-1",
    )

    assert translated.deck_id != source.deck_id
    assert translated.lineage is not None
    assert translated.lineage.remix_of_snapshot_id == "snapshot-source-1"
    assert source.lineage is None


async def test_translate_slide_deck_never_mutates_source_deck() -> None:
    source = await _source_deck()
    before = source.model_dump(mode="json")

    await translate_slide_deck(source, run_id="run-translation", target_language="vi", source_snapshot_id="snap-1")

    assert source.model_dump(mode="json") == before


async def test_translate_slide_deck_preserves_layout_block_structure_and_media_exactly() -> None:
    source = await _source_deck()

    translated = await translate_slide_deck(source, run_id="run-translation", target_language="vi", source_snapshot_id="snap-1")

    assert len(translated.slides) == len(source.slides)
    for translated_slide, source_slide in zip(translated.slides, source.slides, strict=True):
        assert translated_slide.layout == source_slide.layout
        assert len(translated_slide.blocks) == len(source_slide.blocks)
        for translated_block, source_block in zip(translated_slide.blocks, source_slide.blocks, strict=True):
            assert translated_block.block_type == source_block.block_type
            assert translated_block.media == source_block.media
        assert len(translated_slide.interactions) == len(source_slide.interactions)


async def test_translate_slide_deck_generates_fresh_ids_disjoint_from_source() -> None:
    source = await _source_deck()

    translated = await translate_slide_deck(source, run_id="run-translation", target_language="vi", source_snapshot_id="snap-1")

    source_slide_ids = {slide.slide_id for slide in source.slides}
    translated_slide_ids = {slide.slide_id for slide in translated.slides}
    assert source_slide_ids.isdisjoint(translated_slide_ids)
    # SlideDeckData's own deck-wide uniqueness validators (SDTF-01) already ran
    # inside translate_slide_deck's SlideDeckData.model_validate() -- a
    # successfully constructed `translated` IS the uniqueness proof.


async def test_translate_slide_deck_passes_registry_density_and_teacher_only_gates() -> None:
    source = await _source_deck()

    translated = await translate_slide_deck(source, run_id="run-translation", target_language="vi", source_snapshot_id="snap-1")

    assert all(report.passed for report in validate_registry_membership(translated))
    density_reports = audit_density_and_accessibility(translated, {}, translated.accessibility.reading_level)
    assert all(report.passed for report in density_reports)
    assert validate_teacher_only_separation(translated).passed


async def test_translate_slide_deck_does_not_leak_teacher_only_content_beyond_source() -> None:
    source = await _source_deck()

    translated = await translate_slide_deck(source, run_id="run-translation", target_language="vi", source_snapshot_id="snap-1")

    for translated_slide, source_slide in zip(translated.slides, source.slides, strict=True):
        assert (translated_slide.teacher_notes is None) == (source_slide.teacher_notes is None)
        for translated_interaction, source_interaction in zip(translated_slide.interactions, source_slide.interactions, strict=True):
            assert (translated_interaction.teacher_only is None) == (source_interaction.teacher_only is None)


async def test_translate_slide_deck_rejects_unsupported_target_language() -> None:
    source = await _source_deck()

    with pytest.raises(UnsupportedTranslationLanguageError):
        await translate_slide_deck(source, run_id="run-translation", target_language="fr", source_snapshot_id="snap-1")  # type: ignore[arg-type]


def test_supported_translation_languages_is_exactly_en_and_vi() -> None:
    assert set(SUPPORTED_TRANSLATION_LANGUAGES) == {"en", "vi"}


async def test_translate_slide_deck_en_to_vi_and_vi_to_en_both_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.agents import llm

    async def fake_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        request_payload = json.loads(messages[-1]["content"])
        return json.dumps({"translations": {key: f"TRANSLATED::{value}" for key, value in request_payload.items()}})

    monkeypatch.setattr(llm, "complete_json_chat", fake_complete_json_chat)
    source = await _source_deck()

    to_vi = await translate_slide_deck(source, run_id="run-translation", target_language="vi", source_snapshot_id="snap-1")
    assert to_vi.locale == "vi"
    assert to_vi.accessibility.language == "vi"
    assert any(block.body.startswith("TRANSLATED::") for slide in to_vi.slides for block in slide.blocks)

    to_en = await translate_slide_deck(to_vi, run_id="run-translation", target_language="en", source_snapshot_id="snap-vi-1")
    assert to_en.locale == "en"
    assert any(block.body.startswith("TRANSLATED::") for slide in to_en.slides for block in slide.blocks)


async def test_translate_slide_deck_falls_back_to_original_text_on_llm_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.agents import llm

    async def raising_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr(llm, "complete_json_chat", raising_complete_json_chat)
    source = await _source_deck()

    translated = await translate_slide_deck(source, run_id="run-translation", target_language="vi", source_snapshot_id="snap-1")

    source_bodies = [block.body for slide in source.slides for block in slide.blocks]
    translated_bodies = [block.body for slide in translated.slides for block in slide.blocks]
    assert translated_bodies == source_bodies


async def test_translate_slide_deck_falls_back_to_original_text_on_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.agents import llm

    async def malformed_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        return "not json at all"

    monkeypatch.setattr(llm, "complete_json_chat", malformed_complete_json_chat)
    source = await _source_deck()

    translated = await translate_slide_deck(source, run_id="run-translation", target_language="vi", source_snapshot_id="snap-1")

    source_bodies = [block.body for slide in source.slides for block in slide.blocks]
    translated_bodies = [block.body for slide in translated.slides for block in slide.blocks]
    assert translated_bodies == source_bodies


async def test_translate_slide_deck_falls_back_when_translation_breaks_field_length(monkeypatch: pytest.MonkeyPatch) -> None:
    """An oversized translated value fails `SlideDeckBlock.body`'s max_length --
    the whole translation pass is discarded (same all-or-nothing precedent as
    `content_materialization.py`), never partially-applied invalid content."""
    from packages.agents import llm

    async def oversized_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        request_payload = json.loads(messages[-1]["content"])
        translations = {key: "x" * 5000 for key in request_payload}
        return json.dumps({"translations": translations})

    monkeypatch.setattr(llm, "complete_json_chat", oversized_complete_json_chat)
    source = await _source_deck()

    translated = await translate_slide_deck(source, run_id="run-translation", target_language="vi", source_snapshot_id="snap-1")

    source_bodies = [block.body for slide in source.slides for block in slide.blocks]
    translated_bodies = [block.body for slide in translated.slides for block in slide.blocks]
    assert translated_bodies == source_bodies

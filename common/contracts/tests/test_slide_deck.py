from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.artifact import ArtifactContent
from common.contracts.run_contract import ContractRevisionMeta, JsonObject, RunContract
from common.contracts.slide_deck import SlideDeckData


def _revision() -> ContractRevisionMeta:
    return ContractRevisionMeta(
        revision=1,
        actor="system",
        source="request",
        reason="slide deck contract test",
        effective_stage="setup_contract",
    )


def _valid_deck() -> JsonObject:
    return {
        "deck_id": "deck-fractions-intro",
        "title": "Equivalent Fractions Mini Deck",
        "locale": "en-US",
        "theme": "default",
        "surfaces": {
            "student": {"mode": "presentation", "export_format": "html"},
            "teacher": {"mode": "teacher_guide", "export_format": "html"},
            "print": {"mode": "print", "export_format": "html"},
        },
        "source_refs": [
            {
                "source_id": "src-fractions-standard",
                "title": "Grade 5 Fractions Standard",
                "citation": "CCSS 5.NF.A",
                "confidence": "verified",
            }
        ],
        "slides": [
            {
                "slide_id": "slide-title",
                "title": "Equivalent Fractions",
                "layout": "title",
                "progression": {"step_index": 1, "reveal_policy": "all_at_once"},
                "blocks": [
                    {
                        "block_id": "block-title",
                        "block_type": "heading",
                        "body": "Equivalent Fractions",
                        "source_ref_ids": ["src-fractions-standard"],
                    },
                    {
                        "block_id": "block-image",
                        "block_type": "image",
                        "body": "Two fraction bars split into equal parts.",
                        "media": {
                            "media_id": "media-bars",
                            "media_type": "image",
                            "source": "packaged/fraction-bars.svg",
                            "tier": "packaged",
                            "alt_text": "Two fraction bars showing one half equals two fourths.",
                        },
                    },
                ],
                "teacher_notes": {
                    "facilitation_notes": ["Ask learners why both bars cover the same area."],
                    "answer_key_notes": [],
                },
            },
            {
                "slide_id": "slide-check",
                "title": "Quick Check",
                "layout": "question",
                "progression": {"step_index": 2, "reveal_policy": "progressive"},
                "blocks": [
                    {
                        "block_id": "block-question",
                        "block_type": "interaction_prompt",
                        "body": "Which fraction equals 1/2?",
                    }
                ],
                "interactions": [
                    {
                        "interaction_id": "interaction-equivalent",
                        "interaction_type": "multiple_choice_single",
                        "prompt": "Which fraction equals 1/2?",
                        "answer_bearing": True,
                        "options": [
                            {"option_id": "a", "label": "1/3"},
                            {"option_id": "b", "label": "2/4"},
                            {"option_id": "c", "label": "3/5"},
                        ],
                        "teacher_only": {
                            "separation": "teacher_only_projection",
                            "correct_option_ids": ["b"],
                            "rationale": "2/4 simplifies to 1/2.",
                        },
                    }
                ],
                "teacher_notes": {
                    "facilitation_notes": ["Do not show the rationale until discussion."],
                    "answer_key_notes": ["Correct answer: b"],
                },
            },
        ],
        "accessibility": {
            "reading_level": "Grade 5",
            "language": "en",
            "alt_text_required": True,
            "keyboard_navigation": True,
        },
        "media_policy": {
            "default_tier": "packaged",
            "online_optional_allowed": True,
            "fallback_required": True,
        },
    }


def test_run_contract_accepts_slide_deck_artifact_type() -> None:
    contract = RunContract(
        contract_id="contract-slide",
        run_id="run-slide",
        teacher_id="teacher-1",
        topic="Equivalent fractions",
        grade_band="Grade 5",
        subject="math",
        locale="en-US",
        instruction_language="en",
        citation_locale="en-US",
        artifact_types=["slide_deck"],
        export_formats=["html"],
        config_version="test",
        config_hash="a" * 64,
        revision_meta=_revision(),
    )

    assert contract.artifact_types == ["slide_deck"]


def test_artifact_content_accepts_slide_deck_type() -> None:
    artifact = ArtifactContent(
        artifact_type="slide_deck",
        title="Equivalent Fractions Mini Deck",
        sections=[{"deck_ref": "deck-fractions-intro"}],
    )

    assert artifact.artifact_type == "slide_deck"


def test_slide_deck_validates_representative_deck() -> None:
    deck = SlideDeckData.model_validate(_valid_deck())

    assert deck.deck_id == "deck-fractions-intro"
    assert deck.slides[1].interactions[0].teacher_only is not None
    assert deck.accessibility.alt_text_required is True


def test_slide_deck_rejects_no_slides() -> None:
    payload = {**_valid_deck(), "slides": []}

    with pytest.raises(ValidationError):
        SlideDeckData.model_validate(payload)


def test_slide_deck_rejects_duplicate_slide_ids() -> None:
    payload = _valid_deck()
    payload["slides"][1]["slide_id"] = "slide-title"

    with pytest.raises(ValidationError, match="duplicate slide_id"):
        SlideDeckData.model_validate(payload)


def test_slide_deck_rejects_duplicate_block_ids_within_slide() -> None:
    payload = _valid_deck()
    payload["slides"][0]["blocks"][1]["block_id"] = "block-title"

    with pytest.raises(ValidationError, match="duplicate block_id"):
        SlideDeckData.model_validate(payload)


def test_slide_deck_rejects_duplicate_block_ids_across_slides() -> None:
    # ADR-045: block IDs are future teaching-session join points, so they must
    # be unique deck-wide even when the collision spans two different slides.
    payload = _valid_deck()
    payload["slides"][1]["blocks"][0]["block_id"] = "block-title"

    with pytest.raises(ValidationError, match="duplicate block_id across slide deck"):
        SlideDeckData.model_validate(payload)


def test_slide_deck_rejects_duplicate_interaction_ids_across_slides() -> None:
    payload = _valid_deck()
    payload["slides"][0]["interactions"] = [dict(payload["slides"][1]["interactions"][0])]

    with pytest.raises(ValidationError, match="duplicate interaction_id across slide deck"):
        SlideDeckData.model_validate(payload)


def test_slide_deck_rejects_unsupported_layout_block_and_interaction_types() -> None:
    invalid_layout = _valid_deck()
    invalid_layout["slides"][0]["layout"] = "open_slide_runtime"

    invalid_block = _valid_deck()
    invalid_block["slides"][0]["blocks"][0]["block_type"] = "raw_html"

    invalid_interaction = _valid_deck()
    invalid_interaction["slides"][1]["interactions"][0]["interaction_type"] = "custom_js"

    for payload in (invalid_layout, invalid_block, invalid_interaction):
        with pytest.raises(ValidationError):
            SlideDeckData.model_validate(payload)


def test_slide_deck_rejects_media_without_alt_text() -> None:
    payload = _valid_deck()
    del payload["slides"][0]["blocks"][1]["media"]["alt_text"]

    with pytest.raises(ValidationError):
        SlideDeckData.model_validate(payload)


def test_slide_deck_rejects_answer_bearing_interaction_without_teacher_projection() -> None:
    payload = _valid_deck()
    del payload["slides"][1]["interactions"][0]["teacher_only"]

    with pytest.raises(ValidationError, match="teacher_only_projection"):
        SlideDeckData.model_validate(payload)


def test_slide_deck_accepts_registered_v1_interactions() -> None:
    payload = _valid_deck()
    payload["slides"][1]["interactions"] = [
        {
            "interaction_id": interaction_type,
            "interaction_type": interaction_type,
            "prompt": f"Prompt for {interaction_type}",
            "no_js_fallback": "Use this interaction without storing student responses.",
            "accessibility_label": f"{interaction_type} interaction",
        }
        for interaction_type in ("reveal", "poll_prompt", "timer", "discussion_prompt", "exit_ticket", "think_pair_share")
    ]

    deck = SlideDeckData.model_validate(payload)

    assert {interaction.interaction_type for interaction in deck.slides[1].interactions} == {
        "reveal", "poll_prompt", "timer", "discussion_prompt", "exit_ticket", "think_pair_share",
    }


def test_slide_deck_accepts_short_answer_interaction_with_teacher_only_acceptable_answers() -> None:
    # ADR-045: short-answer is one of the four required response intents
    # (quick check, discussion prompt, exit ticket, short answer). It is
    # answer-bearing, so it must carry teacher-only acceptable answers rather
    # than option-based correctness.
    payload = _valid_deck()
    payload["slides"][1]["interactions"] = [
        {
            "interaction_id": "interaction-short-answer",
            "interaction_type": "short_answer",
            "prompt": "Write one fraction that is equivalent to 1/2.",
            "answer_bearing": True,
            "no_js_fallback": "Students write their answer on paper; no response is stored.",
            "accessibility_label": "Short answer prompt",
            "teacher_only": {
                "separation": "teacher_only_projection",
                "acceptable_answers": ["2/4", "3/6", "4/8"],
                "rationale": "Any fraction that simplifies to 1/2 is acceptable.",
            },
        },
    ]

    deck = SlideDeckData.model_validate(payload)

    interaction = deck.slides[1].interactions[0]
    assert interaction.interaction_type == "short_answer"
    assert interaction.answer_bearing is True
    assert interaction.teacher_only is not None
    assert interaction.teacher_only.acceptable_answers == ["2/4", "3/6", "4/8"]


def test_slide_deck_rejects_packaged_media_with_external_url() -> None:
    payload = _valid_deck()
    payload["slides"][0]["blocks"][1]["media"]["source"] = "https://example.com/fraction-bars.svg"

    with pytest.raises(ValidationError, match="packaged media"):
        SlideDeckData.model_validate(payload)


def test_slide_deck_online_optional_media_requires_network_and_fallback() -> None:
    missing_network = _valid_deck()
    missing_network["slides"][0]["blocks"][1]["media"] = {
        "media_id": "online-video",
        "media_type": "video",
        "source": "https://example.com/video",
        "tier": "online_optional",
        "alt_text": "Video explanation of equivalent fractions.",
        "fallback_text": "Use fraction bars instead.",
    }

    with pytest.raises(ValidationError, match="requires_network"):
        SlideDeckData.model_validate(missing_network)

    valid_online = _valid_deck()
    valid_online["slides"][0]["blocks"][1]["media"] = {
        "media_id": "online-video",
        "media_type": "video",
        "source": "https://example.com/video",
        "tier": "online_optional",
        "alt_text": "Video explanation of equivalent fractions.",
        "fallback_text": "Use fraction bars instead.",
        "requires_network": True,
    }

    deck = SlideDeckData.model_validate(valid_online)

    assert deck.slides[0].blocks[1].media is not None
    assert deck.slides[0].blocks[1].media.requires_network is True

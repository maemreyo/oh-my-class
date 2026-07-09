from __future__ import annotations

from typing import Final

from pydantic import ValidationError

from common.contracts.slide_deck import SlideDeckData

from packages.agents.slide_deck_engine.models import AssembledSlideDeckInput, PedagogicalPlan
from packages.agents.slide_deck_engine.phases.content_materialization_llm import (
    SlideDeckWordingResponse,
    generate_slide_deck_wording,
)

_TITLE_SUFFIX = " Slide Deck"
_TITLE_MAX_LENGTH = 200
_FOOD_VOCABULARY_MARKERS: Final = ("food vocabulary", "food", "eat", "drink")


async def materialize_deck(
    assembled: AssembledSlideDeckInput,
    plan: PedagogicalPlan,
) -> tuple[SlideDeckData, int]:
    """Build the deck, authoring wording/examples/activity text via a real LLM call.

    Returns ``(deck, llm_calls)`` — ``llm_calls`` is 1 only when the LLM produced a
    schema-valid response that was actually used; 0 whenever the call failed
    (timeout, invalid schema) or its output couldn't be assembled into a valid
    deck, in which case the deck falls back to the engine's existing deterministic
    per-topic wording (real curated content, not a placeholder).
    """
    topic = assembled.topic
    wording = await generate_slide_deck_wording(
        run_id=assembled.run_id,
        topic=topic,
        grade_level=assembled.grade_level,
        locale=assembled.locale,
        learning_goal=plan.learning_goal,
    )
    try:
        deck_payload = _deck_payload(assembled, plan, topic, wording)
        return SlideDeckData.model_validate(deck_payload), (1 if wording is not None else 0)
    except ValidationError:
        # ponytail: all-or-nothing fallback — one invalid/oversized LLM field discards
        # the whole response rather than salvaging the other fields; upgrade to
        # per-field validation if this proves too lossy in practice.
        return SlideDeckData.model_validate(_deck_payload(assembled, plan, topic, None)), 0


def _deck_payload(
    assembled: AssembledSlideDeckInput,
    plan: PedagogicalPlan,
    topic: str,
    wording: SlideDeckWordingResponse | None,
) -> dict[str, object]:
    source_id = str(assembled.source.get("id", "src-generated"))
    source_title = str(assembled.source.get("title", "Teacher supplied lesson context"))
    source_citation = str(assembled.source.get("citation", "Teacher supplied lesson context"))
    return {
        "deck_id": f"slide-deck-{assembled.run_id}",
        "title": _deck_title(topic),
        "locale": assembled.locale,
        "theme": assembled.theme,
        "surfaces": {
            "student": {"mode": "presentation", "export_format": "html"},
            "teacher": {"mode": "teacher_guide", "export_format": "html"},
            "print": {"mode": "print", "export_format": "html"},
        },
        "source_refs": [{
            "source_id": source_id,
            "title": source_title,
            "citation": source_citation,
            "confidence": "verified",
        }],
        "slides": [
            _title_slide(topic, source_id, plan, wording),
            _goal_slide(topic, source_id, plan),
            _vocabulary_slide(topic, source_id, wording),
            _example_slide(topic, source_id, wording),
            _practice_slide(topic, source_id, plan, wording),
            _exit_slide(topic, source_id, wording),
        ],
        "accessibility": {
            "reading_level": assembled.grade_level,
            "language": assembled.locale[:2],
            "alt_text_required": True,
            "keyboard_navigation": True,
        },
        "media_policy": {
            "default_tier": "packaged",
            "online_optional_allowed": True,
            "fallback_required": True,
        },
    }


def _wording_field(wording: SlideDeckWordingResponse | None, field_name: str, fallback: str) -> str:
    if wording is None:
        return fallback
    value = getattr(wording, field_name)
    return value if value else fallback


def _title_slide(
    topic: str,
    source_id: str,
    plan: PedagogicalPlan,
    wording: SlideDeckWordingResponse | None,
) -> dict[str, object]:
    alt_text = _wording_field(wording, "image_alt_text", f"Visual model for {topic}.")
    return {
        "slide_id": "slide-title",
        "title": topic,
        "layout": "title",
        "progression": {"step_index": 1, "reveal_policy": "all_at_once"},
        "blocks": [
            {"block_id": "block-title", "block_type": "heading", "body": topic, "source_ref_ids": [source_id]},
            {
                "block_id": "block-visual",
                "block_type": "image",
                "body": plan.learning_goal,
                "media": {
                    "media_id": "media-model",
                    "media_type": "image",
                    "source": "packaged/slide-deck-default-model.svg",
                    "tier": "packaged",
                    "alt_text": alt_text,
                    "fallback_text": f"Teacher sketches a visual model for {topic}.",
                },
            },
        ],
        "teacher_notes": {
            "facilitation_notes": ["Invite students to say what they already know about the topic."],
            "answer_key_notes": [],
        },
    }


def _goal_slide(topic: str, source_id: str, plan: PedagogicalPlan) -> dict[str, object]:
    return {
        "slide_id": "slide-goal",
        "title": "Learning Goal",
        "layout": "content",
        "progression": {"step_index": 2, "reveal_policy": "progressive"},
        "blocks": [
            {"block_id": "block-goal", "block_type": "callout", "body": plan.learning_goal, "source_ref_ids": [source_id]},
            {
                "block_id": "block-success",
                "block_type": "paragraph",
                "body": f"By the end, students can explain and use {topic} in a short classroom response.",
                "source_ref_ids": [source_id],
            },
        ],
        "teacher_notes": {"facilitation_notes": ["Read the goal aloud, then ask students to paraphrase it."], "answer_key_notes": []},
    }


def _vocabulary_slide(
    topic: str,
    source_id: str,
    wording: SlideDeckWordingResponse | None,
) -> dict[str, object]:
    vocabulary_body = _wording_field(wording, "vocabulary_body", _vocabulary_body(topic))
    practice_body = _wording_field(wording, "vocabulary_practice_body", _vocabulary_practice_body(topic))
    return {
        "slide_id": "slide-vocabulary",
        "title": "Key Vocabulary",
        "layout": "content",
        "progression": {"step_index": 3, "reveal_policy": "progressive"},
        "blocks": [
            {
                "block_id": "block-vocab-1",
                "block_type": "paragraph",
                "body": vocabulary_body,
                "source_ref_ids": [source_id],
            },
            {
                "block_id": "block-vocab-2",
                "block_type": "callout",
                "body": practice_body,
                "source_ref_ids": [source_id],
            },
        ],
        "teacher_notes": {"facilitation_notes": ["Model pronunciation and ask students for one example each."], "answer_key_notes": []},
    }


def _example_slide(
    topic: str,
    source_id: str,
    wording: SlideDeckWordingResponse | None,
) -> dict[str, object]:
    example_body = _wording_field(wording, "example_body", _example_body(topic))
    sentence_stem = _wording_field(wording, "sentence_stem", _sentence_stem(topic))
    return {
        "slide_id": "slide-example",
        "title": "Worked Example",
        "layout": "activity",
        "progression": {"step_index": 4, "reveal_policy": "teacher_controlled"},
        "blocks": [
            {
                "block_id": "block-example",
                "block_type": "paragraph",
                "body": example_body,
                "source_ref_ids": [source_id],
            },
            {
                "block_id": "block-stem",
                "block_type": "callout",
                "body": sentence_stem,
                "source_ref_ids": [source_id],
            },
        ],
        "teacher_notes": {"facilitation_notes": ["Think aloud while filling the stem so students hear the reasoning."], "answer_key_notes": []},
    }


def _practice_slide(
    topic: str,
    source_id: str,
    plan: PedagogicalPlan,
    wording: SlideDeckWordingResponse | None,
) -> dict[str, object]:
    check_prompt = _wording_field(wording, "check_prompt", _check_prompt(topic, plan))
    option_labels = _practice_option_labels(topic)
    distractor_a = _wording_field(wording, "practice_distractor_a", option_labels[0])
    correct_option = _wording_field(wording, "practice_correct_option", option_labels[1])
    distractor_b = _wording_field(wording, "practice_distractor_b", option_labels[2])
    rationale = _wording_field(wording, "teacher_rationale", _teacher_rationale(topic))
    return {
        "slide_id": "slide-practice",
        "title": "Guided Practice",
        "layout": "question",
        "progression": {"step_index": 5, "reveal_policy": "progressive"},
        "blocks": [{"block_id": "block-question", "block_type": "interaction_prompt", "body": check_prompt, "source_ref_ids": [source_id]}],
        "interactions": [{
            "interaction_id": "interaction-check",
            "interaction_type": "quick_check",
            "prompt": check_prompt,
            "answer_bearing": True,
            "no_js_fallback": "Students answer on paper or by hand signal; no response is stored.",
            "accessibility_label": "Quick check question",
            "options": [
                {"option_id": "a", "label": distractor_a},
                {"option_id": "b", "label": correct_option},
                {"option_id": "c", "label": distractor_b},
            ],
            "teacher_only": {
                "separation": "teacher_only_projection",
                "correct_option_ids": ["b"],
                "rationale": rationale,
            },
        }],
        "teacher_notes": {"facilitation_notes": ["Ask students to justify the option before revealing the answer."], "answer_key_notes": ["Correct answer: b"]},
    }


def _exit_slide(
    topic: str,
    source_id: str,
    wording: SlideDeckWordingResponse | None,
) -> dict[str, object]:
    exit_prompt = _wording_field(wording, "exit_prompt", _exit_prompt(topic))
    return {
        "slide_id": "slide-exit",
        "title": "Exit Ticket",
        "layout": "summary",
        "progression": {"step_index": 6, "reveal_policy": "all_at_once"},
        "blocks": [
            {
                "block_id": "block-exit",
                "block_type": "interaction_prompt",
                "body": exit_prompt,
                "source_ref_ids": [source_id],
            },
            {
                "block_id": "block-next",
                "block_type": "paragraph",
                "body": "Teacher collects responses to decide whether to review, practice, or extend next lesson.",
                "source_ref_ids": [source_id],
            },
        ],
        "teacher_notes": {"facilitation_notes": ["Use responses as formative evidence for the next lesson."], "answer_key_notes": []},
    }


def _deck_title(topic: str) -> str:
    prefix_limit = _TITLE_MAX_LENGTH - len(_TITLE_SUFFIX)
    return f"{topic[:prefix_limit].rstrip()}{_TITLE_SUFFIX}"


def _is_food_vocabulary_topic(topic: str) -> bool:
    normalized = topic.lower()
    return any(marker in normalized for marker in _FOOD_VOCABULARY_MARKERS)


def _vocabulary_body(topic: str) -> str:
    if _is_food_vocabulary_topic(topic):
        return "Core words: apple, rice, water, chicken, bread, milk. Students point, repeat, and sort each word as food or drink."
    return f"Core examples for {topic}: name three important terms, show each with a simple visual, then ask students to use one aloud."


def _vocabulary_practice_body(topic: str) -> str:
    if _is_food_vocabulary_topic(topic):
        return "Teacher says: I would like rice. Students echo, then swap in apple, water, bread, milk, or chicken."
    return "Students repeat, gesture, and connect each term to a familiar classroom example."


def _example_body(topic: str) -> str:
    if _is_food_vocabulary_topic(topic):
        return "Teacher models a short exchange: What would you like to eat or drink? I would like rice and water, please."
    return f"Teacher models one complete response using {topic}, then highlights the useful words."


def _sentence_stem(topic: str) -> str:
    if _is_food_vocabulary_topic(topic):
        return "Sentence stems: I would like ___. I eat ___. I drink ___."
    return "Sentence stem: I can see ___, and I can say ___."


def _check_prompt(topic: str, plan: PedagogicalPlan) -> str:
    if _is_food_vocabulary_topic(topic):
        return "What would you like to eat or drink? Choose the best classroom answer."
    return plan.check_prompt


def _practice_option_labels(topic: str) -> tuple[str, str, str]:
    if _is_food_vocabulary_topic(topic):
        return ("I am blue.", "I would like rice and water, please.", "The pencil is under the desk.")
    return ("A partial match", f"A clear example of {topic}", "An unrelated example")


def _teacher_rationale(topic: str) -> str:
    if _is_food_vocabulary_topic(topic):
        return "The best option answers the food-and-drink question with the target sentence frame."
    return "The best option directly represents the lesson goal."


def _exit_prompt(topic: str) -> str:
    if _is_food_vocabulary_topic(topic):
        return "Exit ticket: say or write one food sentence and one drink sentence using I would like ___."
    return f"Write or say one sentence that correctly uses {topic}."

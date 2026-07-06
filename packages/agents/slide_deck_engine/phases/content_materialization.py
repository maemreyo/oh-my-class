from __future__ import annotations

from common.contracts.slide_deck import SlideDeckData

from packages.agents.slide_deck_engine.models import AssembledSlideDeckInput, PedagogicalPlan


def materialize_deck(assembled: AssembledSlideDeckInput, plan: PedagogicalPlan) -> SlideDeckData:
    source_id = str(assembled.source.get("id", "src-generated"))
    source_title = str(assembled.source.get("title", "Teacher supplied lesson context"))
    source_citation = str(assembled.source.get("citation", "Teacher supplied lesson context"))
    return SlideDeckData.model_validate({
        "deck_id": f"slide-deck-{assembled.run_id}",
        "title": f"{assembled.topic} Slide Deck",
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
            {
                "slide_id": "slide-title",
                "title": assembled.topic,
                "layout": "title",
                "progression": {"step_index": 1, "reveal_policy": "all_at_once"},
                "blocks": [
                    {
                        "block_id": "block-title",
                        "block_type": "heading",
                        "body": assembled.topic,
                        "source_ref_ids": [source_id],
                    },
                    {
                        "block_id": "block-visual",
                        "block_type": "image",
                        "body": plan.learning_goal,
                        "media": {
                            "media_id": "media-model",
                            "media_type": "image",
                            "source": "packaged/slide-deck-default-model.svg",
                            "tier": "packaged",
                            "alt_text": f"Visual model for {assembled.topic}.",
                            "fallback_text": f"Teacher sketches a visual model for {assembled.topic}.",
                        },
                    },
                ],
                "teacher_notes": {
                    "facilitation_notes": ["Invite students to describe what the visual model shows."],
                    "answer_key_notes": [],
                },
            },
            {
                "slide_id": "slide-check",
                "title": "Quick Check",
                "layout": "question",
                "progression": {"step_index": 2, "reveal_policy": "progressive"},
                "blocks": [{
                    "block_id": "block-question",
                    "block_type": "interaction_prompt",
                    "body": plan.check_prompt,
                    "source_ref_ids": [source_id],
                }],
                "interactions": [{
                    "interaction_id": "interaction-check",
                    "interaction_type": "quick_check",
                    "prompt": plan.check_prompt,
                    "answer_bearing": True,
                    "no_js_fallback": "Students answer on paper or by hand signal; no response is stored.",
                    "accessibility_label": "Quick check question",
                    "options": [
                        {"option_id": "a", "label": "A partial match"},
                        {"option_id": "b", "label": "The best visual model"},
                        {"option_id": "c", "label": "An unrelated example"},
                    ],
                    "teacher_only": {
                        "separation": "teacher_only_projection",
                        "correct_option_ids": ["b"],
                        "rationale": "The best visual model directly represents the lesson goal.",
                    },
                }],
                "teacher_notes": {
                    "facilitation_notes": ["Ask students to justify the option before revealing the answer."],
                    "answer_key_notes": ["Correct answer: b"],
                },
            },
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
    })

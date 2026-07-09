from __future__ import annotations

from typing import Final

from packages.agents.slide_deck_engine.models import AssembledSlideDeckInput, PedagogicalPlan

# SDX-03: per-preset pedagogical framing. Keyed by AssembledSlideDeckInput's
# `pedagogical_emphasis` (resolved from structure_preset). The "" default
# below reproduces the exact pre-SDX-03 wording for the no-preset path.
_GOAL_TEMPLATES: Final[dict[str, str]] = {
    "explore_before_explain": "Explore examples of {topic} first, then explain the pattern with a visual model.",
    "model_then_practice": "Watch a modeled example of {topic}, then practice it right away.",
    "prior_exposure_recap": "Recap what you already noticed about {topic} before class, then build on it.",
}
_CHECK_PROMPT_TEMPLATES: Final[dict[str, str]] = {
    "explore_before_explain": "Which example did you discover shows {topic_lower}?",
    "model_then_practice": "Which example matches the model we just practiced for {topic_lower}?",
    "prior_exposure_recap": "Which example builds on what you already knew about {topic_lower}?",
}


def plan_pedagogy(assembled: AssembledSlideDeckInput) -> PedagogicalPlan:
    emphasis = assembled.pedagogical_emphasis
    goal_template = _GOAL_TEMPLATES.get(emphasis, "Explain {topic} with a visual model.")
    check_template = _CHECK_PROMPT_TEMPLATES.get(emphasis, "Which example shows {topic_lower}?")
    return PedagogicalPlan(
        learning_goal=goal_template.format(topic=assembled.topic),
        check_prompt=check_template.format(topic_lower=assembled.topic.lower()),
    )

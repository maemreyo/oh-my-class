from __future__ import annotations

from packages.agents.slide_deck_engine.models import AssembledSlideDeckInput, PedagogicalPlan


def plan_pedagogy(assembled: AssembledSlideDeckInput) -> PedagogicalPlan:
    return PedagogicalPlan(
        learning_goal=f"Explain {assembled.topic} with a visual model.",
        check_prompt=f"Which example shows {assembled.topic.lower()}?",
    )

from __future__ import annotations

from packages.agents.slide_deck_engine.models import AssembledSlideDeckInput, SlideArchitecturePlan


def plan_slide_architecture(assembled: AssembledSlideDeckInput) -> SlideArchitecturePlan:
    return SlideArchitecturePlan(
        slide_titles=[assembled.topic, "Quick Check"],
        layouts=["title", "question"],
    )

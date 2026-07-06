from __future__ import annotations

from packages.agents.slide_deck_engine.models import SlideArchitecturePlan
from packages.agents.slide_deck_engine.registries import LAYOUT_REGISTRY, RegistryEntry


def compose_layouts(plan: SlideArchitecturePlan) -> list[RegistryEntry]:
    return [LAYOUT_REGISTRY.get(layout) for layout in plan.layouts]

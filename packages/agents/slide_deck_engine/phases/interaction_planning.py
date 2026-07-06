from __future__ import annotations

from packages.agents.slide_deck_engine.registries import INTERACTION_REGISTRY, RegistryEntry


def plan_interactions() -> list[RegistryEntry]:
    return [
        INTERACTION_REGISTRY.get("reveal"),
        INTERACTION_REGISTRY.get("quick_check"),
        INTERACTION_REGISTRY.get("poll_prompt"),
        INTERACTION_REGISTRY.get("timer"),
        INTERACTION_REGISTRY.get("discussion_prompt"),
        INTERACTION_REGISTRY.get("exit_ticket"),
        INTERACTION_REGISTRY.get("think_pair_share"),
    ]

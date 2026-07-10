from __future__ import annotations
"""Feature flags for progressive feature rollout."""
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class FeatureFlags:
    topic_decomposition_v1: bool
    vocabulary_batch_v1: bool
    component_strategist_v1: bool
    # SDE-10: independent rollout gates -- AI rewrite is additionally gated
    # behind slide_deck_editor_v1 at call sites (can't AI-rewrite if the
    # editor itself is off), so disabling AI rewrite alone leaves manual
    # editing unaffected, but disabling the editor flag turns both off.
    slide_deck_editor_v1: bool
    slide_deck_ai_rewrite_v1: bool
    unit_fanout_concurrency: int  # 1 = sequential, >1 = parallel (Phase 2)

def get_feature_flags() -> FeatureFlags:
    """Read feature flags from environment."""
    return FeatureFlags(
        topic_decomposition_v1=os.getenv("FEATURE_TOPIC_DECOMPOSITION_V1", "false").lower() == "true",
        vocabulary_batch_v1=os.getenv("FEATURE_VOCABULARY_BATCH_V1", "false").lower() == "true",
        component_strategist_v1=os.getenv("FEATURE_COMPONENT_STRATEGIST_V1", "false").lower() == "true",
        slide_deck_editor_v1=os.getenv("FEATURE_SLIDE_DECK_EDITOR_V1", "false").lower() == "true",
        slide_deck_ai_rewrite_v1=os.getenv("FEATURE_SLIDE_DECK_AI_REWRITE_V1", "false").lower() == "true",
        unit_fanout_concurrency=int(os.getenv("UNIT_FANOUT_CONCURRENCY", "1")),
    )

_FEATURES: FeatureFlags | None = None

def features() -> FeatureFlags:
    global _FEATURES
    if _FEATURES is None:
        _FEATURES = get_feature_flags()
    return _FEATURES

def reset_features() -> None:
    """Reset cached flags (for testing)."""
    global _FEATURES
    _FEATURES = None

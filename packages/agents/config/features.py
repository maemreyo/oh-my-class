from __future__ import annotations
"""Feature flags for progressive feature rollout."""
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class FeatureFlags:
    topic_decomposition_v1: bool
    vocabulary_batch_v1: bool
    component_strategist_v1: bool
    unit_fanout_concurrency: int  # 1 = sequential, >1 = parallel (Phase 2)

def get_feature_flags() -> FeatureFlags:
    """Read feature flags from environment."""
    return FeatureFlags(
        topic_decomposition_v1=os.getenv("FEATURE_TOPIC_DECOMPOSITION_V1", "false").lower() == "true",
        vocabulary_batch_v1=os.getenv("FEATURE_VOCABULARY_BATCH_V1", "false").lower() == "true",
        component_strategist_v1=os.getenv("FEATURE_COMPONENT_STRATEGIST_V1", "false").lower() == "true",
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

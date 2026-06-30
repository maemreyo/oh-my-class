"""Teaching Pack feature flags (env-var gated)."""
from __future__ import annotations
import os


def topic_decomposition_v1_enabled() -> bool:
    """Return True when OMC_FEATURE_TOPIC_DECOMPOSITION_V1=true."""
    return os.environ.get("OMC_FEATURE_TOPIC_DECOMPOSITION_V1", "").lower() in ("1", "true", "yes")

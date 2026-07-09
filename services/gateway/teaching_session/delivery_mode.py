"""Delivery-mode policy table (TSP-07 AC1-3, amendment).

Delivery mode (this module) is a distinct axis from display preferences
(SDH-01) -- it governs navigation/response/retention/sync *behavior*, never
visual chrome. Kept as a plain data table, matching SDX-03's
`structure_presets.py` shape: adding/adjusting a mode's declared policy is a
dict edit, not a new contract type.

Only `live`'s policy is backed by real runtime today (SSE sync via
`teaching_session.live_sync`, teacher-controlled nav, TSP-01 retention tiers
enforced live). The four async modes' entries are a *declared* policy shape
for a future slice -- no code here enforces `student_paced` nav or polling
sync yet; `teaching_session.service.create_session` fail-closed rejects
creating a session in any non-live mode (TSP-07 amendment).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from services.gateway.teaching_session.models import DeliveryMode


@dataclass(frozen=True, slots=True)
class DeliveryModePolicy:
    mode: DeliveryMode
    response_policy: str
    retention_policy: str
    sync_policy: str
    teacher_controlled: bool


DELIVERY_MODE_POLICIES: Final[dict[DeliveryMode, DeliveryModePolicy]] = {
    DeliveryMode.LIVE: DeliveryModePolicy(
        mode=DeliveryMode.LIVE,
        response_policy="teacher_controlled_nav",
        retention_policy="tsp01_retention_tier",
        sync_policy="realtime_sse",
        teacher_controlled=True,
    ),
    DeliveryMode.HOMEWORK: DeliveryModePolicy(
        mode=DeliveryMode.HOMEWORK,
        response_policy="student_paced",
        retention_policy="tsp01_retention_tier",
        sync_policy="polling",
        teacher_controlled=False,
    ),
    DeliveryMode.REVIEW: DeliveryModePolicy(
        mode=DeliveryMode.REVIEW,
        response_policy="student_paced",
        retention_policy="tsp01_retention_tier",
        sync_policy="none",
        teacher_controlled=False,
    ),
    DeliveryMode.FLIPPED: DeliveryModePolicy(
        mode=DeliveryMode.FLIPPED,
        response_policy="student_paced",
        retention_policy="tsp01_retention_tier",
        sync_policy="polling",
        teacher_controlled=False,
    ),
    DeliveryMode.CATCH_UP: DeliveryModePolicy(
        mode=DeliveryMode.CATCH_UP,
        response_policy="student_paced",
        retention_policy="tsp01_retention_tier",
        sync_policy="none",
        teacher_controlled=False,
    ),
}

# Only `live` has a working runtime in this slice (TSP-07 amendment).
IMPLEMENTED_DELIVERY_MODES: Final[frozenset[DeliveryMode]] = frozenset({DeliveryMode.LIVE})


def describe_delivery_mode_policy(mode: DeliveryMode) -> DeliveryModePolicy:
    """Policy lookup for teacher/admin surfaces and evidence (mirrors `describe_retention_policy`)."""
    return DELIVERY_MODE_POLICIES[mode]

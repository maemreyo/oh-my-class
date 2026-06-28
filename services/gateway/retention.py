"""Retention configuration and helpers for Teaching Pack data governance.

Each data class has a default retention period (in days).
Per-run overrides are supported via the ``retention_days`` column on ``runs``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

# Default retention periods by data class (days).
_DEFAULT_RETENTION: dict[str, int] = {
    "run_metadata": 365,
    "student_evidence": 30,
    "artifacts": 180,
    "events": 90,
    "snapshots": 180,
}


@dataclass(frozen=True, slots=True)
class RetentionConfig:
    """Immutable retention policy with per-class defaults.

    Attributes:
        run_metadata: How long to keep run-level metadata (days).
        student_evidence: How long to keep student PII / evidence (days).
        artifacts: How long to keep artifact content (days).
        events: How long to keep run events (days).
        snapshots: How long to keep rendered snapshots (days).
    """

    run_metadata: int = _DEFAULT_RETENTION["run_metadata"]
    student_evidence: int = _DEFAULT_RETENTION["student_evidence"]
    artifacts: int = _DEFAULT_RETENTION["artifacts"]
    events: int = _DEFAULT_RETENTION["events"]
    snapshots: int = _DEFAULT_RETENTION["snapshots"]

    def as_dict(self) -> dict[str, int]:
        return {
            "run_metadata": self.run_metadata,
            "student_evidence": self.student_evidence,
            "artifacts": self.artifacts,
            "events": self.events,
            "snapshots": self.snapshots,
        }


_DEFAULT_CONFIG = RetentionConfig()


def get_retention_days(data_class: str) -> int:
    """Return the default retention period for *data_class*.

    Raises:
        KeyError: If *data_class* is not a recognised data class.
    """
    return _DEFAULT_RETENTION[data_class]


def is_expired(deleted_at: datetime | None, retention_days: int) -> bool:
    """Return ``True`` if a soft-deleted resource has exceeded its retention window.

    Args:
        deleted_at: When the resource was soft-deleted. ``None`` means
            it has not been deleted and is therefore *not* expired.
        retention_days: Number of days to retain after deletion.
    """
    if deleted_at is None:
        return False
    now = datetime.now(UTC)
    expiry = deleted_at + timedelta(days=retention_days)
    return now > expiry

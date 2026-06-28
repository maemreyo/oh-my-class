"""Exception types for snapshot storage and validation.

INVARIANT-05 enforcer: answer keys must be isolated in teacher_only markers.
"""

from __future__ import annotations


class SnapshotPersistenceError(RuntimeError):
    """Raised when a snapshot cannot be persisted after creation."""

    def __init__(self, snapshot_id: str) -> None:
        super().__init__(snapshot_id)


class AnswerKeyLeakageError(RuntimeError):
    """Raised when answer-key patterns are found outside teacher_only markers.

    INVARIANT-05 violation: answer keys must be isolated in marked sections.
    """

    def __init__(self, snapshot_id: str, issues: list[str]) -> None:
        self.snapshot_id = snapshot_id
        self.issues = issues
        super().__init__(f"snapshot {snapshot_id}: {'; '.join(issues)}")


class NonStandaloneSnapshotApprovalError(RuntimeError):
    """Raised when attempting to approve a snapshot that is not standalone HTML."""

    def __init__(self, snapshot_id: str) -> None:
        super().__init__(snapshot_id)


class SnapshotVersionMismatchError(RuntimeError):
    """Raised when snapshot versions do not match expected versions with block policy."""

    def __init__(self, snapshot_id: str) -> None:
        super().__init__(snapshot_id)

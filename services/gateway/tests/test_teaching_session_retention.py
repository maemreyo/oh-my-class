from __future__ import annotations

from datetime import UTC, datetime, timedelta

from services.gateway.teaching_session.models import (
    RetentionTier,
    SessionDataCategory,
    SessionStatus,
    TeachingSession,
)
from services.gateway.teaching_session.retention import (
    RetentionSelectionAccepted,
    RetentionSelectionRejected,
    allowed_data_categories_for_tier,
    describe_retention_policy,
    is_prunable,
    validate_retention_selection,
)


class TestRetentionSelection:
    def test_none_tier_allowed_without_class_id(self) -> None:
        result = validate_retention_selection(
            tier=RetentionTier.NONE, class_id=None, identifiable_acknowledged=False,
        )
        assert result == RetentionSelectionAccepted(tier=RetentionTier.NONE)

    def test_aggregate_default_allowed_without_class_id(self) -> None:
        """AC4: aggregate is the K-12-safe default and never needs a real class."""
        result = validate_retention_selection(
            tier=RetentionTier.AGGREGATE, class_id=None, identifiable_acknowledged=False,
        )
        assert result == RetentionSelectionAccepted(tier=RetentionTier.AGGREGATE)

    def test_pseudonymous_rejected_without_class_id(self) -> None:
        result = validate_retention_selection(
            tier=RetentionTier.PSEUDONYMOUS, class_id=None, identifiable_acknowledged=False,
        )
        assert result == RetentionSelectionRejected(
            tier=RetentionTier.PSEUDONYMOUS,
            reason="class_id_required_for_identity_bearing_tier",
        )

    def test_pseudonymous_rejected_for_empty_class_id(self) -> None:
        result = validate_retention_selection(
            tier=RetentionTier.PSEUDONYMOUS, class_id="", identifiable_acknowledged=False,
        )
        assert isinstance(result, RetentionSelectionRejected)

    def test_pseudonymous_accepted_with_class_id(self) -> None:
        result = validate_retention_selection(
            tier=RetentionTier.PSEUDONYMOUS, class_id="class-5a", identifiable_acknowledged=False,
        )
        assert result == RetentionSelectionAccepted(tier=RetentionTier.PSEUDONYMOUS)

    def test_identifiable_rejected_without_class_id(self) -> None:
        result = validate_retention_selection(
            tier=RetentionTier.IDENTIFIABLE, class_id=None, identifiable_acknowledged=True,
        )
        assert result == RetentionSelectionRejected(
            tier=RetentionTier.IDENTIFIABLE,
            reason="class_id_required_for_identity_bearing_tier",
        )

    def test_identifiable_rejected_without_acknowledgment(self) -> None:
        result = validate_retention_selection(
            tier=RetentionTier.IDENTIFIABLE, class_id="class-5a", identifiable_acknowledged=False,
        )
        assert result == RetentionSelectionRejected(
            tier=RetentionTier.IDENTIFIABLE,
            reason="identifiable_tier_requires_explicit_acknowledgment",
        )

    def test_identifiable_accepted_with_class_id_and_acknowledgment(self) -> None:
        result = validate_retention_selection(
            tier=RetentionTier.IDENTIFIABLE, class_id="class-5a", identifiable_acknowledged=True,
        )
        assert result == RetentionSelectionAccepted(tier=RetentionTier.IDENTIFIABLE)


class TestDataCategorySeparation:
    def test_raw_responses_excluded_for_none_tier(self) -> None:
        assert SessionDataCategory.RAW_RESPONSES not in allowed_data_categories_for_tier(
            RetentionTier.NONE,
        )

    def test_raw_responses_excluded_for_aggregate_tier(self) -> None:
        """AC4: the K-12 default never allows raw per-student responses."""
        assert SessionDataCategory.RAW_RESPONSES not in allowed_data_categories_for_tier(
            RetentionTier.AGGREGATE,
        )

    def test_raw_responses_allowed_for_pseudonymous_tier(self) -> None:
        assert SessionDataCategory.RAW_RESPONSES in allowed_data_categories_for_tier(
            RetentionTier.PSEUDONYMOUS,
        )

    def test_raw_responses_allowed_for_identifiable_tier(self) -> None:
        assert SessionDataCategory.RAW_RESPONSES in allowed_data_categories_for_tier(
            RetentionTier.IDENTIFIABLE,
        )

    def test_all_categories_are_covered_by_every_tier_mapping(self) -> None:
        for tier in RetentionTier:
            categories = allowed_data_categories_for_tier(tier)
            assert categories.issubset(set(SessionDataCategory))

    def test_teacher_reflections_and_ai_suggestions_allowed_even_at_none_tier(self) -> None:
        """Teacher-authored content is not student data and is not gated by tier."""
        categories = allowed_data_categories_for_tier(RetentionTier.NONE)
        assert SessionDataCategory.TEACHER_REFLECTIONS in categories
        assert SessionDataCategory.AI_SUGGESTIONS in categories


class TestRetentionPolicyVisibility:
    def test_describe_retention_policy_matches_tier(self) -> None:
        description = describe_retention_policy(RetentionTier.AGGREGATE)
        label = description.label.lower()
        assert description.tier is RetentionTier.AGGREGATE
        assert "class-level" in label or "aggregate" in label
        assert description.allowed_categories == allowed_data_categories_for_tier(
            RetentionTier.AGGREGATE,
        )

    def test_every_tier_has_a_description(self) -> None:
        for tier in RetentionTier:
            description = describe_retention_policy(tier)
            assert description.label
            assert description.description


def _session(
    *,
    status: SessionStatus,
    retention_tier: RetentionTier,
    ended_at: datetime | None = None,
    archived_at: datetime | None = None,
    expired_at: datetime | None = None,
) -> TeachingSession:
    session = TeachingSession(
        session_id="s1",
        teacher_id="t1",
        deck_id="deck1",
        snapshot_id="snap1",
        retention_tier=retention_tier,
    )
    session.status = status
    session.ended_at = ended_at
    session.archived_at = archived_at
    session.expired_at = expired_at
    return session


class TestIsPrunable:
    def test_not_prunable_while_scheduled(self) -> None:
        session = _session(status=SessionStatus.SCHEDULED, retention_tier=RetentionTier.NONE)
        assert is_prunable(session, datetime.now(UTC)) is False

    def test_not_prunable_while_live(self) -> None:
        session = _session(status=SessionStatus.LIVE, retention_tier=RetentionTier.NONE)
        assert is_prunable(session, datetime.now(UTC)) is False

    def test_fail_closed_when_terminal_but_no_terminal_timestamp(self) -> None:
        session = _session(status=SessionStatus.ENDED, retention_tier=RetentionTier.NONE)
        assert is_prunable(session, datetime.now(UTC)) is False

    def test_none_tier_prunable_immediately_once_terminal(self) -> None:
        now = datetime.now(UTC)
        session = _session(
            status=SessionStatus.ENDED, retention_tier=RetentionTier.NONE, ended_at=now,
        )
        assert is_prunable(session, now) is True

    def test_aggregate_tier_not_prunable_before_window_elapses(self) -> None:
        now = datetime.now(UTC)
        ended_at = now - timedelta(days=179)
        session = _session(
            status=SessionStatus.ENDED, retention_tier=RetentionTier.AGGREGATE, ended_at=ended_at,
        )
        assert is_prunable(session, now) is False

    def test_aggregate_tier_prunable_after_window_elapses(self) -> None:
        now = datetime.now(UTC)
        ended_at = now - timedelta(days=181)
        session = _session(
            status=SessionStatus.ENDED, retention_tier=RetentionTier.AGGREGATE, ended_at=ended_at,
        )
        assert is_prunable(session, now) is True

    def test_identifiable_tier_has_shorter_window_than_aggregate(self) -> None:
        """More-identifying data is pruned sooner -- shortest window wins for privacy."""
        now = datetime.now(UTC)
        ended_at = now - timedelta(days=31)
        session = _session(
            status=SessionStatus.ENDED,
            retention_tier=RetentionTier.IDENTIFIABLE,
            ended_at=ended_at,
        )
        assert is_prunable(session, now) is True
        # The same elapsed time would NOT be prunable yet under aggregate's longer window.
        aggregate_session = _session(
            status=SessionStatus.ENDED, retention_tier=RetentionTier.AGGREGATE, ended_at=ended_at,
        )
        assert is_prunable(aggregate_session, now) is False

    def test_archived_session_uses_archived_at_as_terminal_timestamp(self) -> None:
        now = datetime.now(UTC)
        archived_at = now - timedelta(days=200)
        session = _session(
            status=SessionStatus.ARCHIVED,
            retention_tier=RetentionTier.AGGREGATE,
            archived_at=archived_at,
        )
        assert is_prunable(session, now) is True

    def test_expired_session_uses_expired_at_when_no_other_terminal_timestamp(self) -> None:
        now = datetime.now(UTC)
        expired_at = now - timedelta(days=200)
        session = _session(
            status=SessionStatus.EXPIRED,
            retention_tier=RetentionTier.AGGREGATE,
            expired_at=expired_at,
        )
        assert is_prunable(session, now) is True

from __future__ import annotations

import pytest

from common.contracts.lesson_sequence import KnowledgeComponent, LessonSequence, SessionPlan
from packages.agents.middleware.sequence_consistency_validator import (
    ConsistencyIssue,
    ConsistencySeverity,
    SequenceConsistencyValidator,
)


class TestSequenceConsistencyValidator:
    def test_cyclic_prerequisites_yield_cycle_issue(self) -> None:
        sequence = _sequence([
            _session("S01", 1, prerequisites=["S02"]),
            _session("S02", 2, bloom="apply", prerequisites=["S01"]),
        ])

        issues = SequenceConsistencyValidator().validate(sequence)

        assert _rules(issues) == ["cycle"]
        assert issues[0].severity is ConsistencySeverity.HARD

    def test_acyclic_prerequisites_pass_cycle_rule(self) -> None:
        sequence = _sequence([
            _session("S01", 1),
            _session("S02", 2, bloom="apply", prerequisites=["S01"]),
        ])

        issues = SequenceConsistencyValidator().validate(sequence)

        assert "cycle" not in _rules(issues)

    def test_five_new_knowledge_components_yield_clt_issue(self) -> None:
        sequence = _sequence([
            _session("S01", 1, kc_count=5),
            _session("S02", 2, bloom="apply"),
        ])

        issues = SequenceConsistencyValidator().validate(sequence)

        clt_issue = next(issue for issue in issues if issue.rule == "clt_overload")
        assert clt_issue.session_id == "S01"
        assert clt_issue.severity is ConsistencySeverity.HARD

    def test_recalled_knowledge_components_do_not_count_toward_clt_limit(self) -> None:
        sequence = _sequence([
            _session("S01", 1, kc_count=4, recalled_count=8),
            _session("S02", 2, bloom="apply"),
        ])

        issues = SequenceConsistencyValidator().validate(sequence)

        assert "clt_overload" not in _rules(issues)

    def test_non_recall_sequence_requires_two_bloom_levels_and_apply_or_higher(self) -> None:
        sequence = _sequence([
            _session("S01", 1, bloom="remember"),
            _session("S02", 2, bloom="understand"),
        ])

        issues = SequenceConsistencyValidator().validate(sequence)

        assert "bloom_rule" in _rules(issues)

    def test_apply_level_satisfies_bloom_rule(self) -> None:
        sequence = _sequence([
            _session("S01", 1, bloom="remember"),
            _session("S02", 2, bloom="apply"),
        ])

        issues = SequenceConsistencyValidator().validate(sequence)

        assert "bloom_rule" not in _rules(issues)

    def test_pure_recall_sequence_is_exempt_from_bloom_rule(self) -> None:
        sequence = _sequence(
            [_session("S01", 1, bloom="remember")],
            open_questions=["pure_recall"],
        )

        issues = SequenceConsistencyValidator().validate(sequence)

        assert "bloom_rule" not in _rules(issues)

    def test_session_count_outside_norm_is_advisory(self) -> None:
        sequence = _sequence([_session("S01", 1, bloom="apply")])

        issues = SequenceConsistencyValidator().validate(sequence)

        count_issue = next(issue for issue in issues if issue.rule == "session_count_norm")
        assert count_issue.severity is ConsistencySeverity.ADVISORY

    def test_duration_drift_over_tolerance_is_hard_issue(self) -> None:
        sequence = _sequence([
            _session("S01", 1, duration=30),
            _session("S02", 2, bloom="apply", duration=30),
        ], total_duration=90)

        issues = SequenceConsistencyValidator().validate(sequence)

        drift_issue = next(issue for issue in issues if issue.rule == "duration_drift")
        assert drift_issue.severity is ConsistencySeverity.HARD

    def test_duration_within_tolerance_passes(self) -> None:
        sequence = _sequence([
            _session("S01", 1, duration=45),
            _session("S02", 2, bloom="apply", duration=45),
        ], total_duration=100)

        issues = SequenceConsistencyValidator().validate(sequence)

        assert "duration_drift" not in _rules(issues)

    def test_prerequisite_depth_over_three_yields_issue(self) -> None:
        sequence = _sequence([
            _session("S01", 1),
            _session("S02", 2, prerequisites=["S01"]),
            _session("S03", 3, prerequisites=["S02"]),
            _session("S04", 4, prerequisites=["S03"]),
            _session("S05", 5, bloom="apply", prerequisites=["S04"]),
        ])

        issues = SequenceConsistencyValidator().validate(sequence)

        depth_issue = next(issue for issue in issues if issue.rule == "prereq_depth")
        assert depth_issue.session_id == "S05"
        assert depth_issue.severity is ConsistencySeverity.HARD

    def test_prerequisite_depth_three_passes(self) -> None:
        sequence = _sequence([
            _session("S01", 1),
            _session("S02", 2, prerequisites=["S01"]),
            _session("S03", 3, prerequisites=["S02"]),
            _session("S04", 4, bloom="apply", prerequisites=["S03"]),
        ])

        issues = SequenceConsistencyValidator().validate(sequence)

        assert "prereq_depth" not in _rules(issues)


@pytest.mark.property
class TestSequenceConsistencyValidatorProperties:
    def test_valid_acyclic_sequence_passes_hard_rules(self) -> None:
        sequence = _sequence([
            _session("S01", 1, bloom="remember", duration=30, kc_count=4),
            _session("S02", 2, bloom="apply", duration=30, kc_count=4, prerequisites=["S01"]),
            _session("S03", 3, bloom="analyze", duration=30, kc_count=4, prerequisites=["S02"]),
        ], total_duration=90)

        issues = SequenceConsistencyValidator().validate(sequence)

        assert [issue for issue in issues if issue.severity is ConsistencySeverity.HARD] == []

    def test_injected_cycle_produces_cycle_rule(self) -> None:
        sequence = _sequence([
            _session("S01", 1, bloom="remember", prerequisites=["S03"]),
            _session("S02", 2, bloom="apply", prerequisites=["S01"]),
            _session("S03", 3, bloom="analyze", prerequisites=["S02"]),
        ], total_duration=90)

        issues = SequenceConsistencyValidator().validate(sequence)

        assert "cycle" in _rules(issues)


def _session(
    session_id: str,
    order_index: int,
    *,
    bloom: str = "remember",
    duration: int = 45,
    kc_count: int = 1,
    recalled_count: int = 0,
    prerequisites: list[str] | None = None,
) -> SessionPlan:
    return SessionPlan.model_construct(
        schema_version="lesson_sequence.v1",
        session_id=session_id,
        order_index=order_index,
        child_run_id=None,
        title=f"Session {session_id}",
        sub_topic=f"Topic {session_id}",
        duration_minutes=duration,
        learning_objectives=[f"Objective {session_id}"],
        bloom_level_primary=bloom,
        knowledge_components=[_kc(session_id, index) for index in range(kc_count)],
        recalled_kc_ids=[f"recall-{index}" for index in range(recalled_count)],
        prerequisite_sessions=prerequisites or [],
        methodology_primary="active_recall",
        methodology_secondary=None,
    )


def _kc(session_id: str, index: int) -> KnowledgeComponent:
    return KnowledgeComponent(
        kc_id=f"{session_id}-KC{index}",
        title=f"KC {index}",
        description=f"Knowledge component {index}",
    )


def _sequence(
    sessions: list[SessionPlan],
    *,
    total_duration: int | None = None,
    open_questions: list[str] | None = None,
) -> LessonSequence:
    return LessonSequence.model_construct(
        schema_version="lesson_sequence.v1",
        topic="Fractions",
        grade_level="Grade 5",
        subject="Math",
        locale="vi",
        total_sessions=len(sessions),
        total_duration_minutes=total_duration or sum(session.duration_minutes for session in sessions),
        sessions=sessions,
        prerequisite_edges=[],
        grounding_status="grounded",
        confidence=0.9,
        open_questions=open_questions or [],
        rationale="A compact sequence for validator tests.",
    )


def _rules(issues: list[ConsistencyIssue]) -> list[str]:
    return [issue.rule for issue in issues]

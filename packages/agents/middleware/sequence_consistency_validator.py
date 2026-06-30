from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Literal, assert_never

import networkx as nx

from common.contracts.lesson_sequence import BloomLevel, LessonSequence
from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState

ConsistencyRule = Literal[
    "cycle",
    "bloom_rule",
    "clt_overload",
    "duration_drift",
    "session_count_norm",
    "prereq_depth",
]


class ConsistencySeverity(StrEnum):
    HARD = "hard"
    ADVISORY = "advisory"


@dataclass(frozen=True, slots=True)
class ConsistencyIssue:
    rule: ConsistencyRule
    severity: ConsistencySeverity
    message: str
    session_id: str | None = None


class SequenceConsistencyValidator(BaseMiddleware):
    name = "sequence_consistency_validator"
    order = 30

    def validate(self, sequence: LessonSequence) -> list[ConsistencyIssue]:
        session_graph = _session_graph(sequence)
        kc_graph = _knowledge_component_graph(sequence)
        return [
            *_cycle_issues(session_graph, kc_graph),
            *_bloom_issues(sequence),
            *_cognitive_load_issues(sequence),
            *_duration_issues(sequence),
            *_session_count_issues(sequence),
            *_prerequisite_depth_issues(sequence, session_graph),
        ]

    async def before_model(
        self,
        state: OhMyClassState,
        _context: MiddlewareContext,
    ) -> OhMyClassState:
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        _context: MiddlewareContext,
    ) -> OhMyClassState:
        return state


def _session_graph(sequence: LessonSequence) -> nx.DiGraph[str]:
    graph: nx.DiGraph[str] = nx.DiGraph()
    graph.add_nodes_from(session.session_id for session in sequence.sessions)
    for session in sequence.sessions:
        graph.add_edges_from(
            (prerequisite_id, session.session_id)
            for prerequisite_id in session.prerequisite_sessions
        )
    return graph


def _knowledge_component_graph(sequence: LessonSequence) -> nx.DiGraph[str]:
    graph: nx.DiGraph[str] = nx.DiGraph()
    graph.add_nodes_from(
        component.kc_id
        for session in sequence.sessions
        for component in session.knowledge_components
    )
    graph.add_edges_from(
        (edge.source_kc_id, edge.target_kc_id)
        for edge in sequence.prerequisite_edges
    )
    return graph


def _cycle_issues(
    session_graph: nx.DiGraph[str],
    kc_graph: nx.DiGraph[str],
) -> list[ConsistencyIssue]:
    issues: list[ConsistencyIssue] = []
    if not nx.is_directed_acyclic_graph(session_graph):
        issues.append(ConsistencyIssue(
            rule="cycle",
            severity=ConsistencySeverity.HARD,
            message="Session prerequisite graph must be acyclic before unit approval.",
        ))
    if not nx.is_directed_acyclic_graph(kc_graph):
        issues.append(ConsistencyIssue(
            rule="cycle",
            severity=ConsistencySeverity.HARD,
            message="Knowledge-component prerequisite graph must be acyclic before unit approval.",
        ))
    return issues


def _bloom_issues(sequence: LessonSequence) -> list[ConsistencyIssue]:
    if _is_pure_recall(sequence):
        return []
    bloom_levels = {session.bloom_level_primary for session in sequence.sessions}
    has_apply_or_higher = any(_is_apply_or_higher(level) for level in bloom_levels)
    if len(bloom_levels) >= 2 and has_apply_or_higher:
        return []
    return [ConsistencyIssue(
        rule="bloom_rule",
        severity=ConsistencySeverity.HARD,
        message=(
            "Sequence needs at least two Bloom levels and one apply-or-higher level; "
            "this is an operational constraint grounded in PPCT/sample plans."
        ),
    )]


def _cognitive_load_issues(sequence: LessonSequence) -> list[ConsistencyIssue]:
    return [
        ConsistencyIssue(
            rule="clt_overload",
            severity=ConsistencySeverity.HARD,
            session_id=session.session_id,
            message="Session introduces more than 4 new knowledge components; recalled KCs do not count.",
        )
        for session in sequence.sessions
        if len(session.knowledge_components) > 4
    ]


def _duration_issues(sequence: LessonSequence) -> list[ConsistencyIssue]:
    actual_minutes = sum(session.duration_minutes for session in sequence.sessions)
    allowed_drift = max(1, round(sequence.total_duration_minutes * 0.15))
    if abs(actual_minutes - sequence.total_duration_minutes) <= allowed_drift:
        return []
    return [ConsistencyIssue(
        rule="duration_drift",
        severity=ConsistencySeverity.HARD,
        message="Total session minutes drift beyond the 15% hard tolerance.",
    )]


def _session_count_issues(sequence: LessonSequence) -> list[ConsistencyIssue]:
    if 2 <= len(sequence.sessions) <= 8:
        return []
    return [ConsistencyIssue(
        rule="session_count_norm",
        severity=ConsistencySeverity.ADVISORY,
        message=(
            "Session count is far from the grounded norm; treat this as an operational "
            "constraint grounded in PPCT/sample plans, not a universal law."
        ),
    )]


def _prerequisite_depth_issues(
    sequence: LessonSequence,
    session_graph: nx.DiGraph[str],
) -> list[ConsistencyIssue]:
    issues: list[ConsistencyIssue] = []
    for session in sequence.sessions:
        depth = _longest_prerequisite_depth(session_graph, session.session_id)
        if depth > 3:
            issues.append(ConsistencyIssue(
                rule="prereq_depth",
                severity=ConsistencySeverity.HARD,
                session_id=session.session_id,
                message="Prerequisite chain exceeds 3 unmastered levels.",
            ))
    return issues


def _longest_prerequisite_depth(graph: nx.DiGraph[str], session_id: str) -> int:
    ancestors = nx.ancestors(graph, session_id)
    if not ancestors:
        return 0
    subgraph = graph.subgraph([*ancestors, session_id])
    return int(max(
        nx.shortest_path_length(subgraph, source=ancestor, target=session_id)
        for ancestor in ancestors
        if nx.has_path(subgraph, ancestor, session_id)
    ))


def _is_apply_or_higher(level: BloomLevel) -> bool:
    match level:
        case "remember" | "understand":
            return False
        case "apply" | "analyze" | "evaluate" | "create":
            return True
        case unreachable:
            assert_never(unreachable)


def _is_pure_recall(sequence: LessonSequence) -> bool:
    return "pure_recall" in {question.lower() for question in sequence.open_questions}

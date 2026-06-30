"""
Nightly/pre-release eval: runs golden topics through unit_planner and asserts pedagogical invariants.
Real LLM via 9router port 20228, model 4omc.
Run: uv run pytest tests/eval/test_decomposition_quality.py -v
"""
from __future__ import annotations

import pytest
import networkx as nx

from packages.agents.sub_agents.unit_planner import ClarificationRequiredError, unit_planner_node
from packages.agents.sub_agents.unit_planner.state import UnitPlannerNodeState
from packages.agents.sub_agents.unit_planner.observability import unit_attribution_tags
from common.contracts.lesson_sequence import BloomLevel, LessonSequence

pytestmark = pytest.mark.real_llm

# ---------------------------------------------------------------------------
# Golden topic fixtures
# ---------------------------------------------------------------------------

_GOLDEN_TOPICS: list[tuple[str, UnitPlannerNodeState]] = [
    (
        "Phân số — Toán Lớp 5",
        UnitPlannerNodeState(
            raw_request="Phân số — Toán Lớp 5",
            class_info={
                "topic": "Phân số — Toán Lớp 5",
                "grade": "Grade 5",
                "subject_focus": "Math",
                "language": "vi",
                "class_size": 30,
                "proficiency_level": "developing",
                "age_band": "upper_primary",
                "attention_span_band": "medium",
            },
            grounding={"grounding_status": "grounded"},
        ),
    ),
    (
        "Present Tenses — English Grade 8",
        UnitPlannerNodeState(
            raw_request="Present Tenses — English Grade 8",
            class_info={
                "topic": "Present Tenses — English Grade 8",
                "grade": "Grade 8",
                "subject_focus": "English",
                "language": "en",
                "class_size": 28,
                "proficiency_level": "developing",
                "age_band": "lower_secondary",
                "attention_span_band": "medium",
            },
            grounding={"grounding_status": "grounded"},
        ),
    ),
    (
        "Quang hợp — KHTN Lớp 6",
        UnitPlannerNodeState(
            raw_request="Quang hợp — KHTN Lớp 6",
            class_info={
                "topic": "Quang hợp — KHTN Lớp 6",
                "grade": "Grade 6",
                "subject_focus": "Science",
                "language": "vi",
                "class_size": 32,
                "proficiency_level": "developing",
                "age_band": "lower_secondary",
                "attention_span_band": "medium",
            },
            grounding={"grounding_status": "partial"},
        ),
    ),
]

_HIGHER_ORDER_BLOOMS: frozenset[BloomLevel] = frozenset({"apply", "analyze", "evaluate", "create"})


# ---------------------------------------------------------------------------
# Helper: parse LessonSequence from node output dict
# ---------------------------------------------------------------------------

def _parse_sequence(result: dict) -> LessonSequence:
    return LessonSequence.model_validate(result["lesson_sequence"])


# ---------------------------------------------------------------------------
# Parametrised golden-topic invariant tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label,state", _GOLDEN_TOPICS, ids=[t[0] for t in _GOLDEN_TOPICS])
@pytest.mark.asyncio
async def test_acyclic_prerequisite_dag(label: str, state: UnitPlannerNodeState) -> None:
    """Invariant 1: the prerequisite_sessions DAG has no cycles."""
    result = await unit_planner_node(state)
    seq = _parse_sequence(result)

    dag: nx.DiGraph = nx.DiGraph()
    for session in seq.sessions:
        dag.add_node(session.session_id)
        for prereq in session.prerequisite_sessions:
            dag.add_edge(prereq, session.session_id)

    assert nx.is_directed_acyclic_graph(dag), (
        f"[{label}] prerequisite_sessions graph contains a cycle"
    )


@pytest.mark.parametrize("label,state", _GOLDEN_TOPICS, ids=[t[0] for t in _GOLDEN_TOPICS])
@pytest.mark.asyncio
async def test_bloom_coverage(label: str, state: UnitPlannerNodeState) -> None:
    """Invariant 2: >= 2 distinct bloom levels; >= 1 session at apply/analyze/evaluate/create."""
    result = await unit_planner_node(state)
    seq = _parse_sequence(result)

    bloom_values = [s.bloom_level_primary for s in seq.sessions]
    distinct_blooms = set(bloom_values)

    assert len(distinct_blooms) >= 2, (
        f"[{label}] only {len(distinct_blooms)} distinct bloom level(s): {distinct_blooms}"
    )
    higher_order_present = any(b in _HIGHER_ORDER_BLOOMS for b in bloom_values)
    assert higher_order_present, (
        f"[{label}] no session at apply/analyze/evaluate/create -- got: {bloom_values}"
    )


@pytest.mark.parametrize("label,state", _GOLDEN_TOPICS, ids=[t[0] for t in _GOLDEN_TOPICS])
@pytest.mark.asyncio
async def test_kc_load_per_session(label: str, state: UnitPlannerNodeState) -> None:
    """Invariant 3: every session has <= 4 knowledge_components."""
    result = await unit_planner_node(state)
    seq = _parse_sequence(result)

    for session in seq.sessions:
        assert len(session.knowledge_components) <= 4, (
            f"[{label}] session {session.session_id} has "
            f"{len(session.knowledge_components)} KCs (max 4)"
        )


@pytest.mark.parametrize("label,state", _GOLDEN_TOPICS, ids=[t[0] for t in _GOLDEN_TOPICS])
@pytest.mark.asyncio
async def test_duration_drift(label: str, state: UnitPlannerNodeState) -> None:
    """Invariant 4: total_duration_minutes is within +-15% of sum(session.duration_minutes)."""
    result = await unit_planner_node(state)
    seq = _parse_sequence(result)

    sum_session_duration = sum(s.duration_minutes for s in seq.sessions)
    declared = seq.total_duration_minutes
    tolerance = sum_session_duration * 0.15
    assert abs(declared - sum_session_duration) <= tolerance, (
        f"[{label}] total_duration_minutes={declared} deviates more than +-15% "
        f"from sum of session durations={sum_session_duration}"
    )


@pytest.mark.parametrize("label,state", _GOLDEN_TOPICS, ids=[t[0] for t in _GOLDEN_TOPICS])
@pytest.mark.asyncio
async def test_session_count_within_norm(label: str, state: UnitPlannerNodeState) -> None:
    """Invariant 5: 2 <= len(sessions) <= 8."""
    result = await unit_planner_node(state)
    seq = _parse_sequence(result)

    count = len(seq.sessions)
    assert 2 <= count <= 8, (
        f"[{label}] session count {count} outside [2, 8]"
    )


@pytest.mark.parametrize("label,state", _GOLDEN_TOPICS, ids=[t[0] for t in _GOLDEN_TOPICS])
@pytest.mark.asyncio
async def test_methodology_primary_set(label: str, state: UnitPlannerNodeState) -> None:
    """Invariant 6: every session has a methodology_primary set (non-empty string)."""
    result = await unit_planner_node(state)
    seq = _parse_sequence(result)

    for session in seq.sessions:
        assert session.methodology_primary, (
            f"[{label}] session {session.session_id} has no methodology_primary"
        )


@pytest.mark.parametrize("label,state", _GOLDEN_TOPICS, ids=[t[0] for t in _GOLDEN_TOPICS])
@pytest.mark.asyncio
async def test_prerequisite_refs_resolve(label: str, state: UnitPlannerNodeState) -> None:
    """Invariant 7: all prerequisite_sessions refs resolve to real session_ids."""
    result = await unit_planner_node(state)
    seq = _parse_sequence(result)

    session_ids = {s.session_id for s in seq.sessions}
    for session in seq.sessions:
        unknown = set(session.prerequisite_sessions) - session_ids
        assert not unknown, (
            f"[{label}] session {session.session_id} has unresolvable prereqs: {unknown}"
        )


@pytest.mark.parametrize("label,state", _GOLDEN_TOPICS, ids=[t[0] for t in _GOLDEN_TOPICS])
@pytest.mark.asyncio
async def test_grounding_status_not_ungrounded(label: str, state: UnitPlannerNodeState) -> None:
    """Invariant 8: grounding_status is 'grounded' or 'partial' for known topics."""
    result = await unit_planner_node(state)
    seq = _parse_sequence(result)

    assert seq.grounding_status in {"grounded", "partial"}, (
        f"[{label}] grounding_status is '{seq.grounding_status}' -- "
        "known golden topics must not be ungrounded"
    )


@pytest.mark.parametrize("label,state", _GOLDEN_TOPICS, ids=[t[0] for t in _GOLDEN_TOPICS])
@pytest.mark.asyncio
async def test_rationale_non_empty(label: str, state: UnitPlannerNodeState) -> None:
    """Invariant 9: sequence.rationale is non-empty."""
    result = await unit_planner_node(state)
    seq = _parse_sequence(result)

    assert seq.rationale and seq.rationale.strip(), (
        f"[{label}] sequence.rationale is empty"
    )


# ---------------------------------------------------------------------------
# Sentinel: empty topic must raise ClarificationRequiredError
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invariant_sentinel_empty_topic_raises() -> None:
    """A deliberately weak call (single ambiguous word, no grounding) must raise ClarificationRequiredError.

    "math" is in the known-ambiguous set and has only one word; without grounding
    the planner must refuse and ask for clarification.  This test proves the
    harness catches failures -- if the planner silently returns a sequence the
    harness itself is broken.
    """
    state = UnitPlannerNodeState(
        raw_request="math",
        class_info={
            "topic": "math",
            "grade": "Grade 5",
            "subject_focus": "Math",
            "language": "en",
            "class_size": 20,
            "proficiency_level": "developing",
            "age_band": "upper_primary",
        },
        grounding=None,
    )
    with pytest.raises(ClarificationRequiredError):
        await unit_planner_node(state)


# ---------------------------------------------------------------------------
# Cost rollup structure (no LLM call -- pure unit test)
# ---------------------------------------------------------------------------

def test_cost_rollup_structure() -> None:
    """Verify that unit_attribution_tags returns the expected keys."""
    tags = unit_attribution_tags("run-abc", session_id="S01", unit_role="session")

    assert "parent_run_id" in tags, "missing key: parent_run_id"
    assert "session_id" in tags, "missing key: session_id"
    assert "unit_role" in tags, "missing key: unit_role"

    assert tags["parent_run_id"] == "run-abc"
    assert tags["session_id"] == "S01"
    assert tags["unit_role"] == "session"

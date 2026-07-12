"""#464: `GenerateOneArtifactPayload` threads `subject`/`grade_band` through
from the contract so `content_coverage_resolution.resolve_content_coverage`
can eventually be called for real -- these fields didn't exist before this
session (see `content_coverage_resolution.py`'s module docstring for the
remaining wiring gap)."""

from __future__ import annotations

import pytest

from packages.agents.teaching_pack.artifact_fanout import (
    coordinate_artifact_fanout,
    route_after_artifact_workflow,
)


def _state(contract: dict[str, object]) -> dict[str, object]:
    return {
        "run_id": "run-payload-test",
        "contract": contract,
        "lesson_plan": {"topic": "Fractions"},
        "research_brief": {"sources": []},
        "artifact_types": ["quiz"],
    }


def _first_wave_send(contract: dict[str, object]):
    initial_state = _state(contract)
    update = coordinate_artifact_fanout(initial_state)
    # `coordinate_artifact_fanout` returns a partial state update, the way a
    # LangGraph node does -- the graph runtime merges it into full state;
    # here that merge has to happen by hand.
    route = route_after_artifact_workflow({**initial_state, **update})
    assert not isinstance(route, str)
    return next(send for send in route if send.arg["artifact_type"] == "quiz")


def test_payload_carries_subject_and_normalized_grade_band(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)

    quiz_send = _first_wave_send({
        "topic": "Fractions", "theme": "default", "subject": "math", "grade_band": "Grade 5",
    })

    assert quiz_send.arg["subject"] == "math"
    assert quiz_send.arg["grade_band"] == "grades_3_5"


def test_payload_defaults_when_contract_omits_subject_and_grade_band(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)

    quiz_send = _first_wave_send({"topic": "Fractions", "theme": "default"})

    assert quiz_send.arg["subject"] == "general"
    assert quiz_send.arg["grade_band"] == "grades_3_5"


def test_payload_falls_back_to_default_band_for_an_unparseable_grade_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)

    quiz_send = _first_wave_send({
        "topic": "Fractions", "theme": "default", "grade_band": "not-a-real-grade",
    })

    assert quiz_send.arg["grade_band"] == "grades_3_5"

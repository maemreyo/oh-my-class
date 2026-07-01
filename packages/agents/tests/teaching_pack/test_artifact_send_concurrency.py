from __future__ import annotations

from packages.agents.teaching_pack.artifact_fanout import route_after_artifact_workflow


def _workflow_state(artifact_type: str) -> dict[str, object]:
    return {
        "workflow_id": f"gen-1:{artifact_type}",
        "artifact_generation_id": "gen-1",
        "artifact_id": f"{artifact_type}-1",
        "artifact_type": artifact_type,
        "status": "passed",
    }


def test_wave_router_respects_domain_parallelism_cap(monkeypatch) -> None:
    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)
    monkeypatch.setenv("TEACHING_PACK_DEFAULT_ARTIFACT_PARALLELISM", "2")

    route = route_after_artifact_workflow({
        "run_id": "run-cap",
        "contract": {"theme": "default"},
        "artifact_generation_id": "gen-1",
        "artifact_wave_index": 1,
        "artifact_types": ["lesson", "worksheet", "quiz", "drill", "recap"],
        "artifact_workflow_states": [_workflow_state("lesson")],
    })

    assert not isinstance(route, str)
    assert [send.arg["artifact_type"] for send in route] == ["worksheet", "quiz"]


def test_wave_router_returns_remaining_branch_after_capped_branches_complete(monkeypatch) -> None:
    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)
    monkeypatch.setenv("TEACHING_PACK_DEFAULT_ARTIFACT_PARALLELISM", "2")

    route = route_after_artifact_workflow({
        "run_id": "run-cap",
        "contract": {"theme": "default"},
        "artifact_generation_id": "gen-1",
        "artifact_wave_index": 1,
        "artifact_types": ["lesson", "worksheet", "quiz", "drill", "recap"],
        "artifact_workflow_states": [
            _workflow_state("lesson"),
            _workflow_state("worksheet"),
            _workflow_state("quiz"),
        ],
    })

    assert not isinstance(route, str)
    assert [send.arg["artifact_type"] for send in route] == ["drill"]

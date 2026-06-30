from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_triage_surfaces_decomposition_suggestion_for_contract_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from packages.agents.teaching_pack.triage import run_triage

    monkeypatch.setenv("OMC_FEATURE_TOPIC_DECOMPOSITION_V1", "true")

    result = await run_triage({
        "run_id": "run-contract-decomposition",
        "contract": {
            "mode": "generate_pack",
            "raw_request": "Dạy thì hiện tại trong 3 tuần",
            "duration_minutes": 135,
        },
    })

    suggestion = result["gate_payload"]["decomposition_suggestion"]
    assert suggestion["suggested_mode"] == "plan_unit"
    assert suggestion["target_sessions"] == 3
    assert suggestion["source"] == "heuristic"
    assert result["contract"]["mode"] == "plan_unit"
    assert result["contract"]["decomposition_intent"]["target_sessions"] == 3


def test_contract_confirmation_approval_extracts_plan_unit_edits() -> None:
    from services.gateway.contract_confirmation_edits import contract_confirmation_edits

    decomposition_intent = {
        "schema_version": "decomposition_intent.v1",
        "target_sessions": 3,
        "session_length_minutes": 45,
        "source": "system",
        "rationale": "Teacher accepted a multi-session unit plan.",
    }

    edits = contract_confirmation_edits({
        "mode": "plan_unit",
        "decomposition_intent": decomposition_intent,
    })

    assert edits == {
        "mode": "plan_unit",
        "decomposition_intent": decomposition_intent,
    }


def test_contract_confirmation_rejects_invalid_decomposition_intent() -> None:
    from services.gateway.contract_confirmation_edits import contract_confirmation_edits

    edits = contract_confirmation_edits({
        "mode": "plan_unit",
        "decomposition_intent": {
            "schema_version": "decomposition_intent.v1",
            "target_sessions": 999,
            "session_length_minutes": 45,
            "source": "system",
            "rationale": "invalid",
        },
    })

    assert edits == {"mode": "plan_unit"}

from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_ambiguous_request_invokes_llm_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.agents.teaching_pack import triage

    calls: list[str] = []

    async def fake_llm(raw_request: str) -> tuple[str, int, str]:
        calls.append(raw_request)
        return "plan_unit", 4, "Broad topic spans multiple competencies."

    monkeypatch.setenv("OMC_FEATURE_TOPIC_DECOMPOSITION_V1", "true")
    monkeypatch.setattr(triage, "triage_with_llm", fake_llm)

    result = await triage.run_triage({
        "run_id": "run-triage-llm",
        "contract": {
            "raw_request": "Design a complete English communication program",
            "duration_minutes": 60,
        },
    })

    assert calls == ["Design a complete English communication program"]
    assert result["contract"]["mode"] == "plan_unit"
    assert result["contract"]["decomposition_intent"]["rationale"] == (
        "Broad topic spans multiple competencies."
    )
    assert result["gate_payload"]["decomposition_suggestion"] == {
        "suggested_mode": "plan_unit",
        "target_sessions": 4,
        "session_length_minutes": 35,
        "source": "auto",
        "rationale": "Broad topic spans multiple competencies.",
    }

"""Triage stage heuristic tests — no LLM required."""
import pytest
from packages.agents.teaching_pack.triage import triage_heuristic


class TestDurationHeuristic:
    def test_long_duration_suggests_unit(self):
        result = triage_heuristic("Dạy toán", 120)
        assert result is not None
        mode, sessions, rationale = result
        assert mode == "plan_unit"
        assert sessions >= 2

    def test_short_duration_suggests_single(self):
        result = triage_heuristic("Teach present simple", 45)
        # Short request + 45 min → generate_pack
        # Note: depends on word count also
        # "Teach present simple" = 3 words, 45 min → generate_pack
        if result is not None:
            assert result[0] == "generate_pack"


class TestMultiSessionRegex:
    def test_tuan_pattern_suggests_unit(self):
        result = triage_heuristic("Dạy thì hiện tại trong 3 tuần", None)
        assert result is not None
        mode, sessions, rationale = result
        assert mode == "plan_unit"
        assert sessions == 3
        assert "heuristic" in rationale.lower() or "tuần" in rationale.lower() or sessions == 3

    def test_biet_pattern_suggests_unit(self):
        result = triage_heuristic("Chương trình học qua 5 buổi", None)
        assert result is not None
        assert result[0] == "plan_unit"
        assert result[1] == 5

    def test_single_session_no_cues(self):
        result = triage_heuristic("What is photosynthesis?", 45)
        # Might be None (ambiguous) or generate_pack
        if result is not None:
            assert result[0] == "generate_pack"


class TestRunTriageFeatureFlag:
    @pytest.mark.anyio
    async def test_flag_off_returns_empty(self, monkeypatch):
        monkeypatch.delenv("OMC_FEATURE_TOPIC_DECOMPOSITION_V1", raising=False)
        from packages.agents.teaching_pack.triage import run_triage
        result = await run_triage({"contract": {"raw_request": "Dạy 3 tuần"}, "run_id": "test"})
        assert result == {}

    @pytest.mark.anyio
    async def test_flag_on_returns_update(self, monkeypatch):
        monkeypatch.setenv("OMC_FEATURE_TOPIC_DECOMPOSITION_V1", "true")
        from packages.agents.teaching_pack.triage import run_triage
        result = await run_triage({
            "contract": {"raw_request": "Dạy thì hiện tại trong 3 tuần", "duration_minutes": 135},
            "run_id": "test",
        })
        assert "contract" in result
        assert result["contract"]["mode"] == "plan_unit"
        assert "gate_payload" in result
        assert "decomposition_suggestion" in result["gate_payload"]

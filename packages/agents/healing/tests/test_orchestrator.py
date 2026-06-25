"""Tests for HealingOrchestrator and strategy selection."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState



def make_state(**overrides) -> dict[str, Any]:
    base = {
        "raw_request": "Teach photosynthesis",
        "teacher_id": "t-001",
        "class_info": {"grade": 5},
        "run_id": "run-001",
        "fail_count": 0,
        "fail_type": "validation",
        "fail_layer": "schema",
        "fail_context": {"errors": ["missing sections"]},
        "artifacts": [{"type": "lesson", "content": "Plants use light."}],
    }
    base.update(overrides)
    return base


class TestHealingOrchestrator:
    def test_rewrite_on_first_validation_fail(self):
        from packages.agents.healing.orchestrator import HealingOrchestrator
        state = make_state(fail_count=0, fail_type="validation")
        result = HealingOrchestrator().heal(cast("OhMyClassState", state))
        assert result["healing_strategy"] == "rewrite"
        assert result["artifacts"] is None
        assert result["fail_count"] == 1

    def test_rewrite_on_first_content_fail(self):
        from packages.agents.healing.orchestrator import HealingOrchestrator
        state = make_state(fail_count=0, fail_type="content")
        result = HealingOrchestrator().heal(cast("OhMyClassState", state))
        assert result["healing_strategy"] == "rewrite"

    def test_retry_on_first_transient_fail(self):
        from packages.agents.healing.orchestrator import HealingOrchestrator
        state = make_state(fail_count=0, fail_type="transient")
        with patch("packages.agents.healing.strategies.retry.time.sleep"):
            result = HealingOrchestrator().heal(cast("OhMyClassState", state))
        assert result["healing_strategy"] == "retry"

    def test_reroute_on_second_fail(self):
        from packages.agents.healing.orchestrator import HealingOrchestrator
        state = make_state(fail_count=1, fail_type="validation", generation_model="f.light")
        result = HealingOrchestrator().heal(cast("OhMyClassState", state))
        assert result["healing_strategy"] == "reroute"
        assert result["generation_model"] == "f.pro"

    def test_replan_on_third_fail(self):
        from packages.agents.healing.orchestrator import HealingOrchestrator
        state = make_state(fail_count=2, fail_type="validation")
        result = HealingOrchestrator().heal(cast("OhMyClassState", state))
        assert result["healing_strategy"] == "replan"
        assert result["artifacts"] is None
        assert result["judge_score"] is None

    def test_escalate_after_max_retries(self):
        from packages.agents.healing.orchestrator import HealingOrchestrator
        state = make_state(fail_count=4, fail_type="validation", fail_layer="schema")
        result = HealingOrchestrator(max_retries=3).heal(cast("OhMyClassState", state))
        assert result["healing_strategy"] == "escalate"
        assert result["escalate"] is True
        assert result["fail_count"] == 5

    def test_escalate_at_exactly_max_retries_plus_one(self):
        from packages.agents.healing.orchestrator import HealingOrchestrator
        state = make_state(fail_count=3, fail_type="validation")
        result = HealingOrchestrator(max_retries=3).heal(cast("OhMyClassState", state))
        assert result["healing_strategy"] == "escalate"

    def test_healing_node_is_callable(self):
        from packages.agents.healing.orchestrator import healing_node
        assert callable(healing_node)

    def test_route_after_healing_escalate(self):
        from packages.agents.healing.orchestrator import route_after_healing
        assert route_after_healing(cast("OhMyClassState", {"escalate": True})) == "escalate_node"

    def test_route_after_healing_generate(self):
        from packages.agents.healing.orchestrator import route_after_healing
        assert route_after_healing(cast("OhMyClassState", {"escalate": False})) == "step_08_generate"  # noqa: E501
        assert route_after_healing(cast("OhMyClassState", {})) == "step_08_generate"


class TestRetryStrategy:
    def test_returns_retry_strategy(self):
        from packages.agents.healing.strategies.retry import apply
        with patch("packages.agents.healing.strategies.retry.time.sleep"):
            result = apply({}, 1)
        assert result["healing_strategy"] == "retry"

    def test_includes_fail_count(self):
        from packages.agents.healing.strategies.retry import apply
        with patch("packages.agents.healing.strategies.retry.time.sleep"):
            result = apply({}, 2)
        assert result["fail_count"] == 2

    def test_sleep_is_called(self):
        from packages.agents.healing.strategies.retry import apply
        with patch("packages.agents.healing.strategies.retry.time.sleep") as mock_sleep:
            apply({}, 1)
        mock_sleep.assert_called_once()


class TestRewriteStrategy:
    def test_returns_rewrite_strategy(self):
        from packages.agents.healing.strategies.rewrite import apply
        result = apply({"fail_context": {"errors": ["bad schema"]}}, 1)
        assert result["healing_strategy"] == "rewrite"

    def test_clears_artifacts(self):
        from packages.agents.healing.strategies.rewrite import apply
        result = apply({}, 1)
        assert result["artifacts"] is None

    def test_injects_error_context(self):
        from packages.agents.healing.strategies.rewrite import apply
        result = apply({"fail_context": {"errors": ["missing content"]}}, 1)
        assert "rewrite_instruction" in result["healing_context"]
        assert "missing content" in result["healing_context"]["rewrite_instruction"]

    def test_top_3_errors_only(self):
        from packages.agents.healing.strategies.rewrite import apply
        errors = ["err1", "err2", "err3", "err4", "err5"]
        result = apply({"fail_context": {"errors": errors}}, 1)
        instruction = result["healing_context"]["rewrite_instruction"]
        assert "err4" not in instruction
        assert "err5" not in instruction


class TestRerouteStrategy:
    def test_upgrades_light_to_pro(self):
        from packages.agents.healing.strategies.reroute import apply
        result = apply({"generation_model": "f.light"}, 2)
        assert result["generation_model"] == "f.pro"

    def test_downgrades_pro_to_light(self):
        from packages.agents.healing.strategies.reroute import apply
        result = apply({"generation_model": "f.pro"}, 2)
        assert result["generation_model"] == "f.light"

    def test_defaults_to_light_when_no_model(self):
        from packages.agents.healing.strategies.reroute import apply
        result = apply({}, 2)
        assert result["generation_model"] in ("f.light", "f.pro")

    def test_clears_artifacts(self):
        from packages.agents.healing.strategies.reroute import apply
        result = apply({}, 2)
        assert result["artifacts"] is None


class TestReplanStrategy:
    def test_clears_all_downstream_state(self):
        from packages.agents.healing.strategies.replan import apply
        result = apply({}, 3)
        assert result["artifacts"] is None
        assert result["judge_score"] is None
        assert result["schema_valid"] is None

    def test_returns_replan_strategy(self):
        from packages.agents.healing.strategies.replan import apply
        result = apply({}, 3)
        assert result["healing_strategy"] == "replan"


class TestEscalateStrategy:
    def test_sets_escalate_true(self):
        from packages.agents.healing.strategies.escalate import apply
        result = apply({"fail_layer": "schema"}, 5)
        assert result["escalate"] is True

    def test_includes_reason(self):
        from packages.agents.healing.strategies.escalate import apply
        result = apply({"fail_layer": "judge", "fail_context": {"errors": ["low score"]}}, 4)
        assert "escalate_reason" in result
        assert "judge" in result["escalate_reason"]

    def test_sets_error_field(self):
        from packages.agents.healing.strategies.escalate import apply
        result = apply({"fail_layer": "content"}, 4)
        assert "error" in result
        assert "content" in result["error"]


class TestCircuitBreaker:
    def test_allows_calls_when_closed(self):
        from packages.agents.healing.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker(threshold=3)
        result = cb.call(lambda: 42)
        assert result == 42

    def test_opens_after_threshold_failures(self):
        from packages.agents.healing.circuit_breaker import CircuitBreaker, CircuitOpenError
        cb = CircuitBreaker(threshold=3)
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.state == "open"
        with pytest.raises(CircuitOpenError):
            cb.call(lambda: None)

    def test_resets_on_success(self):
        from packages.agents.healing.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker(threshold=3)
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        cb.call(lambda: None)
        assert cb.state == "closed"
        assert cb.failures == 0

    def test_tracks_failure_count(self):
        from packages.agents.healing.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker(threshold=5)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.failures == 1


class TestHTMLHealer:
    def test_injects_missing_doctype(self):
        from packages.agents.healing.html_healer import validate_and_heal
        result = validate_and_heal("<html><body>Hello</body></html>")
        assert "<!DOCTYPE html>" in result["html"]
        assert result["healed"] is True

    def test_does_not_duplicate_doctype(self):
        from packages.agents.healing.html_healer import validate_and_heal
        html = "<!DOCTYPE html><html><body>Hello</body></html>"
        result = validate_and_heal(html)
        assert result["html"].count("<!DOCTYPE html>") == 1

    def test_removes_external_assets(self):
        from packages.agents.healing.html_healer import validate_and_heal
        html = '<!DOCTYPE html><html><body><img src="https://cdn.example.com/img.png"></body></html>'
        result = validate_and_heal(html)
        assert "https://" not in result["html"]
        assert result["healed"] is True

    def test_no_changes_when_valid(self):
        from packages.agents.healing.html_healer import validate_and_heal
        html = "<!DOCTYPE html><html><body>Clean content.</body></html>"
        result = validate_and_heal(html)
        assert result["healed"] is False
        assert result["html"] == html

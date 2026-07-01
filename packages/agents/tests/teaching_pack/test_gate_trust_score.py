"""Tests for gate_trust module — deterministic, no LLM.

All tests use an in-memory store stub that satisfies the BaseStore
get/put interface used by gate_trust.py.
"""
from __future__ import annotations

import dataclasses
from typing import Any


# ── In-memory store stub ──────────────────────────────────────────────────────

@dataclasses.dataclass
class _StubItem:
    value: Any


class _MemoryStore:
    """Minimal in-memory stub satisfying store.get / store.put."""

    def __init__(self) -> None:
        self._data: dict[tuple, dict[str, _StubItem]] = {}

    def get(self, namespace: tuple, key: str) -> _StubItem | None:
        return self._data.get(namespace, {}).get(key)

    def put(
        self,
        namespace: tuple,
        key: str,
        value: Any,
        *,
        ttl: Any = None,
        index: Any = None,
    ) -> None:
        if namespace not in self._data:
            self._data[namespace] = {}
        self._data[namespace][key] = _StubItem(value=value)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _store_with_events(teacher_id: str, gate_name: str, events: list[dict]) -> _MemoryStore:
    """Pre-populate a store with an event list for a teacher+gate."""
    from packages.agents.teaching_pack.store_namespaces import teacher_preferences_ns
    store = _MemoryStore()
    ns = teacher_preferences_ns(teacher_id)
    key = f"gate_trust::{gate_name}"
    store.put(ns, key, {"events": events})
    return store


# ── compute_trust_score ───────────────────────────────────────────────────────

class TestComputeTrustScore:
    def test_no_history_returns_zero(self):
        from packages.agents.teaching_pack.gate_trust import compute_trust_score
        store = _MemoryStore()
        assert compute_trust_score(store, "teacher-1", "content_approval") == 0.0

    def test_all_approvals_returns_one(self):
        from packages.agents.teaching_pack.gate_trust import compute_trust_score
        events = [{"action": "approve", "artifact_types": ["lesson"]}] * 5
        store = _store_with_events("t1", "content_approval", events)
        assert compute_trust_score(store, "t1", "content_approval") == 1.0

    def test_all_rejections_returns_zero(self):
        from packages.agents.teaching_pack.gate_trust import compute_trust_score
        events = [{"action": "reject", "artifact_types": []}] * 4
        store = _store_with_events("t1", "content_approval", events)
        assert compute_trust_score(store, "t1", "content_approval") == 0.0

    def test_mixed_approve_reject_returns_half(self):
        from packages.agents.teaching_pack.gate_trust import compute_trust_score
        events = (
            [{"action": "approve", "artifact_types": []}] * 5
            + [{"action": "reject", "artifact_types": []}] * 5
        )
        store = _store_with_events("t1", "content_approval", events)
        assert compute_trust_score(store, "t1", "content_approval") == 0.5

    def test_edit_counts_as_half_weight(self):
        from packages.agents.teaching_pack.gate_trust import compute_trust_score
        events = [{"action": "edit", "artifact_types": []}] * 4
        store = _store_with_events("t1", "content_approval", events)
        assert compute_trust_score(store, "t1", "content_approval") == 0.5

    def test_request_edits_counts_as_half_weight(self):
        from packages.agents.teaching_pack.gate_trust import compute_trust_score
        events = [{"action": "request_edits", "artifact_types": []}] * 4
        store = _store_with_events("t1", "content_approval", events)
        assert compute_trust_score(store, "t1", "content_approval") == 0.5

    def test_auto_approved_counts_as_full_weight(self):
        from packages.agents.teaching_pack.gate_trust import compute_trust_score
        events = [{"action": "auto_approved", "artifact_types": []}] * 4
        store = _store_with_events("t1", "content_approval", events)
        assert compute_trust_score(store, "t1", "content_approval") == 1.0

    def test_rolling_window_caps_at_10(self):
        from packages.agents.teaching_pack.gate_trust import compute_trust_score
        # 5 rejects (old) + 10 approves (recent) — window of 10 = all approves
        events = (
            [{"action": "reject", "artifact_types": []}] * 5
            + [{"action": "approve", "artifact_types": []}] * 10
        )
        store = _store_with_events("t1", "content_approval", events)
        assert compute_trust_score(store, "t1", "content_approval") == 1.0

    def test_unknown_action_has_zero_weight(self):
        from packages.agents.teaching_pack.gate_trust import compute_trust_score
        events = [{"action": "unknown_action", "artifact_types": []}] * 4
        store = _store_with_events("t1", "content_approval", events)
        assert compute_trust_score(store, "t1", "content_approval") == 0.0

    def test_different_gate_names_isolated(self):
        from packages.agents.teaching_pack.gate_trust import compute_trust_score
        events = [{"action": "approve", "artifact_types": []}] * 4
        store = _store_with_events("t1", "content_approval", events)
        # blueprint_approval has no history — should return 0.0
        assert compute_trust_score(store, "t1", "blueprint_approval") == 0.0

    def test_different_teacher_ids_isolated(self):
        from packages.agents.teaching_pack.gate_trust import compute_trust_score
        events = [{"action": "approve", "artifact_types": []}] * 4
        store = _store_with_events("teacher-A", "content_approval", events)
        assert compute_trust_score(store, "teacher-B", "content_approval") == 0.0


# ── record_gate_event ─────────────────────────────────────────────────────────

class TestRecordGateEvent:
    def test_first_event_stored(self):
        from packages.agents.teaching_pack.gate_trust import compute_trust_score, record_gate_event
        store = _MemoryStore()
        record_gate_event(store, "t1", "content_approval", "approve", ["lesson"])
        assert compute_trust_score(store, "t1", "content_approval") == 1.0

    def test_events_accumulate(self):
        from packages.agents.teaching_pack.gate_trust import compute_trust_score, record_gate_event
        store = _MemoryStore()
        for _ in range(3):
            record_gate_event(store, "t1", "content_approval", "approve", [])
        record_gate_event(store, "t1", "content_approval", "reject", [])
        score = compute_trust_score(store, "t1", "content_approval")
        assert score == 3 / 4  # 3 approves + 1 reject in a 4-item window

    def test_history_capped_at_double_window(self):
        from packages.agents.teaching_pack.gate_trust import record_gate_event
        from packages.agents.teaching_pack.store_namespaces import teacher_preferences_ns
        store = _MemoryStore()
        for i in range(25):
            record_gate_event(store, "t1", "content_approval", "approve", [])
        ns = teacher_preferences_ns("t1")
        stored = store.get(ns, "gate_trust::content_approval")
        assert stored is not None
        assert len(stored.value["events"]) == 20  # capped at WINDOW_SIZE * 2


# ── is_fast_lane_eligible ─────────────────────────────────────────────────────

class TestIsFastLaneEligible:
    def test_content_approval_eligible(self):
        from packages.agents.teaching_pack.gate_trust import is_fast_lane_eligible
        assert is_fast_lane_eligible("content_approval") is True

    def test_blueprint_approval_eligible(self):
        from packages.agents.teaching_pack.gate_trust import is_fast_lane_eligible
        assert is_fast_lane_eligible("blueprint_approval") is True

    def test_clarification_required_excluded(self):
        from packages.agents.teaching_pack.gate_trust import is_fast_lane_eligible
        assert is_fast_lane_eligible("clarification_required") is False

    def test_contract_confirmation_excluded(self):
        from packages.agents.teaching_pack.gate_trust import is_fast_lane_eligible
        assert is_fast_lane_eligible("contract_confirmation") is False

    def test_unknown_gate_not_eligible(self):
        from packages.agents.teaching_pack.gate_trust import is_fast_lane_eligible
        assert is_fast_lane_eligible("some_other_gate") is False


# ── should_fast_lane ──────────────────────────────────────────────────────────

class TestShouldFastLane:
    def test_returns_true_when_score_meets_threshold(self):
        from packages.agents.teaching_pack.gate_trust import should_fast_lane
        events = [{"action": "approve", "artifact_types": []}] * 10
        store = _store_with_events("t1", "content_approval", events)
        assert should_fast_lane(store, "t1", "content_approval", threshold=0.85) is True

    def test_returns_false_when_score_below_threshold(self):
        from packages.agents.teaching_pack.gate_trust import should_fast_lane
        events = [{"action": "approve", "artifact_types": []}] * 7 + [{"action": "reject", "artifact_types": []}] * 3
        store = _store_with_events("t1", "content_approval", events)
        # score = 0.7, threshold = 0.85
        assert should_fast_lane(store, "t1", "content_approval", threshold=0.85) is False

    def test_returns_false_for_zero_threshold(self):
        from packages.agents.teaching_pack.gate_trust import should_fast_lane
        events = [{"action": "approve", "artifact_types": []}] * 10
        store = _store_with_events("t1", "content_approval", events)
        # threshold=0 would auto-approve everyone — guarded
        assert should_fast_lane(store, "t1", "content_approval", threshold=0.0) is False

    def test_returns_false_for_excluded_gate_regardless_of_score(self):
        from packages.agents.teaching_pack.gate_trust import should_fast_lane
        events = [{"action": "approve", "artifact_types": []}] * 10
        store = _store_with_events("t1", "clarification_required", events)
        assert should_fast_lane(store, "t1", "clarification_required", threshold=0.5) is False

    def test_new_teacher_no_history_returns_false(self):
        from packages.agents.teaching_pack.gate_trust import should_fast_lane
        store = _MemoryStore()
        assert should_fast_lane(store, "new-teacher", "content_approval", threshold=0.85) is False

    def test_score_exactly_at_threshold_qualifies(self):
        from packages.agents.teaching_pack.gate_trust import should_fast_lane
        events = [{"action": "approve", "artifact_types": []}] * 8 + [{"action": "reject", "artifact_types": []}] * 2
        store = _store_with_events("t1", "content_approval", events)
        # score = 0.8, threshold = 0.8 — exact match should qualify
        assert should_fast_lane(store, "t1", "content_approval", threshold=0.8) is True


# ── GateConfig fast_lane_threshold ───────────────────────────────────────────

class TestGateConfigFastLaneThreshold:
    def test_default_is_none(self):
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().fast_lane_threshold is None

    def test_env_sets_float(self, monkeypatch):
        monkeypatch.setenv("GATE_FAST_LANE_THRESHOLD", "0.85")
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().fast_lane_threshold == 0.85

    def test_env_empty_string_yields_none(self, monkeypatch):
        monkeypatch.setenv("GATE_FAST_LANE_THRESHOLD", "")
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().fast_lane_threshold is None


# ── _teacher_approval fast-lane path ─────────────────────────────────────────

class TestTeacherApprovalFastLane:
    def _make_state(self, teacher_id: str = "t1") -> dict:
        return {
            "run_id": "run-001",
            "contract": {"teacher_id": teacher_id},
            "rendered_snapshots": [{"snapshot_id": "snap-1"}],
            "artifacts": [{"artifact_type": "lesson", "content": "hi"}],
            "quality_scores": {},
        }

    def test_auto_approves_when_trust_meets_threshold(self, monkeypatch):
        monkeypatch.setenv("GATE_FAST_LANE_THRESHOLD", "0.8")
        from packages.agents.teaching_pack.nodes import _teacher_approval
        events = [{"action": "approve", "artifact_types": []}] * 10
        store = _store_with_events("t1", "content_approval", events)
        result = _teacher_approval(self._make_state(), store=store)
        assert result["teacher_approved"] is True
        assert result["teacher_decision"] == "approve"
        assert result["approval_gate"].get("auto_approved") is True

    def test_auto_approve_records_event(self, monkeypatch):
        monkeypatch.setenv("GATE_FAST_LANE_THRESHOLD", "0.8")
        from packages.agents.teaching_pack.gate_trust import compute_trust_score
        from packages.agents.teaching_pack.nodes import _teacher_approval
        events = [{"action": "approve", "artifact_types": []}] * 10
        store = _store_with_events("t1", "content_approval", events)
        _teacher_approval(self._make_state(), store=store)
        # After auto-approval, an "approve" event is recorded — still 1.0
        assert compute_trust_score(store, "t1", "content_approval") == 1.0

    def test_no_auto_approve_when_threshold_is_none(self, monkeypatch):
        monkeypatch.delenv("GATE_FAST_LANE_THRESHOLD", raising=False)
        import unittest.mock as mock
        from packages.agents.teaching_pack.nodes import _teacher_approval
        store = _MemoryStore()
        # interrupt() must be called when threshold is None
        with mock.patch("langgraph.types.interrupt", side_effect=StopIteration("interrupted")):
            try:
                _teacher_approval(self._make_state(), store=store)
            except StopIteration as exc:
                assert str(exc) == "interrupted"
            else:
                raise AssertionError("interrupt() was not called")

    def test_no_auto_approve_when_store_is_none(self, monkeypatch):
        monkeypatch.setenv("GATE_FAST_LANE_THRESHOLD", "0.8")
        import unittest.mock as mock
        from packages.agents.teaching_pack.nodes import _teacher_approval
        # Without store, trust can't be computed → fall through to interrupt()
        with mock.patch("langgraph.types.interrupt", side_effect=StopIteration("interrupted")):
            try:
                _teacher_approval(self._make_state(), store=None)
            except StopIteration as exc:
                assert str(exc) == "interrupted"
            else:
                raise AssertionError("interrupt() was not called")

    def test_no_auto_approve_when_score_below_threshold(self, monkeypatch):
        monkeypatch.setenv("GATE_FAST_LANE_THRESHOLD", "0.9")
        import unittest.mock as mock
        from packages.agents.teaching_pack.nodes import _teacher_approval
        # score = 0.5 (5 approves + 5 rejects) < 0.9 → interrupt required
        events = (
            [{"action": "approve", "artifact_types": []}] * 5
            + [{"action": "reject", "artifact_types": []}] * 5
        )
        store = _store_with_events("t1", "content_approval", events)
        with mock.patch("langgraph.types.interrupt", side_effect=StopIteration("interrupted")):
            try:
                _teacher_approval(self._make_state(), store=store)
            except StopIteration as exc:
                assert str(exc) == "interrupted"
            else:
                raise AssertionError("interrupt() was not called")

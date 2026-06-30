"""Issue agent-interaction/000: scoped-regeneration determinism.

Verifies that merge_regenerated_artifacts (sequential path) is a pure,
deterministic function under any call order. No LLM.
"""
from __future__ import annotations

import pytest

from packages.agents.teaching_pack.scoped_regeneration import (
    merge_regenerated_artifacts,
    rejected_artifact_types,
    scoped_rejections,
)


def _a(artifact_id: str, artifact_type: str) -> dict:
    return {"artifact_id": artifact_id, "artifact_type": artifact_type, "content": "c"}


def _scoped_gate(rejections: list[dict]) -> dict:
    return {"rejection_type": "scoped", "artifact_rejections": rejections}


class TestMergeRegeneratedArtifacts:
    def test_no_rejections_returns_generated(self):
        existing = [_a("1", "lesson"), _a("2", "worksheet")]
        generated = [_a("3", "lesson"), _a("4", "worksheet")]
        result = merge_regenerated_artifacts(existing, {}, generated)
        assert result == generated

    def test_scoped_rejection_removes_rejected_and_appends_new(self):
        a = _a("id-a", "lesson")
        b = _a("id-b", "worksheet")
        existing = [a, b]
        gate = _scoped_gate([{"artifact_id": "id-b", "reason": "bad"}])
        new_b = _a("id-b-new", "worksheet")
        result = merge_regenerated_artifacts(existing, gate, [new_b])
        ids = [r["artifact_id"] for r in result]
        assert "id-b" not in ids
        assert "id-b-new" in ids
        assert "id-a" in ids

    def test_preserved_items_come_before_newly_generated(self):
        a = _a("id-a", "lesson")
        b = _a("id-b", "worksheet")
        existing = [a, b]
        gate = _scoped_gate([{"artifact_id": "id-b", "reason": "bad"}])
        new_b = _a("id-b-new", "worksheet")
        result = merge_regenerated_artifacts(existing, gate, [new_b])
        assert result[0]["artifact_id"] == "id-a"
        assert result[1]["artifact_id"] == "id-b-new"

    def test_deterministic_called_twice_same_result(self):
        existing = [_a("1", "lesson"), _a("2", "worksheet"), _a("3", "quiz")]
        gate = _scoped_gate([{"artifact_id": "2", "reason": "r"}])
        new_ws = _a("2-new", "worksheet")
        r1 = merge_regenerated_artifacts(existing, gate, [new_ws])
        r2 = merge_regenerated_artifacts(existing, gate, [new_ws])
        assert r1 == r2

    def test_non_scoped_gate_treated_as_no_rejection(self):
        existing = [_a("1", "lesson")]
        gate = {"rejection_type": "full"}  # not scoped
        generated = [_a("2", "lesson")]
        result = merge_regenerated_artifacts(existing, gate, generated)
        assert result == generated

    def test_empty_existing_returns_generated(self):
        generated = [_a("1", "lesson")]
        result = merge_regenerated_artifacts([], {}, generated)
        assert result == generated

    def test_type_also_excluded_in_scoped_rejection(self):
        a = _a("id-a", "lesson")
        b = _a("id-b", "worksheet")
        c = _a("id-c", "worksheet")  # same type as b
        existing = [a, b, c]
        gate = _scoped_gate([{"artifact_id": "id-b", "reason": "r"}])
        new_ws = _a("id-b-new", "worksheet")
        result = merge_regenerated_artifacts(existing, gate, [new_ws])
        types = [r["artifact_type"] for r in result]
        # Both b and c (worksheet type) are excluded; new worksheet added
        assert types.count("worksheet") == 1
        assert result[-1]["artifact_id"] == "id-b-new"


class TestRejectedArtifactTypes:
    def test_returns_types_for_scoped_rejections(self):
        existing = [_a("id-a", "lesson"), _a("id-b", "worksheet")]
        gate = _scoped_gate([{"artifact_id": "id-b", "reason": "r"}])
        types = rejected_artifact_types(existing, gate)
        assert types == ["worksheet"]

    def test_no_rejection_returns_empty(self):
        existing = [_a("id-a", "lesson")]
        types = rejected_artifact_types(existing, {})
        assert types == []

    def test_deduplicated(self):
        existing = [_a("id-a", "lesson"), _a("id-b", "lesson")]
        gate = _scoped_gate([
            {"artifact_id": "id-a", "reason": "r"},
            {"artifact_id": "id-b", "reason": "r"},
        ])
        types = rejected_artifact_types(existing, gate)
        assert types == ["lesson"]


class TestScopedRejections:
    def test_returns_empty_for_non_scoped(self):
        assert scoped_rejections([_a("1", "lesson")], {"rejection_type": "full"}) == []
        assert scoped_rejections([_a("1", "lesson")], {}) == []

    def test_unknown_artifact_id_in_gate_skipped(self):
        existing = [_a("id-a", "lesson")]
        gate = _scoped_gate([{"artifact_id": "id-unknown", "reason": "r"}])
        result = scoped_rejections(existing, gate)
        assert result == []

    def test_known_artifact_id_returned(self):
        a = _a("id-a", "lesson")
        gate = _scoped_gate([{"artifact_id": "id-a", "reason": "too short"}])
        result = scoped_rejections([a], gate)
        assert len(result) == 1
        assert result[0]["artifact_id"] == "id-a"
        assert result[0]["artifact_type"] == "lesson"

"""Issue agent-interaction/000: order-stable index-keyed reducer.

Property tests: parallel Send branches writing artifacts in any order must
produce identical merged state. No LLM.
"""
from __future__ import annotations

import itertools

from packages.agents.teaching_pack.reducers import (
    stable_merge_artifact_references,
    stable_merge_files,
    stable_merge_workflow_states,
)


def _artifact(document_id: str, artifact_type: str = "lesson") -> dict[str, object]:
    return {
        "document_id": document_id,
        "artifact_id": document_id,
        "artifact_type": artifact_type,
        "generation_id": "gen-1",
        "version": 1,
        "title": f"body-{document_id}",
    }


def _workflow_state(
    artifact_id: str,
    artifact_type: str = "lesson",
    status: str = "passed",
) -> dict[str, object]:
    return {
        "workflow_id": f"wf-{artifact_id}",
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "status": status,
    }


class TestStableMergeArtifacts:
    def test_empty_prev_returns_new_sorted(self):
        a, b, c = _artifact("c"), _artifact("a"), _artifact("b")
        result = stable_merge_artifact_references([], [a, b, c])
        assert [r["document_id"] for r in result] == ["a", "b", "c"]

    def test_empty_new_returns_prev_sorted(self):
        a, b = _artifact("b"), _artifact("a")
        result = stable_merge_artifact_references([a, b], [])
        assert [r["document_id"] for r in result] == ["a", "b"]

    def test_both_empty_returns_empty(self):
        assert stable_merge_artifact_references([], []) == []

    def test_new_overwrites_prev_by_document_id(self):
        old = _artifact("x", "lesson")
        new = {**old, "title": "updated", "version": 2}
        result = stable_merge_artifact_references([old], [new])
        assert len(result) == 1
        assert result[0]["title"] == "updated"

    def test_non_overlapping_accumulates(self):
        a = _artifact("a", "lesson")
        b = _artifact("b", "worksheet")
        result = stable_merge_artifact_references([a], [b])
        ids = [r["document_id"] for r in result]
        assert sorted(ids) == ids  # sorted
        assert set(ids) == {"a", "b"}

    def test_sort_by_type_then_id(self):
        items = [
            _artifact("z", "worksheet"),
            _artifact("a", "lesson"),
            _artifact("m", "worksheet"),
            _artifact("b", "lesson"),
        ]
        result = stable_merge_artifact_references([], items)
        keys = [(r["artifact_type"], r["document_id"]) for r in result]
        assert keys == sorted(keys)

    def test_permutation_property_all_arrivals_identical(self):
        """Core property: any arrival order → identical merged result."""
        section_artifacts = [
            _artifact("s1", "lesson"),
            _artifact("s2", "worksheet"),
            _artifact("s3", "quiz"),
            _artifact("s4", "recap"),
        ]
        # Simulate 4 parallel Send branches completing in every possible order.
        canonical: list[dict[str, object]] | None = None
        for perm in itertools.permutations(section_artifacts):
            state: list[dict[str, object]] = []
            for artifact in perm:
                state = stable_merge_artifact_references(state, [artifact])
            if canonical is None:
                canonical = state
            else:
                assert state == canonical, (
                    f"Non-deterministic merge for permutation {[a['document_id'] for a in perm]}"
                )

    def test_permutation_with_concurrent_batch_writes(self):
        """Batches arriving in different orders must also merge identically."""
        batch_a = [_artifact("a1", "lesson"), _artifact("a2", "worksheet")]
        batch_b = [_artifact("b1", "quiz"), _artifact("b2", "recap")]

        result_ab = stable_merge_artifact_references(
            stable_merge_artifact_references([], batch_a), batch_b
        )
        result_ba = stable_merge_artifact_references(
            stable_merge_artifact_references([], batch_b), batch_a
        )
        assert result_ab == result_ba

    def test_none_inputs_treated_as_empty(self):
        a = _artifact("a")
        result = stable_merge_artifact_references(None, [a])  # type: ignore[arg-type]
        assert result == [a]

        result2 = stable_merge_artifact_references([a], None)  # type: ignore[arg-type]
        assert result2 == [a]

    def test_missing_document_id_collapses_to_one_shared_key(self):
        """No fallback key exists (unlike the old artifact_id-or-id scheme) --
        references missing document_id all merge under the same empty-string
        key, so only the last one survives. Callers must always populate
        document_id; this documents the real behavior rather than a
        speculative fallback."""
        first = {"artifact_type": "lesson", "title": "first"}
        second = {"artifact_type": "lesson", "title": "second"}
        result = stable_merge_artifact_references([], [first, second])
        assert len(result) == 1
        assert result[0]["title"] == "second"

    def test_idempotent_reapplication(self):
        items = [_artifact("a"), _artifact("b")]
        once = stable_merge_artifact_references([], items)
        twice = stable_merge_artifact_references(once, items)
        assert once == twice


class TestStableMergeFiles:
    def test_deduplicates_and_sorts(self):
        result = stable_merge_files(["c.html", "a.html"], ["b.html", "a.html"])
        assert result == ["a.html", "b.html", "c.html"]

    def test_empty_inputs(self):
        assert stable_merge_files([], []) == []
        assert stable_merge_files(["a.html"], []) == ["a.html"]
        assert stable_merge_files([], ["a.html"]) == ["a.html"]

    def test_permutation_property(self):
        files = ["c.html", "a.html", "b.html"]
        for perm in itertools.permutations(files):
            state: list[str] = []
            for f in perm:
                state = stable_merge_files(state, [f])
            assert state == ["a.html", "b.html", "c.html"]

    def test_none_treated_as_empty(self):
        result = stable_merge_files(None, ["a.html"])  # type: ignore[arg-type]
        assert result == ["a.html"]


class TestStableMergeWorkflowStates:
    def test_new_overwrites_prev_by_workflow_id(self):
        old = _workflow_state("quiz", "quiz", "running")
        new = {**old, "status": "passed"}

        result = stable_merge_workflow_states([old], [new])

        assert result == [new]

    def test_falls_back_to_artifact_id_when_workflow_id_missing(self):
        old = {"artifact_id": "quiz", "artifact_type": "quiz", "status": "running"}
        new = {"artifact_id": "quiz", "artifact_type": "quiz", "status": "failed"}

        result = stable_merge_workflow_states([old], [new])

        assert result == [new]

    def test_permutation_property_all_arrivals_identical(self):
        states = [
            _workflow_state("lesson", "lesson"),
            _workflow_state("worksheet", "worksheet"),
            _workflow_state("quiz", "quiz"),
            _workflow_state("recap", "recap"),
        ]
        canonical: list[dict[str, object]] | None = None

        for perm in itertools.permutations(states):
            merged: list[dict[str, object]] = []
            for state in perm:
                merged = stable_merge_workflow_states(merged, [state])
            if canonical is None:
                canonical = merged
            else:
                assert merged == canonical

    def test_idempotent_reapplication(self):
        states = [_workflow_state("lesson"), _workflow_state("quiz", "quiz")]

        once = stable_merge_workflow_states([], states)
        twice = stable_merge_workflow_states(once, states)

        assert once == twice

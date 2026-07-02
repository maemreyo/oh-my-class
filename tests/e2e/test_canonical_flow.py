"""Canonical-flow conformance — testing/008.

Each test drives a feature end-to-end through the REAL graph via the harness. A
passing test means the runtime chain is genuinely wired; an xfail means the audit
found it dark and it is a resurrection target (the xfail flips loudly to a failure
when the feature is wired, forcing the marker to be removed).
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from packages.agents.config.features import reset_features
from tests.e2e.canonical_flow import (
    run_teaching_pack_flow,
    single_lesson_start_state,
    vocabulary_batch_start_state,
)


@dataclass
class _Bundle:
    readiness: str = "passed"


@dataclass
class _Result:
    verdict: str = "passed"


def _passing_vocab_stages():
    """Deterministic vocab stages so the flow exercises the real graph, not the LLM."""
    from packages.agents.teaching_pack.vocabulary_batch_orchestrator import VocabularyBatchStages

    async def gather(cluster, snapshot_hash, run_id):
        return {"cluster_id": cluster.cluster_id}

    async def ground(request, run_id):
        return _Bundle()

    async def synthesize(cluster, bundle, run_id):
        return {"anchor": cluster.cluster_id}

    async def make_practice(anchor, run_id):
        return {"practice": True}

    def evaluate(anchor, practice):
        return _Result()

    return VocabularyBatchStages(gather, ground, synthesize, make_practice, evaluate)


@pytest.mark.anyio
async def test_single_lesson_pack_flows_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    """The single-lesson pack is genuinely wired (audit: REAL) — assert the chain runs."""
    result = await run_teaching_pack_flow(
        monkeypatch,
        single_lesson_start_state(),
        interrupt_before=["render_quality"],
    )

    # Every artifact type crossed the LLM boundary — the chain executed, not a fixture.
    assert result.content_creator_calls == ["lesson", "quiz", "recap"]
    final = result.final_state
    assert final["artifact_fanout_complete"] is True
    assert [a["artifact_type"] for a in final["artifacts"]] == ["lesson", "quiz", "recap"]
    assert {s["status"] for s in final["artifact_workflow_states"]} == {"passed"}


@pytest.mark.anyio
async def test_vocabulary_batch_flow_produces_clusters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Phase 2 (resurrected): the vocab_batch chain moves clusters past 'queued'.

    Was xfail while the orchestrator was inert (audit 2026-07-01). Now the real graph
    routes into the chain; stages are stubbed deterministically so the flow exercises
    wiring, not the LLM.
    """
    monkeypatch.setenv("FEATURE_VOCABULARY_BATCH_V1", "true")
    reset_features()
    monkeypatch.setattr(
        "packages.agents.teaching_pack.vocabulary_batch_orchestrator.default_stages",
        _passing_vocab_stages,
    )
    try:
        result = await run_teaching_pack_flow(
            monkeypatch,
            vocabulary_batch_start_state(),
            interrupt_before=["render_quality"],
        )
        workflows = result.final_state["vocabulary_cluster_workflows"]
        assert isinstance(workflows, list) and workflows
        statuses = {str(wf["status"]) for wf in workflows}
        assert statuses == {"passed"}, (
            "vocabulary_batch chain should carry the cluster through to 'passed'"
        )
    finally:
        reset_features()

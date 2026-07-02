"""Deterministic tests for the vocabulary-batch async chain (no LLM/network).

Injects fake stages and asserts the orchestrator walks the state machine
queued -> grounding -> synthesizing -> practice_generating -> validating -> passed,
and fails closed on stage errors / gate verdicts. This is the chain the audit found
missing (orchestrator previously stopped at "queued").
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from packages.agents.teaching_pack.vocabulary_batch_orchestrator import (
    VocabularyBatchStages,
    run_vocabulary_batch_orchestrator,
)


@dataclass
class _Bundle:
    readiness: str


@dataclass
class _Result:
    verdict: str


def _stages(*, readiness: str = "passed", verdict: str = "passed", fail_stage: str | None = None) -> VocabularyBatchStages:
    async def gather(cluster, snapshot_hash, run_id):
        if fail_stage == "gather":
            raise RuntimeError("gather boom")
        return {"cluster_id": cluster.cluster_id}

    async def ground(request, run_id):
        if fail_stage == "ground":
            raise RuntimeError("ground boom")
        return _Bundle(readiness)

    async def synthesize(cluster, bundle, run_id):
        if fail_stage == "synthesize":
            raise RuntimeError("synth boom")
        return {"anchor": cluster.cluster_id}

    async def make_practice(anchor, run_id):
        if fail_stage == "practice":
            raise RuntimeError("practice boom")
        return {"practice": True}

    def evaluate(anchor, practice):
        return _Result(verdict)

    return VocabularyBatchStages(gather, ground, synthesize, make_practice, evaluate)


def _state(cluster_count: int = 1) -> dict[str, object]:
    clusters = [
        {
            "cluster_id": f"c{index}",
            "terms": ["affect", "effect"],
            "raw_input_span": "affect / effect",
            "confidence": 0.9,
        }
        for index in range(cluster_count)
    ]
    return {
        "run_id": "run-chain",
        "input_normalization_report": {
            "report_id": "report-1",
            "ready_clusters": clusters,
            "parse_confidence": 0.9,
        },
    }


def _statuses(result: dict) -> list[str]:
    return [str(wf["status"]) for wf in result["vocabulary_cluster_workflows"]]


@pytest.mark.anyio
async def test_chain_moves_cluster_to_passed() -> None:
    result = await run_vocabulary_batch_orchestrator(_state(), stages=_stages(verdict="passed"))
    assert _statuses(result) == ["passed"]


@pytest.mark.anyio
async def test_grounding_needs_review_stops_chain() -> None:
    result = await run_vocabulary_batch_orchestrator(_state(), stages=_stages(readiness="needs_review"))
    assert _statuses(result) == ["needs_review"]


@pytest.mark.anyio
async def test_gate_failed_verdict_fails_cluster() -> None:
    result = await run_vocabulary_batch_orchestrator(_state(), stages=_stages(verdict="failed"))
    assert _statuses(result) == ["failed"]


@pytest.mark.anyio
async def test_stage_exception_fails_closed_with_error() -> None:
    result = await run_vocabulary_batch_orchestrator(_state(), stages=_stages(fail_stage="synthesize"))
    workflow = result["vocabulary_cluster_workflows"][0]
    assert workflow["status"] == "failed"
    assert "synth boom" in str(workflow["last_error"])


@pytest.mark.anyio
async def test_passed_cluster_persists_produced_content() -> None:
    result = await run_vocabulary_batch_orchestrator(_state(), stages=_stages(verdict="passed"))
    content = result["vocabulary_cluster_content"]
    assert len(content) == 1
    assert content[0]["cluster_id"] == "c0"
    assert content[0]["anchor"] == {"anchor": "c0"}
    assert content[0]["practice"] == {"practice": True}
    assert content[0]["quality_verdict"] == "passed"


@pytest.mark.anyio
async def test_failed_cluster_persists_no_content() -> None:
    result = await run_vocabulary_batch_orchestrator(_state(), stages=_stages(verdict="failed"))
    assert result["vocabulary_cluster_content"] == []


@pytest.mark.anyio
async def test_all_clusters_processed_and_counted() -> None:
    result = await run_vocabulary_batch_orchestrator(_state(3), stages=_stages())
    assert _statuses(result) == ["passed", "passed", "passed"]
    assert result["vocabulary_batch_progress"]["status_counts"]["passed"] == 3

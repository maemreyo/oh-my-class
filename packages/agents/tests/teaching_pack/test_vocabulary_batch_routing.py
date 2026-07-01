from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_vocabulary_batch_mode_uses_vocabulary_orchestrator(monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.agents.config.features import reset_features

    monkeypatch.setenv("FEATURE_VOCABULARY_BATCH_V1", "true")
    reset_features()
    from packages.agents.teaching_pack.nodes import _artifact_workflow

    state = await _artifact_workflow({
        "run_id": "run-vocab",
        "contract": {"mode": "vocabulary_batch"},
        "input_normalization_report": {
            "report_id": "norm-1",
            "ready_clusters": [{
                "cluster_id": "cluster-1",
                "terms": ["fare", "ticket"],
                "raw_input_span": "fare / ticket",
                "confidence": 0.9,
            }],
            "ambiguous_clusters": [],
            "parse_confidence": 0.9,
        },
    })

    assert state["vocabulary_batch_progress"]["total_clusters"] == 1
    assert state["vocabulary_cluster_workflows"][0]["status"] == "queued"
    assert "artifacts" not in state
    reset_features()


@pytest.mark.asyncio
async def test_vocabulary_batch_feature_flag_off_rejects_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.agents.config.features import reset_features
    from packages.agents.teaching_pack.nodes import _artifact_workflow

    monkeypatch.setenv("FEATURE_VOCABULARY_BATCH_V1", "false")
    reset_features()

    with pytest.raises(RuntimeError, match="FEATURE_VOCABULARY_BATCH_V1"):
        await _artifact_workflow({
            "run_id": "run-vocab-off",
            "contract": {"mode": "vocabulary_batch"},
            "input_normalization_report": {
                "report_id": "norm-1",
                "ready_clusters": [{
                    "cluster_id": "cluster-1",
                    "terms": ["fare", "ticket"],
                    "raw_input_span": "fare / ticket",
                    "confidence": 0.9,
                }],
                "ambiguous_clusters": [],
                "parse_confidence": 0.9,
            },
        })

    reset_features()


def test_generate_pack_is_not_vocabulary_batch_mode() -> None:
    from packages.agents.teaching_pack.vocabulary_batch_orchestrator import is_vocabulary_batch_mode

    assert is_vocabulary_batch_mode({"contract": {"mode": "generate_pack"}}) is False
    assert is_vocabulary_batch_mode({"contract": {"mode": "vocabulary_batch"}}) is True

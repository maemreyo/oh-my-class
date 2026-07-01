from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.vocabulary_cluster_workflow import (
    VocabularyClusterEvidenceEntry,
    VocabularyClusterWorkflow,
    apply_cluster_transition,
)


def test_cluster_workflow_validates_full_persistence_shape() -> None:
    workflow = VocabularyClusterWorkflow(
        workflow_id="workflow-1",
        cluster_id="cluster-1",
        run_id="run-1",
        normalized_input=("travel", "journey", "trip"),
        raw_input_span="travel / journey / trip",
        status="needs_review",
        attempts=2,
        review_status="needs_review",
        export_refs={"teacher_review_html": "clusters/cluster-1/review.html"},
        snapshot_hash="a" * 64,
        last_error=None,
    )

    assert workflow.cluster_id == "cluster-1"
    assert workflow.normalized_input == ("travel", "journey", "trip")
    assert workflow.export_refs["teacher_review_html"].endswith("review.html")


def test_cluster_lifecycle_accepts_forward_transition() -> None:
    next_status = apply_cluster_transition("queued", "grounding")

    assert next_status == "grounding"


def test_cluster_lifecycle_rejects_illegal_transition() -> None:
    with pytest.raises(ValueError, match="Illegal vocabulary cluster transition"):
        apply_cluster_transition("failed", "synthesizing")


def test_evidence_entry_rejects_forbidden_provider_payload() -> None:
    with pytest.raises(ValidationError):
        VocabularyClusterEvidenceEntry(
            evidence_id="evidence-1",
            workflow_id="workflow-1",
            cluster_id="cluster-1",
            run_id="run-1",
            sequence=1,
            event_type="grounding_sources",
            payload={"provider_raw_response": "hidden chain"},
        )


def test_evidence_entry_accepts_structured_safe_payload() -> None:
    entry = VocabularyClusterEvidenceEntry(
        evidence_id="evidence-1",
        workflow_id="workflow-1",
        cluster_id="cluster-1",
        run_id="run-1",
        sequence=1,
        event_type="grounding_sources",
        payload={"source_ids": ["cambridge-travel", "oxford-journey"]},
    )

    assert entry.payload == {"source_ids": ["cambridge-travel", "oxford-journey"]}

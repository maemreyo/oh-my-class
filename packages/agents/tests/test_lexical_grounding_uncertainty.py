from __future__ import annotations

import pytest

from common.contracts.vocabulary_batch import (
    LexicalGroundingRequest,
    LexicalGroundingSourceEvidence,
    NormalizedVocabularyCluster,
)


def _request_with_single_source() -> LexicalGroundingRequest:
    return LexicalGroundingRequest(
        cluster=NormalizedVocabularyCluster(
            cluster_id="bank-cluster",
            terms=("bank", "shore"),
            raw_input_span="bank / shore",
            title_hint=None,
            notes=(),
            confidence=0.72,
        ),
        source_evidence=(LexicalGroundingSourceEvidence(
            source_id="single-source",
            title="One dictionary source",
            url=None,
            excerpt="Bank can mean land beside a river.",
            verification_status="VERIFIED",
        ),),
        cluster_snapshot_hash="snapshot-bank",
    )


@pytest.mark.asyncio
async def test_insufficient_evidence_yields_needs_review_uncertainty_without_llm() -> None:
    from packages.agents.sub_agents.researcher.lexical_grounding import lexical_grounding_profile

    bundle = await lexical_grounding_profile(_request_with_single_source(), run_id="run-vocab-2")

    assert bundle.readiness == "needs_review"
    assert bundle.confidence <= 0.6
    assert bundle.uncertainty_flags == ("insufficient_verified_sources",)
    assert bundle.teacher_source_notes == ("Only 1 verified source(s) available; teacher review is required.",)


def test_contract_rejects_confident_bundle_with_insufficient_sources() -> None:
    from pydantic import ValidationError

    from common.contracts.vocabulary_batch import LexicalGroundingBundle, LexicalGroundingCacheKeys

    with pytest.raises(ValidationError):
        LexicalGroundingBundle(
            bundle_id="bad-grounding",
            cluster_id="bank-cluster",
            terms=("bank", "shore"),
            source_ids=("single-source",),
            term_definitions=(),
            usage_constraints=(),
            common_confusions=("bank can confuse river edge and finance senses",),
            example_pairs=(),
            distinction_notes=("Bank is more specific than shore for river edges.",),
            teacher_source_notes=("Only one source.",),
            student_projection_fields=("distinction_notes",),
            confidence=0.9,
            readiness="passed",
            cache_keys=LexicalGroundingCacheKeys(
                cluster_snapshot_key="lexical-grounding:cluster:snapshot-bank",
                term_distinction_key="lexical-grounding:terms:bank|shore",
            ),
            uncertainty_flags=(),
        )

from __future__ import annotations

import contextlib
import json
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from common.contracts.vocabulary_batch import (
    LexicalGroundingBundle,
    LexicalGroundingCacheKeys,
    LexicalTermDefinition,
    LexicalUsageConstraint,
    NormalizedVocabularyCluster,
    SemanticAnchorCluster,
)


def _cluster() -> NormalizedVocabularyCluster:
    return NormalizedVocabularyCluster(
        cluster_id="fare-ticket-fee",
        terms=("fare", "ticket", "fee"),
        raw_input_span="fare / ticket / fee",
        title_hint="Payment and access words",
        notes=(),
        confidence=0.93,
    )


def _grounding() -> LexicalGroundingBundle:
    return LexicalGroundingBundle(
        bundle_id="ground-fare-ticket-fee",
        cluster_id="fare-ticket-fee",
        terms=("fare", "ticket", "fee"),
        source_ids=("cambridge-fare", "oxford-ticket"),
        term_definitions=(
            LexicalTermDefinition(
                term="fare",
                definition="money paid to travel by bus, train, taxi, or plane",
                source_ids=("cambridge-fare",),
                confidence=0.92,
            ),
            LexicalTermDefinition(
                term="ticket",
                definition="a printed or digital proof that lets you enter or travel",
                source_ids=("oxford-ticket",),
                confidence=0.9,
            ),
        ),
        usage_constraints=(
            LexicalUsageConstraint(
                term="fee",
                constraint="Use for service, membership, or professional payments, not usually transport price.",
                source_ids=("cambridge-fare", "oxford-ticket"),
                confidence=0.88,
            ),
        ),
        common_confusions=("fare is the transport price; ticket is the proof or pass",),
        example_pairs=(),
        distinction_notes=("Fare is money for transport; ticket is access proof; fee is service payment.",),
        teacher_source_notes=("Dictionary sources support fare as transport price.",),
        student_projection_fields=("term_definitions", "usage_constraints", "distinction_notes"),
        confidence=0.9,
        readiness="passed",
        cache_keys=LexicalGroundingCacheKeys(
            cluster_snapshot_key="lexical-grounding:cluster:snapshot-fare",
            term_distinction_key="lexical-grounding:terms:fare|fee|ticket",
        ),
        uncertainty_flags=(),
    )


def _valid_cluster_json() -> str:
    return json.dumps({
        "cluster_id": "fare-ticket-fee",
        "title": "Payment and access words",
        "title_confidence": 0.91,
        "raw_input_span": "fare / ticket / fee",
        "terms": ["fare", "ticket", "fee"],
        "anchors": [
            {
                "word": "fare",
                "impression_vi": "tiền đi xe",
                "core_trigger_en": "transport price",
                "visual_cue_vi": "tay đưa tiền cho tài xế xe buýt",
                "semantic_chain": ["fare", "transport", "pay", "ride"],
                "example_en": "The bus fare is two dollars.",
                "contrast_note_vi": "Fare là số tiền đi lại, không phải tờ vé.",
                "student_explanation_vi": "Fare là tiền phải trả để đi xe, tàu hoặc máy bay.",
                "teacher_script_vi": "Neo fare vào cảnh trả tiền trước khi lên xe buýt.",
                "edge_cases": ["airfare"],
                "source_notes": ["Cambridge: fare is money paid for a journey."],
            }
        ],
        "contrast_notes": ["Fare is the transport price; ticket is the proof."],
        "summary_rows": ["fare = transport price"],
        "review_status": "passed",
        "warnings": [],
        "teacher_source_notes": ["Dictionary sources support transport-price nuance."],
    })


@contextlib.contextmanager
def _patch_content_llm(responses: list[str]) -> Generator[AsyncMock]:
    mock_llm = AsyncMock(side_effect=responses)
    with patch("packages.agents.llm.complete_json_chat", mock_llm):
        yield mock_llm


@pytest.mark.asyncio
async def test_semantic_anchor_synthesis_produces_valid_cluster() -> None:
    from packages.agents.sub_agents.content_creator.semantic_anchor_synthesis import synthesize_semantic_anchor_cluster

    with _patch_content_llm([_valid_cluster_json()]) as mock_llm:
        cluster = await synthesize_semantic_anchor_cluster(_cluster(), _grounding(), run_id="run-anchor-1")

    assert isinstance(cluster, SemanticAnchorCluster)
    assert cluster.cluster_id == "fare-ticket-fee"
    assert cluster.anchors[0].impression_vi == "tiền đi xe"
    assert cluster.anchors[0].core_trigger_en == "transport price"
    assert cluster.anchors[0].teacher_script_vi.startswith("Neo fare")
    assert mock_llm.await_count == 1
    assert "profile:semantic_anchor_synthesis" in mock_llm.call_args.kwargs["tags"]


@pytest.mark.asyncio
async def test_semantic_anchor_synthesis_retries_with_validation_feedback() -> None:
    from packages.agents.sub_agents.content_creator.semantic_anchor_synthesis import synthesize_semantic_anchor_cluster

    invalid = json.dumps({"cluster_id": "fare-ticket-fee", "terms": ["fare", "ticket", "fee"]})
    with _patch_content_llm([invalid, _valid_cluster_json()]) as mock_llm:
        cluster = await synthesize_semantic_anchor_cluster(_cluster(), _grounding(), run_id="run-anchor-2")

    retry_prompt = mock_llm.call_args_list[1].kwargs["messages"][1]["content"]
    assert cluster.review_status == "passed"
    assert mock_llm.await_count == 2
    assert "Previous output failed SemanticAnchorCluster validation" in retry_prompt


@pytest.mark.asyncio
async def test_semantic_anchor_synthesis_fails_closed_after_retries() -> None:
    from packages.agents.sub_agents.content_creator.semantic_anchor_synthesis import (
        SemanticAnchorSynthesisFailed,
        synthesize_semantic_anchor_cluster,
    )

    invalid = json.dumps({"cluster_id": "fare-ticket-fee", "terms": ["fare", "ticket", "fee"]})
    with _patch_content_llm([invalid, invalid, invalid]):
        with pytest.raises(SemanticAnchorSynthesisFailed):
            await synthesize_semantic_anchor_cluster(_cluster(), _grounding(), run_id="run-anchor-3")

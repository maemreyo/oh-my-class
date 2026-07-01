from __future__ import annotations

import contextlib
import json
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from common.contracts.vocabulary_batch import AnchorCard, PracticeSet, SemanticAnchorCluster


def _cluster() -> SemanticAnchorCluster:
    return SemanticAnchorCluster(
        cluster_id="fare-ticket-fee",
        title="Payment and access words",
        title_confidence=0.91,
        raw_input_span="fare / ticket / fee",
        terms=("fare", "ticket", "fee"),
        anchors=(AnchorCard(
            word="fare",
            impression_vi="tiền đi xe",
            core_trigger_en="transport price",
            visual_cue_vi="tay đưa tiền cho tài xế xe buýt",
            semantic_chain=("fare", "transport", "pay", "ride"),
            example_en="The bus fare is two dollars.",
            contrast_note_vi="Fare là tiền đi lại, không phải tờ vé.",
            student_explanation_vi="Fare là tiền phải trả để đi xe, tàu hoặc máy bay.",
            teacher_script_vi="Neo fare vào cảnh trả tiền trước khi lên xe buýt.",
            edge_cases=("airfare",),
            source_notes=("Cambridge: fare is money paid for a journey.",),
        ),),
        contrast_notes=("Fare is the transport price; ticket is the proof.",),
        summary_rows=("fare = transport price",),
        review_status="passed",
        warnings=(),
        teacher_source_notes=("Dictionary sources support transport-price nuance.",),
    )


def _practice_json() -> str:
    return json.dumps({
        "practice_set_id": "practice-fare-ticket-fee",
        "cluster_id": "fare-ticket-fee",
        "items": [
            {"item_id": "item-1", "intent": "core_trigger_recall", "prompt": "Which word means money paid for a bus ride?", "answer": "fare", "rationale": "Fare is the transport price."},
            {"item_id": "item-2", "intent": "context_discrimination", "prompt": "Choose: I bought a ___ to enter the concert.", "answer": "ticket", "rationale": "Ticket is proof of access."},
            {"item_id": "item-3", "intent": "boundary_explanation", "prompt": "Explain why fee is not the best word for a bus price.", "answer": "Fee is usually for services or membership; fare is for transport.", "rationale": "The boundary is transport price versus service payment."},
            {"item_id": "item-4", "intent": "reverse_retrieval", "prompt": "transport price → ?", "answer": "fare", "rationale": "The anchor trigger points back to fare."}
        ]
    })


@contextlib.contextmanager
def _patch_llm(responses: list[str]) -> Generator[AsyncMock]:
    mock_llm = AsyncMock(side_effect=responses)
    with patch("packages.agents.llm.complete_json_chat", mock_llm):
        yield mock_llm


@pytest.mark.asyncio
async def test_semantic_anchor_practice_generates_all_four_intents() -> None:
    from packages.agents.sub_agents.practice_generator.semantic_anchor import (
        PracticeGenerationRequest,
        generate_semantic_anchor_practice,
    )

    request = PracticeGenerationRequest(
        cluster=_cluster(),
        grade_band="Grade 6",
        target_cefr="A2",
        exam_target="classroom review",
    )
    with _patch_llm([_practice_json()]) as mock_llm:
        practice = await generate_semantic_anchor_practice(request, run_id="run-practice-1")

    assert isinstance(practice, PracticeSet)
    assert {item.intent for item in practice.items} == {
        "core_trigger_recall",
        "context_discrimination",
        "boundary_explanation",
        "reverse_retrieval",
    }
    user_prompt = mock_llm.call_args.kwargs["messages"][1]["content"]
    assert "Grade 6" in user_prompt
    assert "A2" in user_prompt
    assert "classroom review" in user_prompt


@pytest.mark.asyncio
async def test_practice_regeneration_does_not_mutate_cluster() -> None:
    from packages.agents.sub_agents.practice_generator.semantic_anchor import (
        PracticeGenerationRequest,
        generate_semantic_anchor_practice,
    )

    cluster = _cluster()
    before = cluster.model_dump_json()
    with _patch_llm([_practice_json(), _practice_json()]):
        first = await generate_semantic_anchor_practice(PracticeGenerationRequest(cluster=cluster), run_id="run-practice-2")
        second = await generate_semantic_anchor_practice(PracticeGenerationRequest(cluster=cluster), run_id="run-practice-3")

    assert cluster.model_dump_json() == before
    assert first.practice_set_id == second.practice_set_id

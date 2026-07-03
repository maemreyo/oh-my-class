from __future__ import annotations

import contextlib
import json
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from common.contracts.vocabulary_batch import (
    LexicalGroundingBundle,
    LexicalGroundingRequest,
    LexicalGroundingSourceEvidence,
    NormalizedVocabularyCluster,
)
from packages.agents.teaching_pack.stages import StageEnum


def _travel_request() -> LexicalGroundingRequest:
    return LexicalGroundingRequest(
        cluster=NormalizedVocabularyCluster(
            cluster_id="travel-words",
            terms=("travel", "journey", "trip", "voyage", "excursion"),
            raw_input_span="travel / journey / trip / voyage / excursion",
            title_hint="Travel words",
            notes=(),
            confidence=0.96,
        ),
        source_evidence=(
            LexicalGroundingSourceEvidence(
                source_id="cambridge-travel",
                title="Cambridge Dictionary travel words",
                url="https://dictionary.cambridge.org/example",
                excerpt="Voyage is a long journey, especially by ship or in space.",
                verification_status="VERIFIED",
            ),
            LexicalGroundingSourceEvidence(
                source_id="oxford-trip",
                title="Oxford learner examples",
                url="https://www.oxfordlearnersdictionaries.com/example",
                excerpt="A trip is a journey to a place and back again, often short.",
                verification_status="VERIFIED",
            ),
        ),
        cluster_snapshot_hash="snapshot-a",
    )


def _grounding_json() -> str:
    return json.dumps({
        "bundle_id": "ground-travel-words",
        "cluster_id": "travel-words",
        "terms": ["travel", "journey", "trip", "voyage", "excursion"],
        "source_ids": ["cambridge-travel", "oxford-trip"],
        "term_definitions": [
            {"term": "travel", "definition": "go from one place to another", "source_ids": ["cambridge-travel"], "confidence": 0.86},
            {"term": "voyage", "definition": "a long journey by sea or in space", "source_ids": ["cambridge-travel"], "confidence": 0.91},
        ],
        "usage_constraints": [
            {"term": "voyage", "constraint": "Use for long or formal sea/space journeys.", "source_ids": ["cambridge-travel"], "confidence": 0.9}
        ],
        "common_confusions": ["trip is often shorter than journey; voyage is more formal or long"],
        "example_pairs": [
            {
                "term": "voyage",
                "example": "The voyage across the ocean took months.",
                "counterexample": "The trip to the shop took ten minutes.",
                "contrast_note": "The counterexample is too short and ordinary for voyage.",
                "source_ids": ["cambridge-travel", "oxford-trip"],
            }
        ],
        "distinction_notes": ["Voyage carries long/formal travel; trip can be short and return-based."],
        "teacher_source_notes": ["Cambridge supports voyage as long sea/space journey."],
        "student_projection_fields": ["term_definitions", "usage_constraints", "common_confusions", "example_pairs", "distinction_notes"],
        "confidence": 0.88,
        "readiness": "passed",
        "cache_keys": {
            "cluster_snapshot_key": "lexical-grounding:cluster:snapshot-a",
            "term_distinction_key": "lexical-grounding:terms:excursion|journey|travel|trip|voyage",
        },
        "uncertainty_flags": [],
    })


@contextlib.contextmanager
def _patch_llm(return_value: str) -> Generator[AsyncMock]:
    mock_llm = AsyncMock(return_value=return_value)
    with patch("packages.agents.llm.complete_json_chat", mock_llm):
        yield mock_llm


@pytest.mark.asyncio
async def test_lexical_grounding_profile_returns_source_notes_and_confidence() -> None:
    from packages.agents.sub_agents.researcher.lexical_grounding import lexical_grounding_profile

    with _patch_llm(_grounding_json()) as mock_llm:
        bundle = await lexical_grounding_profile(_travel_request(), run_id="run-vocab-1")

    assert isinstance(bundle, LexicalGroundingBundle)
    assert bundle.cluster_id == "travel-words"
    assert bundle.confidence == pytest.approx(0.88)
    assert bundle.teacher_source_notes == ("Cambridge supports voyage as long sea/space journey.",)
    assert "teacher_source_notes" not in bundle.student_projection_fields
    assert bundle.cache_keys.term_distinction_key.endswith("excursion|journey|travel|trip|voyage")
    assert mock_llm.call_args.kwargs["tags"] == [
        "agent:researcher",
        "step:5",
        "stage:post_blueprint_research",
        "run:run-vocab-1",
        "attempt:1",
        "profile:lexical_grounding",
        "pipeline:oh-my-class",
    ]


@pytest.mark.asyncio
async def test_ordinary_post_blueprint_research_prompt_is_unchanged_for_generate_pack() -> None:
    from packages.agents.sub_agents.researcher.nodes import researcher_node

    valid_bundle = json.dumps({
        "topic": "Photosynthesis",
        "sources": [
            {"title": "Source 1", "credibility_score": 0.9, "verification_status": "VERIFIED"},
            {"title": "Source 2", "credibility_score": 0.8, "verification_status": "VERIFIED"},
        ],
        "key_findings": ["Plants convert sunlight to glucose"],
        "research_policy": "standard",
    })
    with contextlib.ExitStack() as stack:
        mock_llm = stack.enter_context(patch("packages.agents.llm.complete_json_chat", AsyncMock(return_value=valid_bundle)))
        stack.enter_context(patch("packages.agents.tools.web_search.web_search", AsyncMock(return_value=[
            {"title": "Source 1", "url": "https://example.edu/one", "snippet": "Alpha"},
            {"title": "Source 2", "url": "https://example.edu/two", "snippet": "Beta"},
        ])))
        stack.enter_context(patch("packages.agents.sub_agents.researcher.tools.web_fetch", AsyncMock(return_value="Fetched page content.")))
        result = await researcher_node({
            "lesson_plan": {"topic": "Photosynthesis", "learning_objectives": []},
            "research_policy": "standard",
            "run_id": "run-generate-pack",
            "current_step": StageEnum.POST_BLUEPRINT_RESEARCH,
            "research_bundle": None,
        })

    user_prompt = mock_llm.call_args.kwargs["messages"][1]["content"]
    assert "research_bundle" in result
    assert "Research topic: Photosynthesis" in user_prompt
    assert "lexical_grounding" not in user_prompt
    assert "teacher_source_notes" not in user_prompt

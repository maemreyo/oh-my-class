"""Canonical-flow harness — testing/008.

Runs a feature end-to-end through the **real** teaching-pack graph
(``build_teaching_pack_graph`` + ``ainvoke``), stubbing ONLY the LLM boundary
(``content_creator_node``). This is the truth-detector for the false-green pattern
found in the 2026-07-01 audit: it fails when a feature's runtime chain is *dark*
(built but never wired), which per-unit fixture tests structurally cannot catch —
they hand-construct the intermediate contracts instead of running the prior stage.

Contract: seed a start state (helpers below), then ``await run_teaching_pack_flow``.
The harness records every artifact type that crossed the LLM boundary, so a test can
assert the chain actually executed rather than trusting a fixture.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import pytest

from packages.agents.teaching_pack.graph import build_teaching_pack_graph
from packages.agents.teaching_pack.nodes import TeachingPackState

CONTENT_CREATOR_TARGET = (
    "packages.agents.teaching_pack.generate_one_artifact.content_creator_node"
)

# Stages completed before artifact generation, so a seeded state flows straight into
# the part under test without re-running research/planning.
PRE_ARTIFACT_STAGES: tuple[str, ...] = (
    "setup_contract",
    "triage",
    "preplanning_search",
    "planning_blueprint",
    "post_blueprint_research",
)


def default_artifact(artifact_type: str) -> dict[str, object]:
    return {
        "artifact_id": f"{artifact_type}-1",
        "artifact_type": artifact_type,
        "theme": "default",
        "title": f"{artifact_type.title()} Artifact",
        "sections": [{"title": "Intro", "content": "Use unit fractions."}],
        "metadata": {},
        "accessibility": {"language": "en"},
    }


@dataclass
class CanonicalFlowResult:
    final_state: dict[str, object]
    content_creator_calls: list[str] = field(default_factory=list)


async def run_teaching_pack_flow(
    monkeypatch: pytest.MonkeyPatch,
    start_state: TeachingPackState,
    *,
    interrupt_before: list[str] | None = None,
    content_creator: Callable[[dict[str, object]], Awaitable[dict[str, object]]] | None = None,
) -> CanonicalFlowResult:
    """Drive the real graph to ``interrupt_before``, stubbing the LLM boundary only."""
    calls: list[str] = []

    async def default_stub(state: dict[str, object]) -> dict[str, object]:
        artifact_types = state["artifact_types"]
        assert isinstance(artifact_types, list)
        artifact_type = str(artifact_types[0])
        calls.append(artifact_type)
        return {"artifacts": [default_artifact(artifact_type)]}

    monkeypatch.setattr(CONTENT_CREATOR_TARGET, content_creator or default_stub)
    graph = build_teaching_pack_graph(interrupt_before=list(interrupt_before or []))
    final = await graph.ainvoke(start_state)
    return CanonicalFlowResult(final_state=dict(final), content_creator_calls=calls)


def single_lesson_start_state(
    *,
    run_id: str = "run-canonical-single-lesson",
    topic: str = "Fractions",
    artifact_types: list[str] | None = None,
) -> TeachingPackState:
    return {
        "run_id": run_id,
        "contract": {"topic": topic, "theme": "default"},
        "lesson_plan": {"topic": topic},
        "research_brief": {"sources": []},
        "artifact_types": artifact_types or ["lesson", "quiz", "recap"],
        "completed_stages": list(PRE_ARTIFACT_STAGES),
    }


def vocabulary_batch_start_state(
    *,
    run_id: str = "run-canonical-vocab-batch",
) -> TeachingPackState:
    return {
        "run_id": run_id,
        "contract": {"topic": "Confusing words", "theme": "default", "mode": "vocabulary_batch"},
        "lesson_plan": {"topic": "Confusing words"},
        "research_brief": {"sources": []},
        "artifact_types": ["lesson"],
        "completed_stages": list(PRE_ARTIFACT_STAGES),
        "input_normalization_report": {
            "report_id": "report-canonical-1",
            "ready_clusters": [
                {
                    "cluster_id": "cluster-affect-effect",
                    "terms": ["affect", "effect"],
                    "raw_input_span": "affect / effect",
                    "confidence": 0.9,
                }
            ],
            "parse_confidence": 0.9,
        },
    }

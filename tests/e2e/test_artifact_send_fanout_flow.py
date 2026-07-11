from __future__ import annotations

import pytest

from common.contracts.slide_deck import SlideDeckData
from packages.agents.teaching_pack.graph import build_teaching_pack_graph
from packages.agents.teaching_pack.nodes import TeachingPackState
from packages.agents.teaching_pack.stages import StageEnum


def _minimal_slide_deck_data() -> dict[str, object]:
    """The smallest deck that satisfies `SlideDeckData` -- #463's V2 mapper
    requires `metadata.slide_deck_data` to actually validate against the
    contract (not just be present), unlike the pre-#463 path this fixture
    predates."""
    surface = {"mode": "presentation", "export_format": "html"}
    return SlideDeckData.model_validate({
        "deck_id": "deck-1",
        "title": "Fractions Deck",
        "locale": "en",
        "theme": "default",
        "surfaces": {"student": surface, "teacher": surface, "print": surface},
        "slides": [{
            "slide_id": "slide-1",
            "title": "Intro",
            "layout": "content",
            "progression": {"step_index": 1, "reveal_policy": "all_at_once"},
            "blocks": [{
                "block_id": "block-1",
                "block_type": "paragraph",
                "body": "Use unit fractions.",
            }],
        }],
        "accessibility": {"reading_level": "grade_5", "language": "en"},
        "media_policy": {"default_tier": "packaged", "online_optional_allowed": False, "fallback_required": True},
    }).model_dump(mode="json")


def _artifact(artifact_type: str) -> dict[str, object]:
    artifact: dict[str, object] = {
        "artifact_id": f"{artifact_type}-1",
        "artifact_type": artifact_type,
        "theme": "default",
        "title": f"{artifact_type.title()} Artifact",
        "sections": [{"title": "Intro", "content": "Use unit fractions."}],
        "metadata": {},
        "accessibility": {"language": "en"},
    }
    if artifact_type in {"quiz", "drill"}:
        artifact["sections"] = [{
            "title": "Questions",
            "components": [{
                "type": "question_card",
                "id": "quiz-1",
                "text": "Which fraction equals one half?",
                "options": {"A": "2/4", "B": "1/3"},
                "answer": "A",
                "explain": "Two fourths equals one half.",
            }],
        }]
    if artifact_type == "slide_deck":
        artifact["metadata"] = {"slide_deck_data": _minimal_slide_deck_data()}
    return artifact


def _start_state() -> TeachingPackState:
    return {
        "run_id": "run-send-e2e-happy",
        "contract": {"topic": "Fractions", "theme": "default"},
        "lesson_plan": {"topic": "Fractions"},
        "research_brief": {"sources": []},
        "artifact_types": ["lesson", "worksheet", "quiz", "drill", "slide_deck"],
        "completed_stages": [
            StageEnum.SETUP_CONTRACT,
            StageEnum.TRIAGE,
            StageEnum.PREPLANNING_SEARCH,
            StageEnum.PLANNING_BLUEPRINT,
            StageEnum.POST_BLUEPRINT_RESEARCH,
        ],
    }


@pytest.mark.anyio
async def test_graph_generates_complete_pack_before_render_quality_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_get_specialist(artifact_type: str):
        def generate(_lesson_plan: dict[str, object], _research_brief: dict[str, object]) -> dict[str, object]:
            calls.append(artifact_type)
            return _artifact(artifact_type)

        return generate

    async def fake_slide_deck_artifact(payload: dict[str, object], _dependencies: list[dict[str, object]]) -> dict[str, object]:
        calls.append(str(payload["artifact_type"]))
        return _artifact("slide_deck")

    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)
    monkeypatch.setenv("TEACHING_PACK_DEFAULT_ARTIFACT_PARALLELISM", "3")
    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.get_specialist",
        fake_get_specialist,
    )
    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact._slide_deck_artifact",
        fake_slide_deck_artifact,
    )

    graph = build_teaching_pack_graph(interrupt_before=["render_quality"])
    result = await graph.ainvoke(_start_state())

    assert calls == ["lesson", "worksheet", "quiz", "drill", "slide_deck"]
    assert result["artifact_fanout_complete"] is True
    assert [reference["artifact_type"] for reference in result["artifact_references"]] == [
        "drill",
        "lesson",
        "quiz",
        "slide_deck",
        "worksheet",
    ]
    assert {state["status"] for state in result["artifact_workflow_states"]} == {"passed"}

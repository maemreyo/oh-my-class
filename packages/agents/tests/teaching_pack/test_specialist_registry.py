"""#439: registry-driven specialist dispatch reaches a real specialist, not
the universal content_creator_node placeholder, for artifact types that have one."""

from __future__ import annotations

import pytest

from packages.agents.teaching_pack.generate_one_artifact import generate_one_artifact
from packages.agents.teaching_pack.specialist_registry import SPECIALIST_REGISTRY, get_specialist


def test_recap_and_flashcard_deck_are_registered() -> None:
    assert get_specialist("recap") is not None
    assert get_specialist("flashcard_deck") is not None


def test_unregistered_artifact_type_returns_none() -> None:
    assert get_specialist("worksheet") is None


def _recap_payload() -> dict[str, object]:
    return {
        "run_id": "run-1",
        "artifact_generation_id": "gen-1",
        "artifact_type": "recap",
        "lesson_plan": {
            "topic": "Photosynthesis",
            "learning_objectives": [
                {"description": "Explain how plants convert light to energy.", "bloom_level": "understand"},
            ],
        },
        "research_brief": {"sources": []},
        "theme": "default",
        "revision_feedback": "",
        "dependency_artifact_references": [],
    }


@pytest.mark.anyio
async def test_recap_generation_never_calls_content_creator_node(monkeypatch: pytest.MonkeyPatch) -> None:
    """A queued run for `recap` must reach the real specialist -- if this test's
    patched content_creator_node is ever called, dispatch fell through to the
    universal placeholder instead."""
    called = False

    async def fake_content_creator_node(_state: dict[str, object]) -> dict[str, object]:
        nonlocal called
        called = True
        return {"artifacts": []}

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fake_content_creator_node,
    )

    result = await generate_one_artifact(_recap_payload())  # type: ignore[arg-type]

    assert called is False
    assert result["artifact_workflow_states"][0]["status"] == "passed"


@pytest.mark.anyio
async def test_recap_generation_fails_closed_with_no_grounded_content(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _recap_payload()
    payload["lesson_plan"] = {"topic": "Empty"}  # no learning_objectives at all

    async def fail_if_called(_state: dict[str, object]) -> dict[str, object]:
        raise AssertionError("must not fall through to content_creator_node")

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fail_if_called,
    )

    result = await generate_one_artifact(payload)  # type: ignore[arg-type]

    assert result["artifact_workflow_states"][0]["status"] == "failed"
    assert result["artifact_workflow_states"][0]["error_class"] == "NoGroundedConceptsError"


def test_registry_is_not_mutated_by_import_side_effects() -> None:
    """Sanity: the registry is a plain module-level dict, not rebuilt per call."""
    assert SPECIALIST_REGISTRY["recap"] is get_specialist("recap")


def _flashcard_payload() -> dict[str, object]:
    return {
        "run_id": "run-1",
        "artifact_generation_id": "gen-1",
        "artifact_type": "flashcard_deck",
        "lesson_plan": {
            "topic": "Equivalent Fractions",
            "grade_level": "Grade 5",
            "learning_objectives": [
                {"description": "Equivalent fractions represent the same value."},
            ],
        },
        "research_brief": {"sources": []},
        "theme": "default",
        "revision_feedback": "",
        "dependency_artifact_references": [],
    }


@pytest.mark.anyio
async def test_flashcard_deck_generation_never_calls_content_creator_node(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_if_called(_state: dict[str, object]) -> dict[str, object]:
        raise AssertionError("must not fall through to content_creator_node")

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fail_if_called,
    )

    result = await generate_one_artifact(_flashcard_payload())  # type: ignore[arg-type]

    assert result["artifact_workflow_states"][0]["status"] == "passed"

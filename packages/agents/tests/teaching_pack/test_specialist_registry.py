"""#439: registry-driven specialist dispatch reaches a real specialist, not
the universal content_creator_node placeholder, for artifact types that have one."""

from __future__ import annotations

import pytest

from packages.agents.teaching_pack.generate_one_artifact import generate_one_artifact
from packages.agents.teaching_pack.specialist_registry import SPECIALIST_REGISTRY, get_specialist


def test_lesson_recap_and_flashcard_deck_are_registered() -> None:
    assert get_specialist("lesson") is not None
    assert get_specialist("worksheet") is not None
    assert get_specialist("quiz") is not None
    assert get_specialist("drill") is not None
    assert get_specialist("roadmap") is not None
    assert get_specialist("reading_passage") is not None
    assert get_specialist("infographic") is not None
    assert get_specialist("exit_ticket") is not None
    assert get_specialist("recap") is not None
    assert get_specialist("flashcard_deck") is not None


def test_unregistered_artifact_type_returns_none() -> None:
    assert get_specialist("slide_deck") is None


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


def _lesson_payload() -> dict[str, object]:
    return {
        "run_id": "run-1",
        "artifact_generation_id": "gen-1",
        "artifact_type": "lesson",
        "lesson_plan": {
            "topic": "Photosynthesis",
            "duration_minutes": 45,
            "methodology": "inquiry",
            "learning_objectives": [
                {"description": "Explain how plants convert light to energy."},
            ],
            "learning_plan": {"engage": "Observe a leaf in sunlight."},
        },
        "research_brief": {"sources": []},
        "theme": "default",
        "revision_feedback": "",
        "dependency_artifact_references": [],
    }


def _worksheet_payload() -> dict[str, object]:
    payload = _lesson_payload()
    payload["artifact_type"] = "worksheet"
    return payload


def _quiz_payload() -> dict[str, object]:
    payload = _lesson_payload()
    payload["artifact_type"] = "quiz"
    return payload


def _drill_payload() -> dict[str, object]:
    payload = _lesson_payload()
    payload["artifact_type"] = "drill"
    return payload


def _roadmap_payload() -> dict[str, object]:
    payload = _lesson_payload()
    payload["artifact_type"] = "roadmap"
    return payload


def _reading_passage_payload() -> dict[str, object]:
    payload = _lesson_payload()
    payload["artifact_type"] = "reading_passage"
    payload["research_brief"] = {"sources": [{"title": "Fractions Guide", "excerpt": "Equivalent fractions represent the same value."}]}
    return payload


def _infographic_payload() -> dict[str, object]:
    payload = _lesson_payload()
    payload["artifact_type"] = "infographic"
    return payload


def _exit_ticket_payload() -> dict[str, object]:
    payload = _lesson_payload()
    payload["artifact_type"] = "exit_ticket"
    return payload


@pytest.mark.anyio
async def test_lesson_generation_never_calls_content_creator_node(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_if_called(_state: dict[str, object]) -> dict[str, object]:
        raise AssertionError("must not fall through to content_creator_node")

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fail_if_called,
    )

    result = await generate_one_artifact(_lesson_payload())  # type: ignore[arg-type]

    assert result["artifact_workflow_states"][0]["status"] == "passed"


@pytest.mark.anyio
async def test_worksheet_generation_never_calls_content_creator_node(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_if_called(_state: dict[str, object]) -> dict[str, object]:
        raise AssertionError("must not fall through to content_creator_node")

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fail_if_called,
    )

    result = await generate_one_artifact(_worksheet_payload())  # type: ignore[arg-type]

    assert result["artifact_workflow_states"][0]["status"] == "passed"


@pytest.mark.anyio
async def test_quiz_generation_never_calls_content_creator_node(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_if_called(_state: dict[str, object]) -> dict[str, object]:
        raise AssertionError("must not fall through to content_creator_node")

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fail_if_called,
    )

    result = await generate_one_artifact(_quiz_payload())  # type: ignore[arg-type]

    assert result["artifact_workflow_states"][0]["status"] == "passed"


@pytest.mark.anyio
async def test_drill_generation_never_calls_content_creator_node(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_if_called(_state: dict[str, object]) -> dict[str, object]:
        raise AssertionError("must not fall through to content_creator_node")

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fail_if_called,
    )

    result = await generate_one_artifact(_drill_payload())  # type: ignore[arg-type]

    assert result["artifact_workflow_states"][0]["status"] == "passed"


@pytest.mark.anyio
async def test_roadmap_generation_never_calls_content_creator_node(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_if_called(_state: dict[str, object]) -> dict[str, object]:
        raise AssertionError("must not fall through to content_creator_node")

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fail_if_called,
    )

    result = await generate_one_artifact(_roadmap_payload())  # type: ignore[arg-type]

    assert result["artifact_workflow_states"][0]["status"] == "passed"


@pytest.mark.anyio
async def test_reading_passage_generation_never_calls_content_creator_node(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_if_called(_state: dict[str, object]) -> dict[str, object]:
        raise AssertionError("must not fall through to content_creator_node")

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fail_if_called,
    )

    result = await generate_one_artifact(_reading_passage_payload())  # type: ignore[arg-type]

    assert result["artifact_workflow_states"][0]["status"] == "passed"


@pytest.mark.anyio
async def test_infographic_generation_never_calls_content_creator_node(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_if_called(_state: dict[str, object]) -> dict[str, object]:
        raise AssertionError("must not fall through to content_creator_node")

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fail_if_called,
    )

    result = await generate_one_artifact(_infographic_payload())  # type: ignore[arg-type]

    assert result["artifact_workflow_states"][0]["status"] == "passed"


@pytest.mark.anyio
async def test_exit_ticket_generation_never_calls_content_creator_node(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_if_called(_state: dict[str, object]) -> dict[str, object]:
        raise AssertionError("must not fall through to content_creator_node")

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fail_if_called,
    )

    result = await generate_one_artifact(_exit_ticket_payload())  # type: ignore[arg-type]

    assert result["artifact_workflow_states"][0]["status"] == "passed"


@pytest.mark.anyio
async def test_lesson_generation_uses_the_requested_theme() -> None:
    payload = _lesson_payload()
    payload["theme"] = "ocean"

    class ContentStore:
        async def persist(self, _run_id: str, _generation_id: str, artifact: object, _artifact_id: str) -> object:
            assert getattr(artifact, "theme") == "ocean"
            return type("Reference", (), {"as_state": lambda self: {"document_id": "lesson-1"}})()

        async def read_projections(self, _references: object) -> list[object]:
            return []

    result = await generate_one_artifact(payload, ContentStore())  # type: ignore[arg-type]

    assert result["artifact_workflow_states"][0]["status"] == "passed"


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

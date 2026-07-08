from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from common.contracts.quality import ArtifactQualityReport
from packages.agents.teaching_pack.nodes import JsonObject, TeachingPackState, _render_quality
from packages.agents.teaching_pack.stages import StageEnum


def _passing_gate() -> AsyncMock:
    """These tests exercise artifact_workflow wiring (delegation, stable IDs,
    answer-key marking), not reviewer content quality (LIC-01) — stub the gate
    so they stay fast/deterministic instead of depending on a live LLM judge."""
    gate = AsyncMock()
    gate.evaluate.return_value = ArtifactQualityReport(
        artifact_id="stub", artifact_type="lesson", passed=True, issues=[],
    )
    return gate


def _artifacts(result: TeachingPackState) -> list[JsonObject]:
    return result.get("artifacts", [])


def _json_list(value: JsonObject, key: str) -> list[JsonObject]:
    items = value.get(key)
    assert isinstance(items, list)
    narrowed: list[JsonObject] = []
    for item in items:
        assert isinstance(item, dict)
        narrowed.append(item)
    return narrowed


class TestTeachingPackArtifactWorkflow:
    """These cover the imperative _artifact_workflow delegation, which asf-008 moved
    behind the Send-fanout rollback flag. The default Send path is covered by the asf-*
    and canonical-flow suites; here we exercise the rollback path explicitly."""

    @pytest.fixture(autouse=True)
    def _use_rollback_path(self, monkeypatch) -> None:
        monkeypatch.setenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", "1")

    @pytest.mark.anyio
    async def test_artifact_workflow_delegates_to_content_creator_node(self, monkeypatch) -> None:
        from packages.agents.teaching_pack import nodes

        calls = []

        async def fake_content_creator_node(state):
            calls.append(state)
            return {
                "artifacts": [{
                    "artifact_id": "artifact-lesson",
                    "artifact_type": "lesson",
                    "title": "Generated Lesson",
                    "sections": [{"title": "Intro", "content": "Generated content"}],
                    "metadata": {},
                    "accessibility": {"language": "vi"},
                }],
            }

        monkeypatch.setattr(
            "packages.agents.sub_agents.content_creator.nodes.content_creator_node",
            fake_content_creator_node,
        )

        result = await nodes._artifact_workflow(TeachingPackState(
            run_id="run-content",
            contract={"topic": "Fractions", "theme": "default"},
            lesson_plan={"topic": "Fractions"},
            research_brief={"sources": []},
            artifact_types=["lesson"],
        ))

        assert calls == [{
            "lesson_plan": {"topic": "Fractions"},
            "research_bundle": {"sources": []},
            "artifact_types": ["lesson"],
            "theme": "default",
            "run_id": "run-content",
            "current_step": StageEnum.ARTIFACT_WORKFLOW,
            "artifacts": None,
            "revision_feedback": "",
            "use_hierarchical_creator": True,
            "component_effectiveness": {},
        }]
        assert _artifacts(result)[0].get("title") == "Generated Lesson"
        assert _artifacts(result)[0].get("status") == "ready"

    @pytest.mark.anyio
    async def test_artifact_workflow_adds_stable_ids_when_creator_omits_them(self, monkeypatch) -> None:
        from packages.agents.teaching_pack import nodes

        async def fake_content_creator_node(_state):
            return {
                "artifacts": [{
                    "artifact_type": "lesson",
                    "title": "Equivalent Fractions Lesson",
                    "sections": [{"title": "Intro", "content": "Compare equal parts."}],
                    "metadata": {},
                    "accessibility": {"language": "vi"},
                }],
            }

        monkeypatch.setattr(
            "packages.agents.sub_agents.content_creator.nodes.content_creator_node",
            fake_content_creator_node,
        )

        result = await nodes._artifact_workflow(TeachingPackState(
            run_id="run-normalize",
            contract={"topic": "Fractions", "theme": "default"},
            lesson_plan={"topic": "Fractions"},
            research_brief={"sources": []},
            artifact_types=["lesson"],
        ))

        render_result = await _render_quality(TeachingPackState(
            run_id="run-normalize",
            artifacts=_artifacts(result),
        ), quality_gate=_passing_gate())

        assert _artifacts(result)[0].get("artifact_id") == "lesson-1"
        snapshots = render_result.get("rendered_snapshots", [])
        assert snapshots[0].get("artifact_id") == "lesson-1"

    @pytest.mark.anyio
    async def test_artifact_workflow_marks_generated_answer_key_sections_teacher_only(
        self,
        monkeypatch,
    ) -> None:
        from packages.agents.teaching_pack import nodes

        async def fake_content_creator_node(_state):
            return {
                "artifacts": [{
                    "artifact_type": "quiz",
                    "title": "Photosynthesis Quiz",
                    "sections": [
                        {"title": "Question", "content": "What gas do plants release?"},
                        {"title": "Answer Key", "content": "Answer: oxygen"},
                    ],
                    "metadata": {},
                    "accessibility": {"language": "en"},
                }],
            }

        monkeypatch.setattr(
            "packages.agents.sub_agents.content_creator.nodes.content_creator_node",
            fake_content_creator_node,
        )

        result = await nodes._artifact_workflow(TeachingPackState(
            run_id="run-answer-key",
            contract={"topic": "Photosynthesis", "theme": "default"},
            lesson_plan={"topic": "Photosynthesis"},
            research_brief={"sources": []},
            artifact_types=["quiz"],
        ))
        render_result = await _render_quality(TeachingPackState(
            run_id="run-answer-key",
            artifacts=_artifacts(result),
        ), quality_gate=_passing_gate())

        sections = _json_list(_artifacts(result)[0], "sections")
        assert sections[1].get("teacher_only") is True
        assert render_result.get("quality_scores", {}).get("passed") is True

    @pytest.mark.anyio
    async def test_artifact_workflow_marks_correct_answer_sections_teacher_only(
        self,
        monkeypatch,
    ) -> None:
        from packages.agents.teaching_pack import nodes

        async def fake_content_creator_node(_state):
            return {
                "artifacts": [{
                    "artifact_type": "quiz",
                    "title": "Classroom Objects Quiz",
                    "sections": [
                        {"title": "Question", "content": "Which object writes on paper?"},
                        {"title": "Correct Answer", "content": "B. Pencil"},
                    ],
                    "metadata": {},
                    "accessibility": {"language": "en"},
                }],
            }

        monkeypatch.setattr(
            "packages.agents.sub_agents.content_creator.nodes.content_creator_node",
            fake_content_creator_node,
        )

        result = await nodes._artifact_workflow(TeachingPackState(
            run_id="run-correct-answer",
            contract={"topic": "Classroom objects", "theme": "default"},
            lesson_plan={"topic": "Classroom objects"},
            research_brief={"sources": []},
            artifact_types=["quiz"],
        ))
        render_result = await _render_quality(TeachingPackState(
            run_id="run-correct-answer",
            artifacts=_artifacts(result),
        ), quality_gate=_passing_gate())

        sections = _json_list(_artifacts(result)[0], "sections")
        assert sections[1].get("teacher_only") is True
        assert render_result.get("quality_scores", {}).get("passed") is True

    @pytest.mark.anyio
    async def test_artifact_workflow_regenerates_only_scoped_rejected_artifacts(
        self,
        monkeypatch,
    ) -> None:
        from packages.agents.teaching_pack import nodes

        calls = []

        async def fake_content_creator_node(state):
            calls.append(state)
            return {
                "artifacts": [{
                    "artifact_type": "quiz",
                    "title": "Regenerated Quiz",
                    "sections": [{"title": "Question", "content": "What is 2+2?"}],
                    "metadata": {},
                    "accessibility": {"language": "en"},
                }],
            }

        monkeypatch.setattr(
            "packages.agents.sub_agents.content_creator.nodes.content_creator_node",
            fake_content_creator_node,
        )

        result = await nodes._artifact_workflow(TeachingPackState(
            run_id="run-scoped-reject",
            contract={"topic": "Addition", "theme": "default"},
            lesson_plan={"topic": "Addition"},
            research_brief={"sources": []},
            artifact_types=["lesson", "quiz"],
            artifacts=[
                {
                    "artifact_id": "lesson-1",
                    "artifact_type": "lesson",
                    "title": "Accepted Lesson",
                    "sections": [{"title": "Intro", "content": "Keep this."}],
                    "metadata": {},
                    "accessibility": {"language": "en"},
                },
                {
                    "artifact_id": "quiz-2",
                    "artifact_type": "quiz",
                    "title": "Rejected Quiz",
                    "sections": [{"title": "Question", "content": "Old."}],
                    "metadata": {},
                    "accessibility": {"language": "en"},
                },
            ],
            gate_payload={
                "action": "reject",
                "rejection_type": "scoped",
                "artifact_rejections": [
                    {"artifact_id": "quiz-2", "reason": "Need easier distractors."},
                ],
            },
            revision_feedback="Need easier distractors.",
        ))

        assert calls[0]["artifact_types"] == ["quiz"]
        assert calls[0]["revision_feedback"] == "Need easier distractors."
        assert [artifact.get("title") for artifact in _artifacts(result)] == [
            "Accepted Lesson",
            "Regenerated Quiz",
        ]

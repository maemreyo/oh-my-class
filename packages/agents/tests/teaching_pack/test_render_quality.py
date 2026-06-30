from __future__ import annotations

import pytest

from common.contracts.quality import ArtifactQualityReport
from packages.agents.teaching_pack.nodes import (
    TeachingPackState,
    _render_quality,
)
from packages.agents.teaching_pack.quality import TeachingPackQualityGateError
from packages.agents.teaching_pack.quality_routing import route_after_render_quality


class TestTeachingPackRenderQuality:
    @pytest.mark.anyio
    async def test_render_quality_invokes_injected_quality_gate_for_valid_artifacts(self) -> None:
        calls = []

        class RecordingQualityGate:
            async def evaluate(self, state):
                calls.append(state)
                return ArtifactQualityReport(
                    artifact_id=state.artifact_id,
                    artifact_type=state.artifact_type,
                    passed=True,
                )

        state = TeachingPackState(
            run_id="run-quality-gate",
            artifacts=[{
                "artifact_id": "lesson-1",
                "artifact_type": "lesson",
                "theme": "default",
                "title": "Equivalent Fractions Lesson",
                "sections": [{"title": "Intro", "content": "Compare equivalent fractions."}],
                "metadata": {},
                "accessibility": {"language": "en"},
            }],
        )

        result = await _render_quality(state, quality_gate=RecordingQualityGate())

        assert len(calls) == 1
        assert calls[0].run_id == "run-quality-gate"
        assert calls[0].artifact_id == "lesson-1"
        assert result.get("quality_scores", {}).get("passed") is True
        assert result.get("rendered_snapshots")

    @pytest.mark.anyio
    async def test_render_quality_precheck_short_circuits_before_injected_gate(self) -> None:
        calls = []

        class RecordingQualityGate:
            async def evaluate(self, state):
                calls.append(state)
                return ArtifactQualityReport(
                    artifact_id=state.artifact_id,
                    artifact_type=state.artifact_type,
                    passed=True,
                )

        state = TeachingPackState(
            run_id="run-quality",
            artifacts=[{
                "artifact_type": "lesson",
                "theme": "default",
                "title": "[TBD] Lesson",
                "sections": [{"title": "Intro", "content": "placeholder"}],
                "metadata": {},
                "accessibility": {"language": "vi"},
            }],
        )

        with pytest.raises(TeachingPackQualityGateError, match="placeholder_content"):
            await _render_quality(state, quality_gate=RecordingQualityGate())

        assert calls == []

    @pytest.mark.anyio
    async def test_render_quality_blocks_placeholder_artifacts_before_approval(self) -> None:
        state = TeachingPackState(
            run_id="run-quality",
            artifacts=[{
                "artifact_type": "lesson",
                "theme": "default",
                "title": "[TBD] Lesson",
                "sections": [{"title": "Intro", "content": "placeholder"}],
                "metadata": {},
                "accessibility": {"language": "vi"},
            }],
        )

        with pytest.raises(TeachingPackQualityGateError, match="placeholder_content"):
            await _render_quality(state)

    @pytest.mark.anyio
    async def test_render_quality_blocks_student_facing_answer_keys(self) -> None:
        state = TeachingPackState(
            run_id="run-quality",
            artifacts=[{
                "artifact_type": "quiz",
                "theme": "default",
                "title": "Quiz Lesson",
                "sections": [{"title": "Question", "content": "Answer: A"}],
                "metadata": {},
                "accessibility": {"language": "vi"},
            }],
        )

        with pytest.raises(TeachingPackQualityGateError, match="answer_key_leakage"):
            await _render_quality(state)

    @pytest.mark.anyio
    async def test_render_quality_routes_quiz_that_does_not_match_lesson_terms(self) -> None:
        state = TeachingPackState(
            run_id="run-coherence",
            artifacts=[
                {
                    "artifact_type": "lesson",
                    "theme": "default",
                    "title": "Equivalent Fractions Lesson",
                    "sections": [{"title": "Intro", "content": "Compare numerators and denominators."}],
                    "metadata": {},
                    "accessibility": {"language": "en"},
                },
                {
                    "artifact_type": "quiz",
                    "theme": "default",
                    "title": "Photosynthesis Quiz",
                    "sections": [{"title": "Question", "content": "Which pigment absorbs sunlight?"}],
                    "metadata": {},
                    "accessibility": {"language": "en"},
                },
            ],
        )

        result = await _render_quality(state)

        assert result.get("quality_recovery_route") == "artifact_workflow"
        assert "pack.coherence: quiz_not_aligned_with_lesson" in result.get("quality_issues", [])
        assert route_after_render_quality(TeachingPackState(**result)) == "artifact_workflow"

    @pytest.mark.anyio
    async def test_render_quality_routes_artifacts_that_miss_lesson_objectives(self) -> None:
        state = TeachingPackState(
            run_id="run-objective-coherence",
            artifacts=[
                {
                    "artifact_type": "lesson",
                    "theme": "default",
                    "title": "Equivalent Fractions Lesson",
                    "sections": [{"title": "Intro", "content": "Compare fractions with equal value."}],
                    "metadata": {"learning_objectives": ["Compare equivalent fractions using models"]},
                    "accessibility": {"language": "en"},
                },
                {
                    "artifact_type": "worksheet",
                    "theme": "default",
                    "title": "Worksheet",
                    "sections": [{"title": "Practice", "content": "Label planets in the solar system."}],
                    "metadata": {},
                    "accessibility": {"language": "en"},
                },
            ],
        )

        result = await _render_quality(state)

        assert result.get("quality_recovery_route") == "planning_blueprint"
        assert "pack.coherence: worksheet_not_aligned_with_objectives" in result.get("quality_issues", [])
        assert route_after_render_quality(TeachingPackState(**result)) == "planning_blueprint"

    @pytest.mark.anyio
    async def test_render_quality_routes_vocabulary_drift_across_student_artifacts(self) -> None:
        state = TeachingPackState(
            run_id="run-vocabulary-coherence",
            artifacts=[
                {
                    "artifact_type": "lesson",
                    "theme": "default",
                    "title": "Fraction Vocabulary Lesson",
                    "sections": [{"title": "Intro", "content": "Numerator and denominator name fraction parts."}],
                    "metadata": {"key_terms": ["numerator", "denominator"]},
                    "accessibility": {"language": "en"},
                },
                {
                    "artifact_type": "quiz",
                    "theme": "default",
                    "title": "Fraction Quiz",
                    "sections": [{"title": "Question", "content": "Which numerator shows the shaded parts?"}],
                    "metadata": {},
                    "accessibility": {"language": "en"},
                },
            ],
        )

        result = await _render_quality(state)

        assert result.get("quality_recovery_route") == "artifact_workflow"
        assert "pack.coherence: quiz_missing_lesson_vocabulary" in result.get("quality_issues", [])
        assert route_after_render_quality(TeachingPackState(**result)) == "artifact_workflow"

    @pytest.mark.anyio
    async def test_render_quality_routes_invalid_vietnamese_difficulty_distribution(self) -> None:
        state = TeachingPackState(
            run_id="run-vi-difficulty-coherence",
            artifacts=[
                {
                    "artifact_type": "lesson",
                    "theme": "default",
                    "title": "Phân số tương đương",
                    "sections": [{"title": "Mở đầu", "content": "So sánh tử số và mẫu số của phân số."}],
                    "metadata": {"key_terms": ["phân số", "tử số", "mẫu số"]},
                    "accessibility": {"language": "vi"},
                },
                {
                    "artifact_type": "quiz",
                    "theme": "default",
                    "title": "Bài kiểm tra phân số",
                    "sections": [{"title": "Câu hỏi", "content": "Chọn phân số có tử số và mẫu số phù hợp."}],
                    "metadata": {
                        "difficulty_distribution": {
                            "nhan_biet": 0.1,
                            "thong_hieu": 0.1,
                            "van_dung": 0.4,
                            "van_dung_cao": 0.4,
                        },
                    },
                    "accessibility": {"language": "vi"},
                },
            ],
        )

        result = await _render_quality(state)

        assert result.get("quality_recovery_route") == "planning_blueprint"
        assert "pack.coherence: quiz_invalid_vietnamese_difficulty_distribution" in result.get("quality_issues", [])
        assert route_after_render_quality(TeachingPackState(**result)) == "planning_blueprint"

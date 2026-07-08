from __future__ import annotations

import pytest

from common.contracts.quality import ArtifactQualityReport, QualityFailureClass, QualityIssue
from packages.agents.teaching_pack.nodes import TeachingPackState, _render_quality


class FailingQualityGate:
    def __init__(self, failure_class: QualityFailureClass) -> None:
        self._failure_class = failure_class

    async def evaluate(self, state, _artifact):
        return ArtifactQualityReport(
            artifact_id=state.artifact_id,
            artifact_type=state.artifact_type,
            passed=False,
            issues=[QualityIssue(
                failure_class=self._failure_class,
                location="artifact",
                message="quality failure",
            )],
        )


def _valid_state(fail_count: int = 0, max_healing_attempts: int | None = None) -> TeachingPackState:
    return TeachingPackState(
        run_id="run-healing",
        fail_count=fail_count,
        **({"max_healing_attempts": max_healing_attempts} if max_healing_attempts is not None else {}),
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


class TestTeachingPackHealingRecovery:
    @pytest.mark.anyio
    async def test_quality_failure_triggers_rewrite_healing(self) -> None:
        result = await _render_quality(
            _valid_state(),
            quality_gate=FailingQualityGate(QualityFailureClass.ANSWER_KEY_LEAKAGE),
        )

        assert result.get("healing_strategy") == "rewrite"
        assert result.get("quality_recovery_route") == "artifact_workflow"
        assert result.get("fail_count") == 1

    @pytest.mark.anyio
    async def test_persistent_quality_failure_reroutes_generation_model(self) -> None:
        result = await _render_quality(
            _valid_state(fail_count=1),
            quality_gate=FailingQualityGate(QualityFailureClass.ANSWER_KEY_LEAKAGE),
        )

        assert result.get("healing_strategy") == "reroute"
        # Single-model deployment (no MODEL_STRONG_DEFAULT configured): reroute
        # holds the model steady rather than swapping to a fabricated name.
        assert result.get("generation_model") == "4omc"
        assert result.get("quality_recovery_route") == "artifact_workflow"
        assert result.get("fail_count") == 2

    @pytest.mark.anyio
    async def test_structural_quality_failure_replans_after_two_failed_heals(self) -> None:
        result = await _render_quality(
            _valid_state(fail_count=2),
            quality_gate=FailingQualityGate(QualityFailureClass.PEDAGOGICAL_MISMATCH),
        )

        assert result.get("healing_strategy") == "replan"
        assert result.get("quality_recovery_route") == "planning_blueprint"
        assert result.get("fail_count") == 3

    @pytest.mark.anyio
    async def test_quality_failure_escalates_after_max_healing_attempts(self) -> None:
        result = await _render_quality(
            _valid_state(fail_count=3),
            quality_gate=FailingQualityGate(QualityFailureClass.ANSWER_KEY_LEAKAGE),
        )

        assert result.get("healing_strategy") == "escalate"
        assert result.get("quality_recovery_route") == "teacher_approval"
        assert result.get("escalate") is True

    @pytest.mark.anyio
    async def test_zero_max_healing_attempts_disables_healing(self) -> None:
        result = await _render_quality(
            _valid_state(max_healing_attempts=0),
            quality_gate=FailingQualityGate(QualityFailureClass.ANSWER_KEY_LEAKAGE),
        )

        assert "healing_strategy" not in result
        assert result.get("quality_recovery_route") == "artifact_workflow"
        assert result.get("fail_count") is None

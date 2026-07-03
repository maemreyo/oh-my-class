from __future__ import annotations

from common.contracts.quality import QualityFailureClass
from packages.agents.teaching_pack.healing_runtime import heal_quality_failure


class TestTeachingPackHealingRuntime:
    def test_quality_failures_persist_next_fail_count_in_update(self) -> None:
        first = heal_quality_failure(
            {"run_id": "run-heal", "max_healing_attempts": 3},
            [QualityFailureClass.PLACEHOLDER_CONTENT],
            ["quiz.score: too low"],
        )
        second = heal_quality_failure(
            {"run_id": "run-heal", "fail_count": 1, "max_healing_attempts": 3},
            [QualityFailureClass.PLACEHOLDER_CONTENT],
            ["quiz.score: too low"],
        )
        third = heal_quality_failure(
            {"run_id": "run-heal", "fail_count": 2, "max_healing_attempts": 3},
            [QualityFailureClass.PLACEHOLDER_CONTENT],
            ["quiz.score: too low"],
        )
        fourth = heal_quality_failure(
            {"run_id": "run-heal", "fail_count": 3, "max_healing_attempts": 3},
            [QualityFailureClass.PLACEHOLDER_CONTENT],
            ["quiz.score: too low"],
        )

        assert (first["fail_count"], first["healing_strategy"]) == (1, "rewrite")
        assert (second["fail_count"], second["healing_strategy"]) == (2, "reroute")
        assert (third["fail_count"], third["healing_strategy"]) == (3, "replan")
        assert (fourth["fail_count"], fourth["healing_strategy"]) == (4, "escalate")
        assert fourth["quality_recovery_route"] == "teacher_approval"

    def test_force_escalate_seam_is_inert_when_unset(self, monkeypatch) -> None:
        monkeypatch.delenv("TEACHING_PACK_FORCE_ESCALATE", raising=False)

        result = heal_quality_failure(
            {"run_id": "run-heal", "max_healing_attempts": 3},
            [QualityFailureClass.PLACEHOLDER_CONTENT],
            ["quiz.score: too low"],
        )

        assert result["healing_strategy"] == "rewrite"
        assert result.get("escalate") is not True

    def test_force_escalate_seam_routes_to_teacher_approval(self, monkeypatch) -> None:
        monkeypatch.setenv("TEACHING_PACK_FORCE_ESCALATE", "true")

        result = heal_quality_failure(
            {"run_id": "run-heal", "max_healing_attempts": 3},
            [QualityFailureClass.PLACEHOLDER_CONTENT],
            ["quiz.score: too low"],
        )

        assert result["healing_strategy"] == "escalate"
        assert result["escalate"] is True
        assert result["quality_recovery_route"] == "teacher_approval"

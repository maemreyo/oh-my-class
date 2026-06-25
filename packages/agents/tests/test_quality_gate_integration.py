"""Integration tests for quality gate chain and healing loop.

Tests the end-to-end flow: schema validation → content review → LLM judge
→ routing decisions, plus the healing orchestrator strategy selection.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import patch

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


VALID_ARTIFACT = {
    "artifact_type": "lesson",
    "title": "Photosynthesis Basics",
    "sections": [{"content": "Plants use sunlight to make food."}],
}
HTML_ARTIFACT = {
    "artifact_type": "lesson",
    "title": "Photosynthesis HTML",
    "sections": [
        {"content": (
            "<!DOCTYPE html><html><body>"
            "Plants use sunlight to make food.</body></html>"
        )},
    ],
}


def _base_state(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "raw_request": "Teach photosynthesis",
        "teacher_id": "t-001",
        "class_info": {"grade": 5, "subject": "science"},
        "run_id": "run-001",
        "blueprint_approved": False,
        "quality_passed": False,
        "teacher_approved": False,
        "revision_count": 0,
        "artifact_types": ["lesson"],
        "theme": "default",
        "artifacts": [],
        "export_formats": ["html"],
        "exported_files": [],
        "current_step": 9,
        "tokens_used": 0,
        "cost_usd": 0.0,
        "research_policy": "basic",
        "fail_count": 0,
    }
    base.update(overrides)
    return base


# ── Schema Validator ────────────────────────────────────────────────────────


class TestSchemaValidator:
    def test_passes_valid_artifacts(self):
        from packages.agents.gates.schema_validator import step_09_schema_validate
        state = _base_state(artifacts=[VALID_ARTIFACT])
        result = step_09_schema_validate(cast("OhMyClassState", state))
        assert result["schema_valid"] is True
        assert "fail_layer" not in result

    def test_fails_empty_artifacts(self):
        from packages.agents.gates.schema_validator import step_09_schema_validate
        state = _base_state(artifacts=[])
        result = step_09_schema_validate(cast("OhMyClassState", state))
        assert result["schema_valid"] is False
        assert result["fail_layer"] == "schema"
        assert result["fail_type"] == "validation"

    def test_fails_missing_keys(self):
        from packages.agents.gates.schema_validator import step_09_schema_validate
        state = _base_state(artifacts=[{"content": "test"}])
        result = step_09_schema_validate(cast("OhMyClassState", state))
        assert result["schema_valid"] is False
        assert result["fail_layer"] == "schema"

    def test_fails_empty_content(self):
        from packages.agents.gates.schema_validator import step_09_schema_validate
        artifact = {"type": "lesson", "content": ""}
        state = _base_state(artifacts=[artifact])
        result = step_09_schema_validate(cast("OhMyClassState", state))
        assert result["schema_valid"] is False

    def test_preserves_fail_count_from_state(self):
        from packages.agents.gates.schema_validator import step_09_schema_validate
        state = _base_state(artifacts=[], fail_count=2)
        result = step_09_schema_validate(cast("OhMyClassState", state))
        assert result["fail_count"] == 2


# ── Content Reviewer ────────────────────────────────────────────────────────


class TestContentReviewer:
    def test_passes_clean_content(self):
        from packages.agents.gates.content_reviewer import step_10_content_review
        state = _base_state(artifacts=[VALID_ARTIFACT])
        result = step_10_content_review(cast("OhMyClassState", state))
        assert result["content_review_passed"] is True
        assert "fail_layer" not in result

    def test_fails_blocked_content(self):
        from packages.agents.gates.content_reviewer import step_10_content_review
        state = _base_state(artifacts=[{
            "artifact_type": "lesson",
            "title": "Bad Lesson",
            "sections": [{"content": "violence and gore in this lesson"}],
        }])
        result = step_10_content_review(cast("OhMyClassState", state))
        assert result["content_review_passed"] is False
        assert result["fail_layer"] == "content"

    def test_fails_html_with_external_assets(self):
        from packages.agents.gates.content_reviewer import step_10_content_review
        html_content = (
            '<!DOCTYPE html><html><body>'
            '<img src="https://ext.com/i.png"></body></html>'
        )
        artifact = {
            "artifact_type": "lesson",
            "title": "HTML Lesson",
            "sections": [{"content": html_content}],
        }
        result = step_10_content_review(cast("OhMyClassState", _base_state(artifacts=[artifact])))
        assert result["content_review_passed"] is False

    def test_no_artifacts_passes(self):
        from packages.agents.gates.content_reviewer import step_10_content_review
        result = step_10_content_review(cast("OhMyClassState", _base_state(artifacts=[])))
        assert result["content_review_passed"] is True


# ── LLM Judge ───────────────────────────────────────────────────────────────


class TestLLMJudge:
    def test_passes_non_empty_artifacts(self):
        from packages.agents.gates.llm_judge import step_10b_llm_judge
        state = _base_state(artifacts=[VALID_ARTIFACT], lesson_plan={"topic": "Math"})
        result = step_10b_llm_judge(cast("OhMyClassState", state))
        assert result["judge_score"] >= 7.0
        assert "fail_layer" not in result

    def test_fails_empty_artifacts(self):
        from packages.agents.gates.llm_judge import step_10b_llm_judge
        result = step_10b_llm_judge(cast("OhMyClassState", _base_state(artifacts=[])))
        assert result["judge_score"] == 0.0
        assert result["fail_layer"] == "judge"
        assert result["fail_type"] == "score"

    def test_empty_content_scores_zero(self):
        from packages.agents.gates.llm_judge import step_10b_llm_judge
        result = step_10b_llm_judge(cast("OhMyClassState", _base_state(artifacts=[{
            "artifact_type": "lesson",
            "title": "Empty Lesson",
            "sections": [{"content": ""}],
        }])))
        assert result["fail_layer"] == "judge"

    def test_score_is_float(self):
        from packages.agents.gates.llm_judge import step_10b_llm_judge
        result = step_10b_llm_judge(cast("OhMyClassState", _base_state(artifacts=[VALID_ARTIFACT])))
        assert isinstance(result["judge_score"], float)


# ── Healing Orchestrator ────────────────────────────────────────────────────


class TestHealingOrchestrator:
    def test_first_validation_failure_rewrites(self):
        from packages.agents.healing.orchestrator import HealingOrchestrator
        state = cast("OhMyClassState", _base_state(fail_count=0, fail_type="validation"))
        result = HealingOrchestrator(max_retries=3).heal(state)
        assert result.get("healing_strategy") == "rewrite"
        assert result["fail_count"] == 1

    def test_second_failure_reroutes(self):
        from packages.agents.healing.orchestrator import HealingOrchestrator
        state = cast("OhMyClassState", _base_state(fail_count=1, fail_type="validation"))
        result = HealingOrchestrator(max_retries=3).heal(state)
        assert result.get("healing_strategy") == "reroute"
        assert result["fail_count"] == 2

    def test_third_failure_replans(self):
        from packages.agents.healing.orchestrator import HealingOrchestrator
        state = cast("OhMyClassState", _base_state(fail_count=2, fail_type="score"))
        result = HealingOrchestrator(max_retries=3).heal(state)
        assert result.get("healing_strategy") == "replan"
        assert result["fail_count"] == 3

    def test_fourth_failure_escalates(self):
        from packages.agents.healing.orchestrator import HealingOrchestrator
        state = cast("OhMyClassState", _base_state(fail_count=3, fail_type="score"))
        result = HealingOrchestrator(max_retries=3).heal(state)
        assert result.get("escalate") is True
        assert result["fail_count"] == 4

    def test_first_transient_failure_retries(self):
        from packages.agents.healing.orchestrator import HealingOrchestrator
        state = cast("OhMyClassState", _base_state(fail_count=0, fail_type="transient"))
        with patch("packages.agents.healing.strategies.retry.time.sleep"):
            result = HealingOrchestrator(max_retries=3).heal(state)
        assert result.get("healing_strategy") == "retry"

    def test_first_score_failure_rewrites(self):
        from packages.agents.healing.orchestrator import HealingOrchestrator
        state = cast("OhMyClassState", _base_state(fail_count=0, fail_type="score"))
        result = HealingOrchestrator(max_retries=3).heal(state)
        assert result.get("healing_strategy") == "rewrite"

    def test_rewrite_clears_artifacts(self):
        from packages.agents.healing.orchestrator import HealingOrchestrator
        state = cast("OhMyClassState", _base_state(fail_count=0, fail_type="validation"))
        result = HealingOrchestrator(max_retries=3).heal(state)
        assert result["artifacts"] is None

    def test_escalate_sets_error_field(self):
        from packages.agents.healing.orchestrator import HealingOrchestrator
        state = cast("OhMyClassState", _base_state(
            fail_count=3, fail_type="score", fail_layer="judge",
        ))
        result = HealingOrchestrator(max_retries=3).heal(state)
        assert "error" in result
        assert "judge" in result["error"]


# ── Routing functions ───────────────────────────────────────────────────────


class TestRoutingAfterSchema:
    def test_routes_to_content_review_on_pass(self):
        from packages.agents.graph import route_after_schema
        state = cast("OhMyClassState", {"schema_valid": True})
        assert route_after_schema(state) == "step_10_content_review"

    def test_routes_to_healing_on_fail(self):
        from packages.agents.graph import route_after_schema
        state = cast("OhMyClassState", {"schema_valid": False})
        assert route_after_schema(state) == "healing_node"

    def test_routes_to_healing_when_no_schema_result(self):
        from packages.agents.graph import route_after_schema
        assert route_after_schema(cast("OhMyClassState", {})) == "healing_node"


class TestRoutingAfterContentReview:
    def test_routes_to_judge_on_pass(self):
        from packages.agents.graph import route_after_content_review
        state = cast("OhMyClassState", {"content_review_passed": True})
        assert route_after_content_review(state) == "step_10b_llm_judge"

    def test_routes_to_healing_on_fail(self):
        from packages.agents.graph import route_after_content_review
        state = cast("OhMyClassState", {"content_review_passed": False})
        assert route_after_content_review(state) == "healing_node"

    def test_routes_to_healing_when_no_result(self):
        from packages.agents.graph import route_after_content_review
        assert route_after_content_review(cast("OhMyClassState", {})) == "healing_node"


class TestRoutingAfterJudge:
    def test_routes_to_gate_on_high_score(self):
        from packages.agents.graph import route_after_judge
        state7 = cast("OhMyClassState", {"judge_score": 7.0})
        assert route_after_judge(state7) == "gate_02_content_approval"
        state9 = cast("OhMyClassState", {"judge_score": 9.5})
        assert route_after_judge(state9) == "gate_02_content_approval"

    def test_routes_to_healing_on_low_score(self):
        from packages.agents.graph import route_after_judge
        state5 = cast("OhMyClassState", {"judge_score": 5.0})
        assert route_after_judge(state5) == "healing_node"
        state6 = cast("OhMyClassState", {"judge_score": 6.9})
        assert route_after_judge(state6) == "healing_node"

    def test_routes_to_healing_when_no_score(self):
        from packages.agents.graph import route_after_judge
        assert route_after_judge(cast("OhMyClassState", {})) == "healing_node"


# ── Full chain integration ──────────────────────────────────────────────────


class TestQualityGateChain:
    def test_valid_artifacts_pass_all_three_gates(self):
        from packages.agents.gates.content_reviewer import step_10_content_review
        from packages.agents.gates.llm_judge import step_10b_llm_judge
        from packages.agents.gates.schema_validator import step_09_schema_validate
        from packages.agents.graph import (
            route_after_content_review,
            route_after_judge,
            route_after_schema,
        )

        state: dict[str, Any] = _base_state(
            artifacts=[VALID_ARTIFACT],
            lesson_plan={"topic": "Photosynthesis"},
        )

        schema_result = step_09_schema_validate(cast("OhMyClassState", state))
        state.update(schema_result)
        schema_route = route_after_schema(cast("OhMyClassState", state))
        assert schema_route == "step_10_content_review"

        content_result = step_10_content_review(cast("OhMyClassState", state))
        state.update(content_result)
        review_route = route_after_content_review(cast("OhMyClassState", state))
        assert review_route == "step_10b_llm_judge"

        judge_result = step_10b_llm_judge(cast("OhMyClassState", state))
        state.update(judge_result)
        judge_route = route_after_judge(cast("OhMyClassState", state))
        assert judge_route == "gate_02_content_approval"

    def test_empty_artifacts_fail_at_schema_and_heal(self):
        from packages.agents.gates.schema_validator import step_09_schema_validate
        from packages.agents.graph import route_after_schema
        from packages.agents.healing.orchestrator import HealingOrchestrator

        state: dict[str, Any] = _base_state(artifacts=[])

        schema_result = step_09_schema_validate(cast("OhMyClassState", state))
        state.update(schema_result)
        assert route_after_schema(cast("OhMyClassState", state)) == "healing_node"

        heal_result = HealingOrchestrator(max_retries=3).heal(cast("OhMyClassState", state))
        state.update(heal_result)
        assert state["healing_strategy"] == "rewrite"
        assert state["artifacts"] is None

    def test_healing_escalates_after_max_retries(self):
        from packages.agents.healing.orchestrator import (
            HealingOrchestrator,
            route_after_healing,
        )

        state: dict[str, Any] = _base_state(
            fail_count=3,
            fail_type="validation",
            fail_layer="schema",
        )

        heal_result = HealingOrchestrator(max_retries=3).heal(
            cast("OhMyClassState", state),
        )
        state.update(heal_result)
        assert state["escalate"] is True
        assert route_after_healing(cast("OhMyClassState", state)) == "escalate_node"


# ── Quality summary builder (read model) ────────────────────────────────────


class TestBuildQualitySummary:
    def test_returns_empty_when_no_quality_data(self):
        from services.gateway.routers.runs import _build_quality_summary
        assert _build_quality_summary({}) == {}

    def test_includes_schema_valid_when_present(self):
        from services.gateway.routers.runs import _build_quality_summary
        result = _build_quality_summary({"schema_valid": True})
        assert result["schema_valid"] is True

    def test_includes_judge_score_when_present(self):
        from services.gateway.routers.runs import _build_quality_summary
        result = _build_quality_summary({"judge_score": 8.5})
        assert result["judge_score"] == 8.5

    def test_includes_healing_strategy_when_present(self):
        from services.gateway.routers.runs import _build_quality_summary
        result = _build_quality_summary({"healing_strategy": "rewrite"})
        assert result["healing_strategy"] == "rewrite"

    def test_includes_fail_count_when_positive(self):
        from services.gateway.routers.runs import _build_quality_summary
        result = _build_quality_summary({"fail_count": 2})
        assert result["fail_count"] == 2

    def test_excludes_fail_count_when_zero(self):
        from services.gateway.routers.runs import _build_quality_summary
        result = _build_quality_summary({"fail_count": 0})
        assert "fail_count" not in result

    def test_includes_fail_context_when_present(self):
        from services.gateway.routers.runs import _build_quality_summary
        ctx = {"errors": ["missing content"]}
        result = _build_quality_summary({"fail_context": ctx})
        assert result["fail_context"] == ctx

    def test_aggregates_multiple_quality_fields(self):
        from services.gateway.routers.runs import _build_quality_summary
        state = {
            "schema_valid": True,
            "content_review_passed": True,
            "judge_score": 8.0,
            "quality_passed": True,
        }
        result = _build_quality_summary(state)
        assert result["schema_valid"] is True
        assert result["content_review_passed"] is True
        assert result["judge_score"] == 8.0
        assert result["passed"] is True


# ── Finalize hard invariant ─────────────────────────────────────────────────


FINALIZE_ARTIFACT_CLEAN = {
    "artifact_type": "lesson",
    "title": "Clean Lesson",
    "sections": [{"content": "Plants use sunlight to make food."}],
    "theme": "default",
    "accessibility": {"language": "en"},
}

FINALIZE_ARTIFACT_WITH_URL = {
    "artifact_type": "lesson",
    "title": "Bad Lesson",
    "sections": [
        {"content": "See this resource: https://cdn.example.com/bad.js"},
    ],
    "theme": "default",
    "accessibility": {"language": "en"},
}

FINALIZE_ARTIFACT_TEACHER_ONLY = {
    "artifact_type": "quiz",
    "title": "Answer Key",
    "sections": [{"content": "https://cdn.example.com/leak.js"}],
    "theme": "default",
    "teacher_only": True,
}


class TestFinalizeHardInvariant:
    def test_clean_artifact_exports_successfully(self):
        from packages.agents.nodes.finalize import step_12_finalize
        state = _base_state(
            artifacts=[FINALIZE_ARTIFACT_CLEAN],
            export_formats=["html"],
        )
        result = step_12_finalize(cast("OhMyClassState", state))
        assert len(result["exported_files"]) == 1
        assert "fail_context" not in result

    def test_artifact_with_url_rejected(self):
        from packages.agents.nodes.finalize import step_12_finalize
        state = _base_state(
            artifacts=[FINALIZE_ARTIFACT_WITH_URL],
            export_formats=["html"],
        )
        result = step_12_finalize(cast("OhMyClassState", state))
        assert result.get("export_ready") is False
        assert result.get("fail_type") == "invariant"
        errors = result["fail_context"]["errors"]
        assert any("https://" in e for e in errors)

    def test_teacher_only_artifact_with_url_skipped(self):
        from packages.agents.nodes.finalize import step_12_finalize
        state = _base_state(
            artifacts=[FINALIZE_ARTIFACT_TEACHER_ONLY],
            export_formats=["html"],
        )
        result = step_12_finalize(cast("OhMyClassState", state))
        assert len(result["exported_files"]) == 0
        assert "fail_context" not in result

    def test_teacher_only_section_with_url_not_flagged(self):
        from packages.agents.nodes.finalize import step_12_finalize
        artifact = {
            "artifact_type": "lesson",
            "title": "Mixed Lesson",
            "sections": [
                {"content": "Clean student content here."},
                {"content": "https://internal.example.com/secret.js", "teacher_only": True},
            ],
            "theme": "default",
            "accessibility": {"language": "en"},
        }
        state = _base_state(artifacts=[artifact], export_formats=["html"])
        result = step_12_finalize(cast("OhMyClassState", state))
        assert len(result["exported_files"]) == 1
        assert "fail_context" not in result

    def test_non_teacher_only_section_with_url_flagged(self):
        from packages.agents.nodes.finalize import step_12_finalize
        artifact = {
            "artifact_type": "lesson",
            "title": "Mixed Lesson",
            "sections": [
                {"content": "See https://cdn.example.com/bad.js for details."},
                {"content": "Clean student content."},
            ],
            "theme": "default",
            "accessibility": {"language": "en"},
        }
        state = _base_state(artifacts=[artifact], export_formats=["html"])
        result = step_12_finalize(cast("OhMyClassState", state))
        assert result.get("export_ready") is False
        assert result.get("fail_type") == "invariant"

    def test_finalize_produces_standalone_html(self):
        from packages.agents.nodes.finalize import step_12_finalize
        state = _base_state(
            artifacts=[FINALIZE_ARTIFACT_CLEAN],
            export_formats=["html"],
        )
        result = step_12_finalize(cast("OhMyClassState", state))
        html = result["exported_files"][0]["content"]
        assert "<!DOCTYPE html>" in html
        assert "oh-my-class" in html
        assert "https://" not in html

    def test_finalize_empty_artifacts_exports_nothing(self):
        from packages.agents.nodes.finalize import step_12_finalize
        state = _base_state(artifacts=[], export_formats=["html"])
        result = step_12_finalize(cast("OhMyClassState", state))
        assert result["exported_files"] == []

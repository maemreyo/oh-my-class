"""Tests for quality gate nodes — schema, content review, LLM judge, export readiness."""
from __future__ import annotations
import pytest

def make_base_state(**overrides) -> dict:
    base = {
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


VALID_ARTIFACT = {"type": "lesson", "content": "Plants use sunlight to make food."}
HTML_ARTIFACT = {
    "type": "lesson_html",
    "content": "<!DOCTYPE html><html><body>Plants use sunlight to make food.</body></html>",
}


class TestSchemaValidator:
    def test_passes_with_valid_artifacts(self):
        from packages.agents.gates.schema_validator import step_09_schema_validate
        state = make_base_state(artifacts=[VALID_ARTIFACT])
        result = step_09_schema_validate(state)
        assert result["schema_valid"] is True
        assert "fail_layer" not in result

    def test_fails_with_no_artifacts(self):
        from packages.agents.gates.schema_validator import step_09_schema_validate
        state = make_base_state(artifacts=[])
        result = step_09_schema_validate(state)
        assert result["schema_valid"] is False
        assert result["fail_layer"] == "schema"
        assert result["fail_type"] == "validation"

    def test_fails_with_missing_content_key(self):
        from packages.agents.gates.schema_validator import step_09_schema_validate
        state = make_base_state(artifacts=[{"type": "lesson"}])
        result = step_09_schema_validate(state)
        assert result["schema_valid"] is False
        assert "fail_context" in result
        assert any("content" in e for e in result["fail_context"]["errors"])

    def test_fails_with_empty_content(self):
        from packages.agents.gates.schema_validator import step_09_schema_validate
        state = make_base_state(artifacts=[{"type": "lesson", "content": "   "}])
        result = step_09_schema_validate(state)
        assert result["schema_valid"] is False

    def test_fails_with_missing_type_key(self):
        from packages.agents.gates.schema_validator import step_09_schema_validate
        state = make_base_state(artifacts=[{"content": "some content"}])
        result = step_09_schema_validate(state)
        assert result["schema_valid"] is False

    def test_preserves_fail_count(self):
        from packages.agents.gates.schema_validator import step_09_schema_validate
        state = make_base_state(artifacts=[], fail_count=2)
        result = step_09_schema_validate(state)
        assert result["fail_count"] == 2  # validator reads, healing_node increments

    def test_multiple_valid_artifacts_pass(self):
        from packages.agents.gates.schema_validator import step_09_schema_validate
        state = make_base_state(artifacts=[VALID_ARTIFACT, HTML_ARTIFACT])
        result = step_09_schema_validate(state)
        assert result["schema_valid"] is True


class TestContentReviewer:
    def test_passes_with_clean_content(self):
        from packages.agents.gates.content_reviewer import step_10_content_review
        state = make_base_state(artifacts=[VALID_ARTIFACT])
        result = step_10_content_review(state)
        assert result["content_review_passed"] is True

    def test_fails_with_blocked_content(self):
        from packages.agents.gates.content_reviewer import step_10_content_review
        state = make_base_state(artifacts=[
            {"type": "lesson", "content": "violence and gore in this lesson"}
        ])
        result = step_10_content_review(state)
        assert result["content_review_passed"] is False
        assert result["fail_layer"] == "content"

    def test_passes_with_valid_html_artifact(self):
        from packages.agents.gates.content_reviewer import step_10_content_review
        state = make_base_state(artifacts=[HTML_ARTIFACT])
        result = step_10_content_review(state)
        assert result["content_review_passed"] is True

    def test_fails_html_with_external_assets(self):
        from packages.agents.gates.content_reviewer import step_10_content_review
        artifact = {
            "type": "lesson_html",
            "content": '<!DOCTYPE html><html><body><img src="https://external.com/img.png"></body></html>',
        }
        state = make_base_state(artifacts=[artifact])
        result = step_10_content_review(state)
        assert result["content_review_passed"] is False

    def test_fails_worksheet_with_answer_key(self):
        from packages.agents.gates.content_reviewer import step_10_content_review
        artifact = {
            "type": "worksheet",
            "content": "Question 1: What is 2+2?\nAnswer Key: 4",
        }
        state = make_base_state(artifacts=[artifact])
        result = step_10_content_review(state)
        assert result["content_review_passed"] is False

    def test_no_artifacts_passes(self):
        from packages.agents.gates.content_reviewer import step_10_content_review
        state = make_base_state(artifacts=[])
        result = step_10_content_review(state)
        # Empty artifacts — no errors to find, passes review
        assert result["content_review_passed"] is True

    def test_fail_context_has_errors(self):
        from packages.agents.gates.content_reviewer import step_10_content_review
        state = make_base_state(artifacts=[
            {"type": "lesson", "content": "explicit adult violence content"}
        ])
        result = step_10_content_review(state)
        assert "fail_context" in result
        assert len(result["fail_context"]["errors"]) > 0


class TestLLMJudge:
    def test_passes_with_valid_artifacts(self):
        from packages.agents.gates.llm_judge import step_10b_llm_judge
        state = make_base_state(artifacts=[VALID_ARTIFACT])
        result = step_10b_llm_judge(state)
        assert "judge_score" in result
        assert result["judge_score"] >= 7.0
        assert "fail_layer" not in result

    def test_fails_with_no_artifacts(self):
        from packages.agents.gates.llm_judge import step_10b_llm_judge
        state = make_base_state(artifacts=[])
        result = step_10b_llm_judge(state)
        assert result["judge_score"] == 0.0
        assert result["fail_layer"] == "judge"

    def test_score_is_float(self):
        from packages.agents.gates.llm_judge import step_10b_llm_judge
        state = make_base_state(artifacts=[VALID_ARTIFACT])
        result = step_10b_llm_judge(state)
        assert isinstance(result["judge_score"], float)

    def test_empty_content_artifact_scores_zero(self):
        from packages.agents.gates.llm_judge import step_10b_llm_judge
        state = make_base_state(artifacts=[{"type": "lesson", "content": ""}])
        result = step_10b_llm_judge(state)
        # Empty content → score 0.0 → fail
        assert result["fail_layer"] == "judge"


class TestExportReadiness:
    def test_passes_when_ready(self):
        from packages.agents.gates.export_readiness import step_11_export_readiness
        state = make_base_state(
            artifacts=[VALID_ARTIFACT],
            export_formats=["html"],
            judge_score=8.0,
        )
        result = step_11_export_readiness(state)
        assert result["export_ready"] is True

    def test_fails_with_no_artifacts(self):
        from packages.agents.gates.export_readiness import step_11_export_readiness
        state = make_base_state(artifacts=[], export_formats=["html"])
        result = step_11_export_readiness(state)
        assert result["export_ready"] is False
        assert result["fail_layer"] == "export"

    def test_fails_with_no_export_formats(self):
        from packages.agents.gates.export_readiness import step_11_export_readiness
        state = make_base_state(artifacts=[VALID_ARTIFACT], export_formats=[])
        result = step_11_export_readiness(state)
        assert result["export_ready"] is False

    def test_fails_when_judge_score_too_low(self):
        from packages.agents.gates.export_readiness import step_11_export_readiness
        state = make_base_state(
            artifacts=[VALID_ARTIFACT],
            export_formats=["html"],
            judge_score=5.0,
        )
        result = step_11_export_readiness(state)
        assert result["export_ready"] is False

    def test_passes_when_judge_score_none(self):
        from packages.agents.gates.export_readiness import step_11_export_readiness
        state = make_base_state(
            artifacts=[VALID_ARTIFACT],
            export_formats=["html"],
        )
        result = step_11_export_readiness(state)
        assert result["export_ready"] is True

    def test_fail_context_has_errors(self):
        from packages.agents.gates.export_readiness import step_11_export_readiness
        state = make_base_state(artifacts=[], export_formats=[])
        result = step_11_export_readiness(state)
        assert "fail_context" in result
        assert len(result["fail_context"]["errors"]) >= 1


class TestFactCheck:
    def test_clean_text_passes(self):
        from packages.agents.gates.fact_check import run_fact_check
        result = run_fact_check("Plants use sunlight to make food through photosynthesis.")
        assert result["passed"] is True

    def test_extracts_percentage_claims(self):
        from packages.agents.gates.fact_check.extractor import extract_claims
        claims = extract_claims("About 50% of the Earth's surface is ocean.")
        assert any("50%" in c["text"] for c in claims)

    def test_classifies_high_risk(self):
        from packages.agents.gates.fact_check.risk_classifier import classify_risk
        assert classify_risk({"text": "Alexander Graham Bell invented the telephone"}) == "HIGH"

    def test_classifies_low_risk(self):
        from packages.agents.gates.fact_check.risk_classifier import classify_risk
        assert classify_risk({"text": "15% of students"}) == "LOW"


class TestHTMLValidator:
    def test_valid_html_passes(self):
        from packages.agents.gates.presentation.html_validator import validate_html
        result = validate_html("<!DOCTYPE html><html><body>Hello</body></html>")
        assert result["passed"] is True

    def test_missing_doctype_fails(self):
        from packages.agents.gates.presentation.html_validator import validate_html
        result = validate_html("<html><body>Hello</body></html>")
        assert result["passed"] is False
        assert any("DOCTYPE" in e for e in result["errors"])

    def test_external_asset_fails(self):
        from packages.agents.gates.presentation.html_validator import validate_html
        result = validate_html('<!DOCTYPE html><html><body><img src="https://cdn.example.com/img.png"></body></html>')
        assert result["passed"] is False

    def test_no_doctype_check_when_disabled(self):
        from packages.agents.gates.presentation.html_validator import validate_html
        result = validate_html("<html><body>Hello</body></html>", block_missing_doctype=False)
        assert result["passed"] is True


class TestAnswerKeyGuard:
    def test_worksheet_with_answer_key_fails(self):
        from packages.agents.gates.presentation.answer_key_guard import check_answer_key_leakage
        artifact = {"type": "worksheet", "content": "Q1: 2+2=?\nAnswer Key: 4"}
        result = check_answer_key_leakage(artifact)
        assert result["passed"] is False

    def test_lesson_plan_passes_with_answer_key(self):
        from packages.agents.gates.presentation.answer_key_guard import check_answer_key_leakage
        artifact = {"type": "lesson_plan", "content": "Answer Key: provided in teacher guide"}
        result = check_answer_key_leakage(artifact)
        assert result["passed"] is True  # lesson_plan is teacher-facing

    def test_clean_worksheet_passes(self):
        from packages.agents.gates.presentation.answer_key_guard import check_answer_key_leakage
        artifact = {"type": "worksheet", "content": "Q1: What is 2+2? Write your answer below."}
        result = check_answer_key_leakage(artifact)
        assert result["passed"] is True

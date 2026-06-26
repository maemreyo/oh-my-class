"""Tests for quality gate nodes — schema, content review, LLM judge, export readiness."""
from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState



def make_base_state(**overrides) -> OhMyClassState:
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
    return cast("OhMyClassState", base)


COMPONENT_ARTIFACT = {
    "artifact_type": "lesson",
    "title": "Photosynthesis Components",
    "sections": [
        {
            "title": "Concept Map",
            "content": " ".join(
                [
                    "Students connect sunlight, water, carbon dioxide, glucose, "
                    "and oxygen using leaf evidence."
                ] * 8,
            ),
            "components": [
                {
                    "type": "concept_map",
                    "nodes": [
                        {"id": "sun", "label": "Sunlight"},
                        {"id": "leaf", "label": "Leaf"},
                    ],
                    "edges": [{"from": "sun", "to": "leaf", "label": "energy"}],
                },
            ],
        },
        {
            "title": "Check",
            "content": " ".join(
                [
                    "Students explain which gas plants absorb during photosynthesis "
                    "and why each distractor is wrong."
                ] * 8,
            ),
            "components": [
                {
                    "type": "question_card",
                    "id": 1,
                    "text": "Which gas do plants absorb during photosynthesis?",
                    "options": {
                        "A": "Oxygen",
                        "B": "Carbon dioxide",
                        "C": "Nitrogen",
                        "D": "Hydrogen",
                    },
                    "answer": "B",
                    "explain": "Plants use carbon dioxide to make glucose.",
                },
            ],
        },
        {
            "title": "Reflection",
            "content": " ".join(
                [
                    "Learners write one sentence linking light energy to glucose "
                    "production and oxygen release."
                ] * 8,
            ),
            "components": [
                {
                    "type": "callout",
                    "variant": "tip",
                    "body": "Reactants enter the leaf; products leave or store energy.",
                },
            ],
        },
    ],
}
HTML_ARTIFACT = {
    "artifact_type": "roadmap",
    "title": "HTML Roadmap",
    "sections": [
        {
            "content": (
                "<!DOCTYPE html><html><body>"
                "Plants use sunlight to make food.</body></html>"
            ),
        },
    ],
}


class TestSchemaValidator:
    def test_passes_with_valid_artifacts(self):
        from packages.agents.gates.schema_validator import step_09_schema_validate
        state = make_base_state(artifacts=[COMPONENT_ARTIFACT])
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
        state = make_base_state(artifacts=[{
            "artifact_type": "lesson",
            "title": "Missing Sections",
        }])
        result = step_09_schema_validate(state)
        assert result["schema_valid"] is False
        assert "fail_context" in result
        assert any("sections" in e for e in result["fail_context"]["errors"])

    def test_fails_with_empty_content(self):
        from packages.agents.gates.schema_validator import step_09_schema_validate
        state = make_base_state(artifacts=[{
            "artifact_type": "lesson",
            "title": "Empty Section",
            "sections": [{"content": "   "}],
        }])
        result = step_09_schema_validate(state)
        assert result["schema_valid"] is False

    def test_passes_components_only_section(self):
        from packages.agents.gates.schema_validator import step_09_schema_validate
        state = make_base_state(artifacts=[{
            "artifact_type": "lesson",
            "title": "Components Only Lesson",
            "sections": [
                {
                    "type": "teaching",
                    "title": "Concept Map",
                    "components": [
                        {
                            "type": "concept_map",
                            "nodes": [{"id": "leaf", "label": "Leaf"}],
                            "edges": [],
                        }
                    ],
                }
            ],
        }])
        result = step_09_schema_validate(state)
        assert result["schema_valid"] is True

    def test_fails_with_missing_type_key(self):
        from packages.agents.gates.schema_validator import step_09_schema_validate
        state = make_base_state(artifacts=[{
            "title": "Missing Type",
            "sections": [{"content": "some content"}],
        }])
        result = step_09_schema_validate(state)
        assert result["schema_valid"] is False

    def test_preserves_fail_count(self):
        from packages.agents.gates.schema_validator import step_09_schema_validate
        state = make_base_state(artifacts=[], fail_count=2)
        result = step_09_schema_validate(state)
        assert result["fail_count"] == 2  # validator reads, healing_node increments

    def test_multiple_valid_artifacts_pass(self):
        from packages.agents.gates.schema_validator import step_09_schema_validate
        state = make_base_state(artifacts=[COMPONENT_ARTIFACT, HTML_ARTIFACT])
        result = step_09_schema_validate(state)
        assert result["schema_valid"] is True


class TestContentReviewer:
    def test_passes_with_clean_content(self):
        from packages.agents.gates.content_reviewer import step_10_content_review
        state = make_base_state(artifacts=[COMPONENT_ARTIFACT])
        result = step_10_content_review(state)
        assert result["content_review_passed"] is True

    def test_fails_flat_content_without_components(self):
        from packages.agents.gates.content_reviewer import step_10_content_review
        state = make_base_state(artifacts=[{
            "artifact_type": "lesson",
            "title": "Flat Lesson",
            "sections": [{"content": "Plants use sunlight to make food."}],
        }])
        result = step_10_content_review(state)
        assert result["content_review_passed"] is False
        assert result["fail_layer"] == "content"

    def test_fails_with_blocked_content(self):
        from packages.agents.gates.content_reviewer import step_10_content_review
        artifact = {
            **COMPONENT_ARTIFACT,
            "sections": [
                {
                    **COMPONENT_ARTIFACT["sections"][0],
                    "content": "violence and gore in this lesson",
                },
                COMPONENT_ARTIFACT["sections"][1],
                COMPONENT_ARTIFACT["sections"][2],
            ],
        }
        state = make_base_state(artifacts=[artifact])
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
            "artifact_type": "roadmap",
            "title": "External HTML",
            "sections": [
                {
                    "content": (
                        '<!DOCTYPE html><html><body><img src="https://external.com/img.png">'
                        "</body></html>"
                    ),
                },
            ],
        }
        state = make_base_state(artifacts=[artifact])
        result = step_10_content_review(state)
        assert result["content_review_passed"] is False

    def test_fails_worksheet_with_answer_key(self):
        from packages.agents.gates.content_reviewer import step_10_content_review
        artifact = {
            "artifact_type": "worksheet",
            "title": "Math Worksheet",
            "sections": [{"content": "Question 1: What is 2+2?\nAnswer Key: 4"}],
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
        artifact = {
            **COMPONENT_ARTIFACT,
            "sections": [
                {
                    **COMPONENT_ARTIFACT["sections"][0],
                    "content": "explicit adult violence content",
                },
                COMPONENT_ARTIFACT["sections"][1],
                COMPONENT_ARTIFACT["sections"][2],
            ],
        }
        state = make_base_state(artifacts=[artifact])
        result = step_10_content_review(state)
        assert "fail_context" in result
        assert len(result["fail_context"]["errors"]) > 0


class TestLLMJudge:
    def test_passes_with_valid_artifacts(self):
        from packages.agents.gates.llm_judge import step_10b_llm_judge
        state = make_base_state(artifacts=[COMPONENT_ARTIFACT])
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
        state = make_base_state(artifacts=[COMPONENT_ARTIFACT])
        result = step_10b_llm_judge(state)
        assert isinstance(result["judge_score"], float)

    def test_empty_content_artifact_scores_zero(self):
        from packages.agents.gates.llm_judge import step_10b_llm_judge
        state = make_base_state(artifacts=[{
            "artifact_type": "lesson",
            "title": "Empty",
            "sections": [{"content": ""}],
        }])
        result = step_10b_llm_judge(state)
        assert result["fail_layer"] == "judge"


class TestExportReadiness:
    def test_passes_when_ready(self):
        from packages.agents.gates.export_readiness import step_11_export_readiness
        state = make_base_state(
            artifacts=[COMPONENT_ARTIFACT],
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
        state = make_base_state(artifacts=[COMPONENT_ARTIFACT], export_formats=[])
        result = step_11_export_readiness(state)
        assert result["export_ready"] is False

    def test_fails_when_judge_score_too_low(self):
        from packages.agents.gates.export_readiness import step_11_export_readiness
        state = make_base_state(
            artifacts=[COMPONENT_ARTIFACT],
            export_formats=["html"],
            judge_score=5.0,
        )
        result = step_11_export_readiness(state)
        assert result["export_ready"] is False

    def test_passes_when_judge_score_none(self):
        from packages.agents.gates.export_readiness import step_11_export_readiness
        state = make_base_state(
            artifacts=[COMPONENT_ARTIFACT],
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
        assert any("50%" in c.text for c in claims)

    def test_classifies_high_risk(self):
        from packages.agents.gates.fact_check.extractor import Claim
        from packages.agents.gates.fact_check.risk_classifier import classify_risk
        claim = Claim(text="Alexander Graham Bell", claim_type="named_entity",
                      context="Alexander Graham Bell invented the telephone")
        assert classify_risk(claim) == "HIGH"

    def test_classifies_low_risk(self):
        from packages.agents.gates.fact_check.extractor import Claim
        from packages.agents.gates.fact_check.risk_classifier import classify_risk
        claim = Claim(text="42", claim_type="number", context="42 students in the class")
        assert classify_risk(claim) == "LOW"


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

"""Tests for quality gate nodes — schema, content review, LLM judge, export readiness."""
from __future__ import annotations

from typing import Any

from packages.agents.gates.state import GateState


def make_base_state(**overrides: Any) -> GateState:
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
    return GateState(**{**base, **overrides})


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

    def test_missing_doctype_cannot_be_disabled(self):
        from packages.agents.gates.presentation.html_validator import validate_html
        result = validate_html("<html><body>Hello</body></html>")
        assert result["passed"] is False


class TestAnswerKeyGuard:
    def test_worksheet_with_answer_key_fails(self):
        from packages.agents.gates.presentation.answer_key_guard import check_answer_key_leakage
        artifact = {"artifact_type": "worksheet", "content": "Q1: 2+2=?\nAnswer Key: 4"}
        result = check_answer_key_leakage(artifact)
        assert result["passed"] is False

    def test_lesson_plan_passes_with_answer_key(self):
        from packages.agents.gates.presentation.answer_key_guard import check_answer_key_leakage
        artifact = {
            "artifact_type": "lesson_plan",
            "content": "Answer Key: provided in teacher guide",
        }
        result = check_answer_key_leakage(artifact)
        assert result["passed"] is True

    def test_clean_worksheet_passes(self):
        from packages.agents.gates.presentation.answer_key_guard import check_answer_key_leakage
        artifact = {
            "artifact_type": "worksheet",
            "content": "Q1: What is 2+2? Write your answer below.",
        }
        result = check_answer_key_leakage(artifact)
        assert result["passed"] is True

    def test_nested_quiz_component_answer_fails(self):
        from packages.agents.gates.presentation.answer_key_guard import check_answer_key_leakage
        artifact = {
            "artifact_type": "quiz",
            "sections": [
                {
                    "components": [
                        {
                            "type": "question_card",
                            "text": "2+2?",
                            "answer": "A",
                        }
                    ],
                }
            ],
        }
        result = check_answer_key_leakage(artifact)
        assert result["passed"] is False

    def test_nested_question_list_answer_fails(self):
        from packages.agents.gates.presentation.answer_key_guard import check_answer_key_leakage
        artifact = {
            "artifact_type": "drill",
            "sections": [
                {
                    "components": [
                        {
                            "type": "question_list",
                            "questions": [
                                {"text": "2+2?", "correct_answer": "A"},
                            ],
                        }
                    ],
                }
            ],
        }
        result = check_answer_key_leakage(artifact)
        assert result["passed"] is False

    def test_recap_student_type_with_answer_key_fails(self):
        from packages.agents.gates.presentation.answer_key_guard import check_answer_key_leakage
        artifact = {"artifact_type": "recap", "content": "Correct answer: B"}
        result = check_answer_key_leakage(artifact)
        assert result["passed"] is False


class TestStep12Finalize:
    """Tests for step_12_finalize URL checking and renderer optimization."""

    def test_component_url_blocked(self):
        """External URL inside a paragraph component blocks finalize."""
        from packages.agents.nodes.finalize import _check_no_external_urls

        artifact = {
            "artifact_type": "lesson",
            "title": "Test Lesson",
            "sections": [
                {
                    "title": "Intro",
                    "components": [
                        {
                            "type": "paragraph",
                            "text": "See the diagram at https://cdn.example.com/diagram.png",
                        },
                    ],
                },
            ],
        }
        errors = _check_no_external_urls(artifact)
        assert len(errors) == 1
        assert "https://cdn.example.com/diagram.png" in errors[0]

    def test_clean_component_passes(self):
        """Artifact with clean component-only content passes URL check."""
        from packages.agents.nodes.finalize import _check_no_external_urls

        artifact = {
            "artifact_type": "lesson",
            "title": "Clean Lesson",
            "sections": [
                {
                    "title": "Concept Map",
                    "components": [
                        {
                            "type": "concept_map",
                            "nodes": [{"id": "a", "label": "Sunlight"}],
                            "edges": [],
                        },
                    ],
                },
            ],
        }
        errors = _check_no_external_urls(artifact)
        assert errors == []

    def test_section_content_url_still_caught(self):
        """External URL in section.content is still caught (backward compat)."""
        from packages.agents.nodes.finalize import _check_no_external_urls

        artifact = {
            "artifact_type": "lesson",
            "title": "Legacy Lesson",
            "sections": [
                {
                    "content": "Visit https://external.com/resource for more info",
                },
            ],
        }
        errors = _check_no_external_urls(artifact)
        assert len(errors) == 1
        assert "https://external.com/resource" in errors[0]

    def test_teacher_only_section_urls_not_flagged(self):
        """URLs inside teacher_only sections are NOT flagged."""
        from packages.agents.nodes.finalize import _check_no_external_urls

        artifact = {
            "artifact_type": "lesson",
            "title": "Teacher Lesson",
            "sections": [
                {
                    "title": "Answer Key",
                    "teacher_only": True,
                    "content": "See https://teacher-only.com/answers for details",
                },
                {
                    "title": "Student Work",
                    "content": "Write your answer below.",
                },
            ],
        }
        errors = _check_no_external_urls(artifact)
        assert errors == []

    def test_component_callout_url_blocked(self):
        """URL inside a callout component body blocks finalize."""
        from packages.agents.nodes.finalize import _check_no_external_urls

        artifact = {
            "artifact_type": "worksheet",
            "title": "Test Worksheet",
            "sections": [
                {
                    "components": [
                        {
                            "type": "callout",
                            "variant": "tip",
                            "body": "Watch the video at https://youtube.com/watch?v=abc123",
                        },
                    ],
                },
            ],
        }
        errors = _check_no_external_urls(artifact)
        assert len(errors) == 1
        assert "https://youtube.com/watch?v=abc123" in errors[0]

    def test_step_12_finalize_returns_export_ready_false_on_url(self):
        """Full step_12_finalize returns export_ready=False when URLs found."""
        from unittest.mock import patch

        from packages.agents.nodes.finalize import step_12_finalize

        artifact = {
            "artifact_type": "lesson",
            "title": "Bad Lesson",
            "sections": [
                {
                    "components": [
                        {
                            "type": "paragraph",
                            "text": "Go to https://cdn.example.com/x.png",
                        },
                    ],
                },
            ],
        }
        state = make_base_state(
            artifacts=[artifact],
            export_formats=["html"],
        )
        with patch("packages.agents.nodes.finalize._build_renderer"):
            with patch("packages.agents.nodes.finalize._render_artifact_with_renderer"):
                result = step_12_finalize(state)
        assert result["export_ready"] is False
        assert result["fail_layer"] == "export"
        assert result["fail_type"] == "invariant"
        assert len(result["fail_context"]["errors"]) == 1

    def test_step_12_finalize_runs_build_once(self):
        """Renderer build is called once, not per artifact."""
        from unittest.mock import MagicMock, patch

        from packages.agents.nodes.finalize import step_12_finalize

        artifacts = [
            {
                "artifact_type": "lesson",
                "title": f"Lesson {i}",
                "sections": [{"content": f"Content for lesson {i}"}],
            }
            for i in range(3)
        ]
        state = make_base_state(
            artifacts=artifacts,
            export_formats=["html"],
        )
        mock_build = MagicMock()
        mock_render = MagicMock(return_value="<html></html>")
        with patch("packages.agents.nodes.finalize._build_renderer", mock_build):
            with patch("packages.agents.nodes.finalize._render_artifact_with_renderer", mock_render):
                result = step_12_finalize(state)
        assert mock_build.call_count == 1
        assert mock_render.call_count == 3
        assert len(result["exported_files"]) == 3

    def test_teacher_only_artifacts_skipped(self):
        """teacher_only artifacts are skipped in export."""
        from unittest.mock import MagicMock, patch

        from packages.agents.nodes.finalize import step_12_finalize

        artifacts = [
            {
                "artifact_type": "lesson",
                "title": "Student Lesson",
                "sections": [{"content": "Hello students"}],
            },
            {
                "artifact_type": "lesson",
                "title": "Teacher Guide",
                "teacher_only": True,
                "sections": [{"content": "Answer key here"}],
            },
        ]
        state = make_base_state(
            artifacts=artifacts,
            export_formats=["html"],
        )
        mock_render = MagicMock(return_value="<html></html>")
        with patch("packages.agents.nodes.finalize._build_renderer"):
            with patch("packages.agents.nodes.finalize._render_artifact_with_renderer", mock_render):
                result = step_12_finalize(state)
        assert mock_render.call_count == 1
        assert len(result["exported_files"]) == 1
        assert result["exported_files"][0]["title"] == "Student Lesson"


COMPONENT_ONLY_LESSON = {
    "artifact_type": "lesson",
    "title": "Component-Only Photosynthesis",
    "sections": [
        {
            "title": "Introduction",
            "components": [
                {
                    "type": "paragraph",
                    "text": (
                        "Photosynthesis is the process by which plants convert "
                        "sunlight, water, and carbon dioxide into glucose and "
                        "oxygen. This lesson explores each stage in detail."
                    ),
                },
                {
                    "type": "concept_map",
                    "nodes": [
                        {"id": "sun", "label": "Sunlight"},
                        {"id": "water", "label": "Water"},
                        {"id": "glucose", "label": "Glucose"},
                    ],
                    "edges": [
                        {"from": "sun", "to": "glucose", "label": "energy"},
                    ],
                },
            ],
        },
        {
            "title": "Key Concepts",
            "components": [
                {
                    "type": "paragraph",
                    "text": (
                        "During the light-dependent reactions, chlorophyll absorbs "
                        "sunlight and splits water molecules to release oxygen. "
                        "The energy is stored as ATP and NADPH for the next stage."
                    ),
                },
                {
                    "type": "question_card",
                    "text": "Which gas do plants release during photosynthesis?",
                    "options": {"A": "Carbon dioxide", "B": "Oxygen"},
                    "answer": "B",
                    "explain": "Plants release oxygen as a byproduct.",
                },
            ],
        },
        {
            "title": "Practice",
            "components": [
                {
                    "type": "callout",
                    "variant": "tip",
                    "body": (
                        "Remember: plants need carbon dioxide from the air and "
                        "water from the soil to produce glucose."
                    ),
                },
            ],
        },
    ],
}


class TestComponentFirstArtifacts:
    def test_component_only_lesson_passes_content_review(self):
        from packages.agents.gates.content_reviewer import step_10_content_review

        state = make_base_state(artifacts=[COMPONENT_ONLY_LESSON])
        result = step_10_content_review(state)
        assert result["content_review_passed"] is True

    def test_component_only_lesson_gets_nonzero_judge_score(self):
        from packages.agents.gates.llm_judge import step_10b_llm_judge

        state = make_base_state(artifacts=[COMPONENT_ONLY_LESSON])
        result = step_10b_llm_judge(state)
        assert result["judge_score"] > 0.0

    def test_empty_components_fails_content_review(self):
        from packages.agents.gates.content_reviewer import step_10_content_review

        artifact = {
            "artifact_type": "lesson",
            "title": "Empty Components",
            "sections": [
                {"components": []},
            ],
        }
        state = make_base_state(artifacts=[artifact])
        result = step_10_content_review(state)
        assert result["content_review_passed"] is False
        assert result["fail_layer"] == "content"

    def test_teacher_only_component_excluded_from_judge(self):
        from packages.agents.gates.llm_judge import _score_artifact

        artifact = {
            "artifact_type": "lesson",
            "title": "Teacher Weight Test",
            "sections": [
                {
                    "title": "Answer Key",
                    "teacher_only": True,
                    "components": [
                        {
                            "type": "paragraph",
                            "text": " ".join(
                                [
                                    "The correct answer is B because plants absorb "
                                    "carbon dioxide during photosynthesis."
                                ]
                                * 20,
                            ),
                        },
                    ],
                },
                {
                    "title": "Student Work",
                    "components": [
                        {
                            "type": "paragraph",
                            "text": "Name three products of photosynthesis.",
                        },
                    ],
                },
            ],
        }
        score = _score_artifact(artifact, None, component_score=5.0)
        # Teacher-only section text must NOT inflate word count;
        # if counted, score would be ~8.0; with exclusion, only section/structure bonuses
        assert score < 5.0

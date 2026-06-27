"""Deterministic prompt evaluation harness for seeded prompt modules.

Compiles judge, planner, and content-creator prompt modules from the
seed registry and verifies their structural invariants — expected
sections, schema metadata, content/compiled hashes — without any
network calls.  These fixtures serve as the regression baseline:
if a prompt module body drifts, the hash checks and section assertions
will catch it.

All tests use the seeded registry directly (no LLM, no I/O).
"""

from __future__ import annotations

import hashlib

import pytest

from packages.agents.llm.prompt_metadata import to_langfuse_metadata
from packages.agents.prompts.compiler import CompiledPrompt, PromptCompiler
from packages.agents.prompts.seed import (
    CONTENT_CREATOR_LESSON_V1,
    CONTENT_CREATOR_MCQ_V1,
    JUDGE_V1,
    PLANNER_V1,
    create_seeded_registry,
)

# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture()
def compiler() -> PromptCompiler:
    """A PromptCompiler backed by the seeded registry."""
    return PromptCompiler(create_seeded_registry())


# ── Eval: Planner ───────────────────────────────────────────────────────────


class TestPlannerEval:
    """Eval fixtures for planner_v1 prompt module."""

    def test_compilation_succeeds(self, compiler: PromptCompiler) -> None:
        result = compiler.compile(module_id="planner_v1", variables={})
        assert isinstance(result, CompiledPrompt)

    def test_expected_sections_present(self, compiler: PromptCompiler) -> None:
        result = compiler.compile(module_id="planner_v1", variables={})
        sections = result.metadata.sections
        assert any(s.startswith("Planner Agent") for s in sections)
        assert "Instructions" in sections
        assert "Constraints" in sections

    def test_content_hash_matches_seed(self, compiler: PromptCompiler) -> None:
        result = compiler.compile(module_id="planner_v1", variables={})
        assert result.metadata.content_hash == PLANNER_V1.content_hash

    def test_compiled_hash_is_sha256_of_body(self, compiler: PromptCompiler) -> None:
        result = compiler.compile(module_id="planner_v1", variables={})
        expected = hashlib.sha256(result.compiled_body.encode("utf-8")).hexdigest()
        assert result.metadata.compiled_hash == expected

    def test_output_schema_required_fields(self) -> None:
        schema = PLANNER_V1.output_schema
        assert schema is not None
        required = schema.get("required", [])
        assert "topic" in required
        assert "grade_level" in required
        assert "learning_objectives" in required

    def test_metadata_task_field(self) -> None:
        assert PLANNER_V1.metadata["task"] == "lesson_planning"

    def test_langfuse_metadata_round_trip(self, compiler: PromptCompiler) -> None:
        result = compiler.compile(module_id="planner_v1", variables={})
        langfuse = to_langfuse_metadata(result.metadata)
        assert langfuse["prompt_id"] == "planner_v1"
        assert langfuse["prompt_version"] == "1.0.0"
        assert langfuse["content_hash"] == PLANNER_V1.content_hash
        assert isinstance(langfuse["sections"], list)
        assert len(langfuse["sections"]) >= 2


# ── Eval: Judge ─────────────────────────────────────────────────────────────


class TestJudgeEval:
    """Eval fixtures for judge_v1 prompt module."""

    def test_compilation_succeeds(self, compiler: PromptCompiler) -> None:
        result = compiler.compile(module_id="judge_v1", variables={})
        assert isinstance(result, CompiledPrompt)

    def test_expected_sections_present(self, compiler: PromptCompiler) -> None:
        result = compiler.compile(module_id="judge_v1", variables={})
        sections = result.metadata.sections
        assert any(s.startswith("Reviewer Agent") for s in sections)
        assert "Scoring Layers" in sections
        assert "Rules" in sections
        assert any("Hard Blocks" in s for s in sections)

    def test_content_hash_matches_seed(self, compiler: PromptCompiler) -> None:
        result = compiler.compile(module_id="judge_v1", variables={})
        assert result.metadata.content_hash == JUDGE_V1.content_hash

    def test_compiled_hash_is_sha256_of_body(self, compiler: PromptCompiler) -> None:
        result = compiler.compile(module_id="judge_v1", variables={})
        expected = hashlib.sha256(result.compiled_body.encode("utf-8")).hexdigest()
        assert result.metadata.compiled_hash == expected

    def test_output_schema_required_fields(self) -> None:
        schema = JUDGE_V1.output_schema
        assert schema is not None
        required = schema.get("required", [])
        assert "overall_score" in required
        assert "layers" in required
        assert "critical_issues" in required

    def test_output_schema_score_range(self) -> None:
        schema = JUDGE_V1.output_schema
        assert schema is not None
        score_schema = schema["properties"]["overall_score"]
        assert score_schema["minimum"] == 0
        assert score_schema["maximum"] == 10

    def test_metadata_task_field(self) -> None:
        assert JUDGE_V1.metadata["task"] == "quality_review"

    def test_compiled_body_contains_scoring_weights(self, compiler: PromptCompiler) -> None:
        result = compiler.compile(module_id="judge_v1", variables={})
        assert "15%" in result.compiled_body
        assert "55%" in result.compiled_body
        assert "30%" in result.compiled_body


# ── Eval: Content Creator MCQ ───────────────────────────────────────────────


class TestContentCreatorMCQEval:
    """Eval fixtures for content_creator_mcq_v1 prompt module."""

    def test_compilation_succeeds(self, compiler: PromptCompiler) -> None:
        result = compiler.compile(module_id="content_creator_mcq_v1", variables={})
        assert isinstance(result, CompiledPrompt)

    def test_expected_sections_present(self, compiler: PromptCompiler) -> None:
        result = compiler.compile(module_id="content_creator_mcq_v1", variables={})
        sections = result.metadata.sections
        assert any(s.startswith("Content Creator") for s in sections)
        assert "Instructions" in sections
        assert "Hard Constraints" in sections

    def test_content_hash_matches_seed(self, compiler: PromptCompiler) -> None:
        result = compiler.compile(module_id="content_creator_mcq_v1", variables={})
        assert result.metadata.content_hash == CONTENT_CREATOR_MCQ_V1.content_hash

    def test_compiled_hash_is_sha256_of_body(self, compiler: PromptCompiler) -> None:
        result = compiler.compile(module_id="content_creator_mcq_v1", variables={})
        expected = hashlib.sha256(result.compiled_body.encode("utf-8")).hexdigest()
        assert result.metadata.compiled_hash == expected

    def test_output_schema_artifact_type_const(self) -> None:
        schema = CONTENT_CREATOR_MCQ_V1.output_schema
        assert schema is not None
        assert schema["properties"]["artifact_type"]["const"] == "quiz"

    def test_output_schema_required_fields(self) -> None:
        schema = CONTENT_CREATOR_MCQ_V1.output_schema
        assert schema is not None
        required = schema.get("required", [])
        assert "artifact_type" in required
        assert "title" in required
        assert "sections" in required

    def test_metadata_task_field(self) -> None:
        assert CONTENT_CREATOR_MCQ_V1.metadata["task"] == "mcq_generation"

    def test_metadata_artifact_type(self) -> None:
        assert CONTENT_CREATOR_MCQ_V1.metadata["artifact_type"] == "quiz"

    def test_compiled_body_contains_difficulty_distribution(self, compiler: PromptCompiler) -> None:
        result = compiler.compile(module_id="content_creator_mcq_v1", variables={})
        assert "recognition 40%" in result.compiled_body
        assert "comprehension 30%" in result.compiled_body


# ── Eval: Content Creator Lesson ────────────────────────────────────────────


class TestContentCreatorLessonEval:
    """Eval fixtures for content_creator_lesson_v1 prompt module."""

    def test_compilation_succeeds(self, compiler: PromptCompiler) -> None:
        result = compiler.compile(module_id="content_creator_lesson_v1", variables={})
        assert isinstance(result, CompiledPrompt)

    def test_expected_sections_present(self, compiler: PromptCompiler) -> None:
        result = compiler.compile(module_id="content_creator_lesson_v1", variables={})
        sections = result.metadata.sections
        assert any(s.startswith("Content Creator") for s in sections)
        assert "Instructions" in sections
        assert "Hard Constraints" in sections

    def test_content_hash_matches_seed(self, compiler: PromptCompiler) -> None:
        result = compiler.compile(module_id="content_creator_lesson_v1", variables={})
        assert result.metadata.content_hash == CONTENT_CREATOR_LESSON_V1.content_hash

    def test_compiled_hash_is_sha256_of_body(self, compiler: PromptCompiler) -> None:
        result = compiler.compile(module_id="content_creator_lesson_v1", variables={})
        expected = hashlib.sha256(result.compiled_body.encode("utf-8")).hexdigest()
        assert result.metadata.compiled_hash == expected

    def test_output_schema_required_fields(self) -> None:
        schema = CONTENT_CREATOR_LESSON_V1.output_schema
        assert schema is not None
        required = schema.get("required", [])
        assert "artifact_type" in required
        assert "title" in required
        assert "sections" in required

    def test_metadata_task_field(self) -> None:
        assert CONTENT_CREATOR_LESSON_V1.metadata["task"] == "lesson_generation"

    def test_metadata_artifact_type(self) -> None:
        assert CONTENT_CREATOR_LESSON_V1.metadata["artifact_type"] == "lesson"


# ── Eval: Cross-module invariants ───────────────────────────────────────────


class TestCrossModuleInvariants:
    """Invariants that hold across all four seeded modules."""

    MODULE_IDS: list[str] = [
        "planner_v1",
        "judge_v1",
        "content_creator_mcq_v1",
        "content_creator_lesson_v1",
    ]

    def test_all_have_output_schema(self) -> None:
        from packages.agents.prompts.seed import SEED_MODULES

        for module in SEED_MODULES:
            assert module.output_schema is not None, (
                f"Missing output_schema in '{module.id}'"
            )

    def test_all_metadata_non_empty(self) -> None:
        from packages.agents.prompts.seed import SEED_MODULES

        for module in SEED_MODULES:
            assert module.metadata, f"Empty metadata in '{module.id}'"

    def test_all_compile_without_variables(self, compiler: PromptCompiler) -> None:
        for mid in self.MODULE_IDS:
            result = compiler.compile(module_id=mid, variables={})
            assert result.compiled_body, f"Empty compiled_body for '{mid}'"

    def test_all_metadata_prompt_ids_match(self, compiler: PromptCompiler) -> None:
        for mid in self.MODULE_IDS:
            result = compiler.compile(module_id=mid, variables={})
            assert result.metadata.prompt_id == mid
            assert result.metadata.prompt_version == "1.0.0"

    def test_all_compiled_bodies_start_with_header(self, compiler: PromptCompiler) -> None:
        for mid in self.MODULE_IDS:
            result = compiler.compile(module_id=mid, variables={})
            assert result.compiled_body.startswith("# "), (
                f"'{mid}' compiled body does not start with a Markdown header"
            )

    def test_no_variable_placeholders_remain(self, compiler: PromptCompiler) -> None:
        for mid in self.MODULE_IDS:
            result = compiler.compile(module_id=mid, variables={})
            assert "{{" not in result.compiled_body, (
                f"'{mid}' compiled body still contains {{{{ placeholders"
            )

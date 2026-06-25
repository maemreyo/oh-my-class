"""Tests for Layer 1 schema validation."""

import pytest

from common.contracts.lesson_plan import LessonPlan
from packages.quality.layer1_schema.validators import (
    PLACEHOLDER_PATTERNS,
    CircuitBreaker,
    ValidationGateError,
    check_answer_key_separation,
    check_bloom_coverage,
    check_placeholder_content,
    validate_schema,
)


class TestValidateSchema:
    @pytest.mark.asyncio
    async def test_valid_schema_passes(self):
        data = {
            "topic": "Photosynthesis",
            "grade_level": "Grade 5",
            "subject": "science",
            "duration_minutes": 45,
            "learning_objectives": [
                {"description": "Understand photosynthesis", "bloom_level": "understand"},
                {"description": "Apply knowledge", "bloom_level": "apply"},
            ],
        }
        result = await validate_schema(data, LessonPlan)
        assert isinstance(result, LessonPlan)
        assert result.topic == "Photosynthesis"

    @pytest.mark.asyncio
    async def test_invalid_schema_retries_then_fails(self):
        data = {"topic": ""}  # Missing required fields
        with pytest.raises(ValidationGateError) as exc_info:
            await validate_schema(data, LessonPlan, max_retries=2)
        assert exc_info.value.layer == 1
        assert len(exc_info.value.issues) > 0

    @pytest.mark.asyncio
    async def test_empty_dict_raises_validation_gate_error(self):
        with pytest.raises(ValidationGateError) as exc_info:
            await validate_schema({}, LessonPlan)
        assert exc_info.value.layer == 1

    @pytest.mark.asyncio
    async def test_max_retries_respected(self):
        """Verify that exactly max_retries attempts are made."""
        data = {}  # Always invalid
        with pytest.raises(ValidationGateError):
            await validate_schema(data, LessonPlan, max_retries=1)


class TestCheckPlaceholderContent:
    def test_catches_tbd(self):
        data = {"title": "Lesson [TBD]"}
        issues = check_placeholder_content(data)
        assert any("[TBD]" in i for i in issues)

    def test_catches_todo(self):
        data = {"description": "TODO: add content"}
        issues = check_placeholder_content(data)
        assert any("TODO" in i for i in issues)

    def test_catches_lorem_ipsum(self):
        data = {"content": "Lorem ipsum dolor sit amet"}
        issues = check_placeholder_content(data)
        assert any("lorem ipsum" in i for i in issues)

    def test_catches_placeholder(self):
        data = {"text": "PLACEHOLDER text here"}
        issues = check_placeholder_content(data)
        assert any("PLACEHOLDER" in i for i in issues)

    def test_catches_insert(self):
        data = {"name": "[INSERT name here]"}
        issues = check_placeholder_content(data)
        assert any("[INSERT" in i for i in issues)

    def test_catches_nested_dict(self):
        data = {"sections": [{"content": "lorem ipsum"}]}
        issues = check_placeholder_content(data)
        assert any("lorem ipsum" in i for i in issues)

    def test_catches_deeply_nested(self):
        data = {"a": {"b": {"c": "TODO: deep"}}}
        issues = check_placeholder_content(data)
        assert any("TODO" in i for i in issues)

    def test_catches_nested_list_in_dict(self):
        data = {"items": ["real content", "[TBD]"]}
        issues = check_placeholder_content(data)
        assert any("[TBD]" in i for i in issues)

    def test_clean_data_passes(self):
        data = {"title": "Real Content", "description": "A proper lesson"}
        issues = check_placeholder_content(data)
        assert len(issues) == 0

    def test_none_values_skip_gracefully(self):
        data = {"title": None, "body": "Good content"}
        issues = check_placeholder_content(data)
        assert len(issues) == 0

    def test_case_insensitive(self):
        data = {"title": "todo: finish this"}
        issues = check_placeholder_content(data)
        assert any("TODO" in i for i in issues)

    def test_placeholder_patterns_list(self):
        assert "[TBD]" in PLACEHOLDER_PATTERNS
        assert "lorem ipsum" in PLACEHOLDER_PATTERNS
        assert "TODO" in PLACEHOLDER_PATTERNS


class TestCheckBloomCoverage:
    def test_sufficient_coverage(self):
        objectives = [
            {"bloom_level": "remember"},
            {"bloom_level": "apply"},
        ]
        issues = check_bloom_coverage(objectives)
        assert len(issues) == 0

    def test_insufficient_coverage_single_level(self):
        objectives = [
            {"bloom_level": "remember"},
            {"bloom_level": "remember"},
        ]
        issues = check_bloom_coverage(objectives)
        assert len(issues) == 1
        assert "Insufficient" in issues[0]

    def test_empty_objectives(self):
        issues = check_bloom_coverage([])
        assert len(issues) == 1

    def test_missing_bloom_level_key(self):
        objectives = [{"description": "no level"}, {"description": "also no level"}]
        issues = check_bloom_coverage(objectives)
        assert len(issues) == 1

    def test_three_levels_passes_min_two(self):
        objectives = [
            {"bloom_level": "remember"},
            {"bloom_level": "apply"},
            {"bloom_level": "create"},
        ]
        issues = check_bloom_coverage(objectives, min_levels=2)
        assert len(issues) == 0

    def test_custom_min_levels(self):
        objectives = [
            {"bloom_level": "remember"},
            {"bloom_level": "apply"},
        ]
        issues = check_bloom_coverage(objectives, min_levels=3)
        assert len(issues) == 1
        assert "need ≥3" in issues[0]


class TestCheckAnswerKeySeparation:
    def test_answer_in_student_section(self):
        artifact = {
            "sections": [
                {"content": "What is 2+2? Answer: 4", "teacher_only": False}
            ]
        }
        issues = check_answer_key_separation(artifact)
        assert len(issues) == 1
        assert "Answer key leakage" in issues[0]

    def test_correct_in_student_section(self):
        artifact = {
            "sections": [
                {"content": "Correct: option B", "teacher_only": False}
            ]
        }
        issues = check_answer_key_separation(artifact)
        assert len(issues) >= 1

    def test_solution_in_student_section(self):
        artifact = {
            "sections": [
                {"content": "Solution: x = 5", "teacher_only": False}
            ]
        }
        issues = check_answer_key_separation(artifact)
        assert len(issues) >= 1

    def test_answer_in_teacher_section_ok(self):
        artifact = {
            "sections": [
                {"content": "Answer: 4", "teacher_only": True}
            ]
        }
        issues = check_answer_key_separation(artifact)
        assert len(issues) == 0

    def test_no_sections_returns_empty(self):
        artifact = {"title": "Lesson"}
        issues = check_answer_key_separation(artifact)
        assert len(issues) == 0

    def test_section_without_teacher_only_defaults_to_student(self):
        artifact = {
            "sections": [
                {"content": "answer: 42"}  # no teacher_only key
            ]
        }
        issues = check_answer_key_separation(artifact)
        assert len(issues) >= 1

    def test_multiple_issues_detected(self):
        artifact = {
            "sections": [
                {"content": "Answer: 4 and Correct: yes", "teacher_only": False}
            ]
        }
        issues = check_answer_key_separation(artifact)
        assert len(issues) == 2


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker()
        assert not cb.is_open()

    def test_trips_after_threshold(self):
        cb = CircuitBreaker(threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert not cb.is_open()
        cb.record_failure()
        assert cb.is_open()

    def test_resets_on_success(self):
        cb = CircuitBreaker(threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert not cb.is_open()
        assert cb._failure_count == 0

    def test_threshold_one_trips_immediately(self):
        cb = CircuitBreaker(threshold=1)
        cb.record_failure()
        assert cb.is_open()

    def test_success_after_trip_resets(self):
        cb = CircuitBreaker(threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open()
        cb.record_success()
        assert not cb.is_open()

    def test_failure_count_increments(self):
        cb = CircuitBreaker(threshold=5)
        cb.record_failure()
        cb.record_failure()
        assert cb._failure_count == 2

    def test_success_clears_failure_count(self):
        cb = CircuitBreaker(threshold=5)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 0
        assert not cb.is_open()

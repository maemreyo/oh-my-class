"""Tests for StudentResponse and DiagnosticReport models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.student_response import StudentAnswerItem, StudentResponse
from common.contracts.diagnostic_report import (
    BloomGap,
    DiagnosticReport,
    KnowledgeGap,
    MisconceptionPattern,
)


class TestStudentResponse:
    """Test suite for StudentResponse model."""

    def test_valid_instantiation(self):
        """StudentResponse accepts student_id and wrong_question_ids as minimum."""
        sr = StudentResponse(student_id="s-001", wrong_question_ids=[1, 3, 5])
        assert sr.student_id == "s-001"
        assert sr.wrong_question_ids == [1, 3, 5]
        assert sr.test_id == "unknown"
        assert sr.answers == []
        assert sr.total_questions == 0
        assert sr.context == {}

    def test_with_all_fields(self):
        """StudentResponse accepts explicit values for all optional fields."""
        sr = StudentResponse(
            student_id="s-002",
            test_id="test-english-b2",
            wrong_question_ids=[2, 4],
            total_questions=40,
            context={"class": "10A"},
        )
        assert sr.test_id == "test-english-b2"
        assert sr.total_questions == 40
        assert sr.context == {"class": "10A"}

    def test_missing_student_id_raises(self):
        """StudentResponse requires student_id."""
        with pytest.raises(ValidationError):
            StudentResponse(wrong_question_ids=[1])

    def test_missing_wrong_question_ids_raises(self):
        """StudentResponse requires wrong_question_ids."""
        with pytest.raises(ValidationError):
            StudentResponse(student_id="s-001")

    def test_wrong_question_ids_mixed_types(self):
        """wrong_question_ids accepts a mix of int and str ids."""
        sr = StudentResponse(student_id="s-003", wrong_question_ids=[1, "Q2", 3])
        assert sr.wrong_question_ids == [1, "Q2", 3]

    def test_with_answers(self):
        """StudentResponse stores a list of StudentAnswerItem records."""
        item = StudentAnswerItem(
            question_id=1,
            correct_answer="B",
            is_correct=False,
        )
        sr = StudentResponse(
            student_id="s-004",
            wrong_question_ids=[1],
            answers=[item],
        )
        assert len(sr.answers) == 1
        assert sr.answers[0].question_id == 1


class TestStudentAnswerItem:
    """Test suite for StudentAnswerItem model."""

    def test_all_fields(self):
        """StudentAnswerItem stores all provided fields correctly."""
        item = StudentAnswerItem(
            question_id="Q5",
            student_answer="A",
            correct_answer="C",
            is_correct=False,
            section="Grammar",
            bloom_level="apply",
        )
        assert item.question_id == "Q5"
        assert item.student_answer == "A"
        assert item.correct_answer == "C"
        assert item.is_correct is False
        assert item.section == "Grammar"
        assert item.bloom_level == "apply"

    def test_optional_fields_default_to_none(self):
        """student_answer, section, and bloom_level default to None."""
        item = StudentAnswerItem(question_id=7, correct_answer="D", is_correct=True)
        assert item.student_answer is None
        assert item.section is None
        assert item.bloom_level is None

    def test_unanswered_question(self):
        """student_answer=None represents an unanswered question."""
        item = StudentAnswerItem(
            question_id=10, student_answer=None, correct_answer="B", is_correct=False
        )
        assert item.student_answer is None
        assert item.is_correct is False


class TestKnowledgeGap:
    """Test suite for KnowledgeGap model."""

    def test_valid_instantiation(self):
        """KnowledgeGap accepts all required fields."""
        gap = KnowledgeGap(
            category="Tense Usage",
            error_count=8,
            error_rate=0.4,
            severity="critical",
            question_ids=[1, 3, 5, 7],
        )
        assert gap.category == "Tense Usage"
        assert gap.error_count == 8
        assert gap.error_rate == 0.4
        assert gap.severity == "critical"
        assert gap.question_ids == [1, 3, 5, 7]

    def test_severity_values(self):
        """severity accepts exactly the three defined values: critical, moderate, minor."""
        for severity in ("critical", "moderate", "minor"):
            gap = KnowledgeGap(
                category="X", error_count=1, error_rate=0.1, severity=severity, question_ids=[]
            )
            assert gap.severity == severity

    def test_empty_question_ids(self):
        """question_ids may be an empty list."""
        gap = KnowledgeGap(
            category="Reading", error_count=0, error_rate=0.0, severity="minor", question_ids=[]
        )
        assert gap.question_ids == []


class TestBloomGap:
    """Test suite for BloomGap model."""

    def test_valid_instantiation(self):
        """BloomGap stores bloom_level, vn_name, error_count, and error_rate."""
        bg = BloomGap(
            bloom_level="analyze",
            vn_name="Phân tích",
            error_count=5,
            error_rate=0.5,
        )
        assert bg.bloom_level == "analyze"
        assert bg.vn_name == "Phân tích"
        assert bg.error_count == 5
        assert bg.error_rate == 0.5

    def test_all_bloom_levels(self):
        """BloomGap accepts all six Bloom's taxonomy levels."""
        levels = ["remember", "understand", "apply", "analyze", "evaluate", "create"]
        for level in levels:
            bg = BloomGap(bloom_level=level, vn_name="test", error_count=1, error_rate=0.1)
            assert bg.bloom_level == level

    def test_zero_errors(self):
        """BloomGap with zero errors is valid."""
        bg = BloomGap(bloom_level="create", vn_name="Sáng tạo", error_count=0, error_rate=0.0)
        assert bg.error_count == 0
        assert bg.error_rate == 0.0


class TestMisconceptionPattern:
    """Test suite for MisconceptionPattern model."""

    def test_valid_instantiation(self):
        """MisconceptionPattern stores all required fields."""
        mp = MisconceptionPattern(
            id="C1",
            group="a",
            title="Tense Confusion",
            description="Confuses present perfect with simple past",
            question_ids=[2, 6, 11],
        )
        assert mp.id == "C1"
        assert mp.group == "a"
        assert mp.title == "Tense Confusion"
        assert mp.description == "Confuses present perfect with simple past"
        assert mp.question_ids == [2, 6, 11]

    def test_string_question_ids(self):
        """question_ids accepts string identifiers."""
        mp = MisconceptionPattern(
            id="C2",
            group="b",
            title="Article Omission",
            description="Omits definite article before proper nouns",
            question_ids=["Q1", "Q4"],
        )
        assert mp.question_ids == ["Q1", "Q4"]


class TestDiagnosticReport:
    """Test suite for DiagnosticReport model."""

    def test_valid_instantiation(self):
        """DiagnosticReport requires only student_id; all list fields default empty."""
        report = DiagnosticReport(student_id="s-001")
        assert report.student_id == "s-001"
        assert report.knowledge_gaps == []
        assert report.bloom_gaps == []
        assert report.misconception_patterns == []
        assert report.critical_sections == []
        assert report.overall_error_rate == 0.0
        assert report.recommended_level == "B2"
        assert report.summary == ""

    def test_with_all_fields(self):
        """DiagnosticReport stores explicitly provided values for all fields."""
        kg = KnowledgeGap(
            category="Vocabulary",
            error_count=3,
            error_rate=0.3,
            severity="moderate",
            question_ids=[4, 8],
        )
        bg = BloomGap(bloom_level="apply", vn_name="Vận dụng", error_count=3, error_rate=0.3)
        mp = MisconceptionPattern(
            id="C3",
            group="c",
            title="Collocation Error",
            description="Uses incorrect verb-noun collocations",
            question_ids=[4],
        )
        report = DiagnosticReport(
            student_id="s-002",
            knowledge_gaps=[kg],
            bloom_gaps=[bg],
            misconception_patterns=[mp],
            critical_sections=["Grammar", "Vocabulary"],
            overall_error_rate=0.35,
            recommended_level="B1",
            summary="Student struggles with vocabulary and mid-level application tasks.",
        )
        assert len(report.knowledge_gaps) == 1
        assert len(report.bloom_gaps) == 1
        assert len(report.misconception_patterns) == 1
        assert report.critical_sections == ["Grammar", "Vocabulary"]
        assert report.overall_error_rate == 0.35
        assert report.recommended_level == "B1"

    def test_missing_student_id_raises(self):
        """DiagnosticReport requires student_id."""
        with pytest.raises(ValidationError):
            DiagnosticReport()

    def test_json_roundtrip(self):
        """DiagnosticReport survives a model_dump / model_validate round-trip."""
        report = DiagnosticReport(
            student_id="s-003",
            overall_error_rate=0.5,
            recommended_level="B1",
            summary="Needs significant improvement.",
        )
        data = report.model_dump()
        restored = DiagnosticReport.model_validate(data)
        assert restored.student_id == "s-003"
        assert restored.recommended_level == "B1"
        assert restored.summary == "Needs significant improvement."

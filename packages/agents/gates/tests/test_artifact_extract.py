"""Tests for artifact text/URL extraction helpers (component-first content)."""
from __future__ import annotations

from packages.agents.gates.artifact_extract import (
    extract_external_urls,
    extract_student_text,
    extract_student_text_from_sections,
    extract_urls_from_sections,
)


# ── extract_student_text ─────────────────────────────────────────────────────


class TestExtractStudentTextContent:
    """Backward compatibility: section.content string extraction."""

    def test_returns_empty_for_no_sections(self):
        assert extract_student_text({}) == ""

    def test_returns_empty_for_empty_sections(self):
        assert extract_student_text({"sections": []}) == ""

    def test_extracts_single_content_string(self):
        artifact = {"sections": [{"content": "Hello world"}]}
        assert extract_student_text(artifact) == "Hello world"

    def test_joins_multiple_content_strings(self):
        artifact = {"sections": [
            {"content": "First section"},
            {"content": "Second section"},
        ]}
        result = extract_student_text(artifact)
        assert result == "First section\nSecond section"

    def test_skips_whitespace_only_content(self):
        artifact = {"sections": [
            {"content": "   "},
            {"content": "Real content"},
        ]}
        assert extract_student_text(artifact) == "Real content"

    def test_strips_whitespace_from_content(self):
        artifact = {"sections": [{"content": "  spaced  "}]}
        assert extract_student_text(artifact) == "spaced"

    def test_skips_non_string_content(self):
        artifact = {"sections": [
            {"content": 42},
            {"content": None},
            {"content": ["a", "b"]},
        ]}
        assert extract_student_text(artifact) == ""


class TestExtractStudentTextComponents:
    """Component-first extraction for typed component dicts."""

    def test_paragraph_component(self):
        artifact = {"sections": [{"components": [
            {"type": "paragraph", "text": "A paragraph."},
        ]}]}
        assert extract_student_text(artifact) == "A paragraph."

    def test_heading_component(self):
        artifact = {"sections": [{"components": [
            {"type": "heading", "level": 2, "text": "Section Title"},
        ]}]}
        assert extract_student_text(artifact) == "Section Title"

    def test_callout_component_uses_body(self):
        artifact = {"sections": [{"components": [
            {"type": "callout", "variant": "tip", "body": "Helpful tip here."},
        ]}]}
        assert extract_student_text(artifact) == "Helpful tip here."

    def test_question_card_text_and_explain(self):
        artifact = {"sections": [{"components": [
            {"type": "question_card", "id": 1, "text": "What is 2+2?",
             "options": {"A": "3", "B": "4"}, "answer": "B",
             "explain": "Addition basics."},
        ]}]}
        result = extract_student_text(artifact)
        assert "What is 2+2?" in result
        assert "Addition basics." in result

    def test_question_list_nested_questions(self):
        artifact = {"sections": [{"components": [
            {"type": "question_list", "title": "Quiz", "group": "a",
             "section_key": "q", "questions": [
                 {"id": 1, "text": "Q1?", "options": {}, "answer": "A",
                  "explain": "Because."},
                 {"id": 2, "text": "Q2?", "options": {}, "answer": "B",
                  "explain": "Reason."},
             ]},
        ]}]}
        result = extract_student_text(artifact)
        assert "Q1?" in result
        assert "Because." in result
        assert "Q2?" in result
        assert "Reason." in result

    def test_ordered_list_items(self):
        artifact = {"sections": [{"components": [
            {"type": "ordered_list", "items": ["Step 1", "Step 2"]},
        ]}]}
        result = extract_student_text(artifact)
        assert "Step 1" in result
        assert "Step 2" in result

    def test_unordered_list_items(self):
        artifact = {"sections": [{"components": [
            {"type": "unordered_list", "items": ["Apple", "Banana"]},
        ]}]}
        result = extract_student_text(artifact)
        assert "Apple" in result
        assert "Banana" in result

    def test_unknown_type_falls_back_to_text_key(self):
        artifact = {"sections": [{"components": [
            {"type": "custom_widget", "text": "Fallback text"},
        ]}]}
        assert extract_student_text(artifact) == "Fallback text"

    def test_unknown_type_falls_back_to_body_key(self):
        artifact = {"sections": [{"components": [
            {"type": "custom_widget", "body": "Body fallback"},
        ]}]}
        assert extract_student_text(artifact) == "Body fallback"

    def test_dict_without_type_uses_text_key(self):
        artifact = {"sections": [{"components": [
            {"text": "No type field"},
        ]}]}
        assert extract_student_text(artifact) == "No type field"

    def test_dict_without_type_returns_empty_when_no_text_keys(self):
        artifact = {"sections": [{"components": [
            {"foo": "bar", "baz": 42},
        ]}]}
        assert extract_student_text(artifact) == ""

    def test_mixed_content_and_components(self):
        artifact = {"sections": [{"content": "Plain text", "components": [
            {"type": "paragraph", "text": "Component text."},
        ]}]}
        result = extract_student_text(artifact)
        assert "Plain text" in result
        assert "Component text." in result


class TestExtractStudentTextTeacherOnly:
    """Teacher-only sections are excluded from student-facing text."""

    def test_teacher_only_section_excluded(self):
        artifact = {"sections": [
            {"content": "Student content"},
            {"content": "Answer key", "teacher_only": True},
        ]}
        result = extract_student_text(artifact)
        assert "Student content" in result
        assert "Answer key" not in result

    def test_teacher_only_with_components_excluded(self):
        artifact = {"sections": [
            {"components": [{"type": "paragraph", "text": "Student part"}]},
            {"components": [{"type": "paragraph", "text": "Answers"}],
             "teacher_only": True},
        ]}
        result = extract_student_text(artifact)
        assert "Student part" in result
        assert "Answers" not in result

    def test_all_sections_teacher_only_returns_empty(self):
        artifact = {"sections": [
            {"content": "Key 1", "teacher_only": True},
            {"content": "Key 2", "teacher_only": True},
        ]}
        assert extract_student_text(artifact) == ""

    def test_teacher_only_false_treated_as_student(self):
        artifact = {"sections": [
            {"content": "Visible", "teacher_only": False},
        ]}
        assert extract_student_text(artifact) == "Visible"


# ── extract_student_text_from_sections ───────────────────────────────────────


class TestExtractStudentTextFromSections:
    """Direct test of the sections-level helper."""

    def test_handles_non_dict_sections(self):
        result = extract_student_text_from_sections(["not a dict", 42, None])  # type: ignore[list-item]
        assert result == ""

    def test_single_section_with_content(self):
        result = extract_student_text_from_sections([{"content": "Hello"}])
        assert result == "Hello"

    def test_excludes_teacher_only(self):
        result = extract_student_text_from_sections([
            {"content": "Open"},
            {"content": "Secret", "teacher_only": True},
        ])
        assert result == "Open"


# ── URL extraction ──────────────────────────────────────────────────────────


class TestExtractExternalUrls:
    """URL extraction from artifacts and sections."""

    def test_no_urls_returns_empty(self):
        artifact = {"sections": [{"content": "No links here"}]}
        assert extract_external_urls(artifact) == []

    def test_extracts_url_from_content(self):
        artifact = {"sections": [
            {"content": "Visit https://example.com for more."},
        ]}
        assert extract_external_urls(artifact) == ["https://example.com"]

    def test_extracts_url_from_paragraph_component(self):
        artifact = {"sections": [{"components": [
            {"type": "paragraph", "text": "See http://school.edu/page"},
        ]}]}
        assert extract_external_urls(artifact) == ["http://school.edu/page"]

    def test_extracts_url_from_callout_body(self):
        artifact = {"sections": [{"components": [
            {"type": "callout", "variant": "note",
             "body": "Reference at https://docs.example.org/guide"},
        ]}]}
        assert extract_external_urls(artifact) == ["https://docs.example.org/guide"]

    def test_extracts_url_from_question_card(self):
        artifact = {"sections": [{"components": [
            {"type": "question_card", "id": 1, "text": "Check https://quiz.com",
             "options": {}, "answer": "A",
             "explain": "See https://explain.com for details."},
        ]}]}
        urls = extract_external_urls(artifact)
        assert "https://quiz.com" in urls
        assert "https://explain.com" in urls

    def test_deduplicates_urls_preserving_order(self):
        artifact = {"sections": [
            {"content": "Link to https://a.com"},
            {"content": "Also https://a.com and https://b.com"},
        ]}
        urls = extract_external_urls(artifact)
        assert urls == ["https://a.com", "https://b.com"]

    def test_skips_teacher_only_for_urls(self):
        artifact = {"sections": [
            {"content": "Student sees https://open.com"},
            {"content": "Teacher has https://secret.com", "teacher_only": True},
        ]}
        urls = extract_external_urls(artifact)
        assert urls == ["https://open.com"]
        assert "https://secret.com" not in urls

    def test_returns_empty_for_no_sections(self):
        assert extract_external_urls({}) == []

    def test_returns_empty_for_empty_sections(self):
        assert extract_external_urls({"sections": []}) == []


class TestExtractUrlsFromSections:
    """Direct test of the sections-level URL helper."""

    def test_extracts_from_mixed_components(self):
        sections = [
            {"content": "Text with https://first.com"},
            {"components": [
                {"type": "paragraph", "text": "And https://second.com"},
            ]},
        ]
        urls = extract_urls_from_sections(sections)
        assert urls == ["https://first.com", "https://second.com"]

    def test_empty_sections_returns_empty(self):
        assert extract_urls_from_sections([]) == []

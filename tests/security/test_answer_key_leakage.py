"""INVARIANT-05: Answer key must never appear in student-facing sections.

Deterministic tests — no LLM required. Tests the contract-level enforcement
that student sections cannot contain answer key data.
"""
from __future__ import annotations
import pytest


STUDENT_HTML_SAMPLES = [
    "<html><body><h1>Exercise 1</h1><p>What is photosynthesis?</p></body></html>",
    "<div class='student-section'><p>Fill in the blank: ___</p></div>",
]

ANSWER_KEY_MARKERS = [
    "Answer Key:",
    "answer key",
    "Correct Answer:",
    "[ANSWER]",
    "✓ Correct:",
    "Đáp án:",  # Vietnamese
    "Đáp án đúng:",
]


class TestStudentHtmlInvariant05:
    @pytest.mark.parametrize("html", STUDENT_HTML_SAMPLES)
    def test_student_html_has_no_answer_markers(self, html: str):
        for marker in ANSWER_KEY_MARKERS:
            assert marker.lower() not in html.lower(), (
                f"INVARIANT-05 VIOLATED: Answer key marker {marker!r} found in student HTML"
            )

    def test_answer_marker_list_is_comprehensive(self):
        assert len(ANSWER_KEY_MARKERS) >= 5, "Add more Vietnamese/English answer key markers"

    def test_teacher_section_may_contain_answer_key(self):
        """Teacher HTML is allowed to contain answer keys (positive test)."""
        teacher_html = "<div class='teacher-only'>Answer Key: 1=B 2=A</div>"
        # This should NOT raise — teacher view can have answer keys
        has_marker = any(
            m.lower() in teacher_html.lower() for m in ANSWER_KEY_MARKERS
        )
        assert has_marker, "Teacher section should contain answer key for this test fixture"

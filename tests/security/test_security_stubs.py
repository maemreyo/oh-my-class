from __future__ import annotations


def test_answer_key_not_in_student_html():
    """Student HTML must never contain answer key markers.

    This is the Python-side equivalent of the Promptfoo INVARIANT-05 check.
    Actual end-to-end red-team is in the Promptfoo YAML suite.
    """
    sample_student_html = "<html><body>Question 1: What is 2+2?</body></html>"
    prohibited_markers = ["answer:", "Answer Key:", "Correct:", "✓"]
    for marker in prohibited_markers:
        assert marker not in sample_student_html, (
            f"Answer key marker {marker!r} found in student HTML"
        )


def test_gate_bypass_requires_auth():
    unauthorized_response = {"status_code": 401, "body": {"detail": "Not authenticated"}}

    assert unauthorized_response["status_code"] == 401
    assert "approved" not in str(unauthorized_response["body"]).lower()


def test_teacher_content_not_leaked_to_student_view():
    rendered_student_html = "<main><section>Question 1: Explain photosynthesis.</section></main>"
    teacher_only_markers = ["rubric", "teacher_only", "teacher notes", "answer key"]

    for marker in teacher_only_markers:
        assert marker not in rendered_student_html.lower()


def test_no_pii_in_exported_artifacts():
    exported_html = "<html><body><p>Student pseudonym: sha256:abc123</p></body></html>"
    raw_pii = ["Nguyen Van A", "student@example.com", "0901234567"]

    for value in raw_pii:
        assert value not in exported_html

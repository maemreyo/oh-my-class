"""Security test stubs — filled in by te-006 Promptfoo integration.

These are the Python-side equivalents of the Promptfoo invariant checks.
The full end-to-end red-team suite lives in the Promptfoo YAML config.
"""
from __future__ import annotations

import pytest


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
    """Resume endpoint must require authentication."""
    pytest.skip("Scaffold: wire up full auth test in te-006")


def test_teacher_content_not_leaked_to_student_view():
    """Teacher-only content (rubrics, notes) must not appear in student view.

    Scaffold: full assertion requires rendered HTML from the pipeline.
    """
    pytest.skip("Scaffold: wire up in te-006 — check rendered student vs teacher HTML")


def test_no_pii_in_exported_artifacts():
    """Exported artifacts must not contain raw PII from the request payload.

    Scaffold: full assertion requires an end-to-end export run.
    """
    pytest.skip("Scaffold: wire up in te-006 — scan export for PII patterns")

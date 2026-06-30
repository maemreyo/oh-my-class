from __future__ import annotations

from packages.quality.layer2_content.pii import scrub_pii


def test_contact_info_urls_and_social_handles_are_redacted() -> None:
    text = "Email learner@example.com, phone 0912 345 678, site https://school.example/class, handle @student_case."

    result = scrub_pii(text)

    assert "learner@example.com" not in result.value
    assert "0912 345 678" not in result.value
    assert "https://school.example/class" not in result.value
    assert "@student_case" not in result.value
    assert result.audit_event.redaction_counts["email"] == 1
    assert result.audit_event.redaction_counts["phone"] == 1
    assert result.audit_event.redaction_counts["url"] == 1
    assert result.audit_event.redaction_counts["social_handle"] == 1


def test_student_and_school_ids_are_redacted() -> None:
    result = scrub_pii("student id STU-2026-A17 from school code SCH-88B should not appear.")

    assert "STU-2026-A17" not in result.value
    assert "SCH-88B" not in result.value
    assert result.audit_event.redaction_counts["student_id"] == 1
    assert result.audit_event.redaction_counts["school_id"] == 1

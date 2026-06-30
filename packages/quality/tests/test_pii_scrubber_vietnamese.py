from __future__ import annotations

from packages.quality.layer2_content.pii import scrub_pii


def test_vietnamese_names_are_redacted_with_counts() -> None:
    result = scrub_pii("Lớp có Nguyễn Văn An và Trần Thị Bình cần bài tập riêng.")

    assert "Nguyễn Văn An" not in result.value
    assert "Trần Thị Bình" not in result.value
    assert result.audit_event.redaction_counts["person_name"] == 2
    assert len(result.audit_event.token_hashes["person_name"]) == 2


def test_low_confidence_name_is_surfaced_for_teacher_confirmation() -> None:
    result = scrub_pii("Một bạn tên Khoa thường nhầm thì hiện tại hoàn thành.")

    assert result.audit_event.redaction_counts == {}
    assert len(result.low_confidence_matches) == 1
    assert len(result.audit_event.low_confidence_hashes) == 1

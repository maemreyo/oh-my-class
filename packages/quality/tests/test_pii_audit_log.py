from __future__ import annotations

from packages.quality.layer2_content.pii import scrub_pii


def test_audit_event_contains_only_counts_and_hashes() -> None:
    result = scrub_pii("Nguyễn Văn An uses an@example.com.")
    audit_text = str(result.audit_event)

    assert result.audit_event.redaction_counts["person_name"] == 1
    assert result.audit_event.redaction_counts["email"] == 1
    assert "Nguyễn Văn An" not in audit_text
    assert "an@example.com" not in audit_text
    assert "[REDACTED_PERSON_NAME_1]" not in audit_text
    assert all(len(token_hash) == 64 for hashes in result.audit_event.token_hashes.values() for token_hash in hashes)

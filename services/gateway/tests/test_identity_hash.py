"""Tests for identity hashing utility."""

from services.gateway.identity_hash import (
    hash_identity,
    hash_teacher_id,
    hash_email,
    hash_class_id,
    langfuse_safe_metadata,
)


class TestHashIdentity:
    def test_returns_16_char_hex(self):
        result = hash_identity("test-123")
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self):
        assert hash_identity("abc") == hash_identity("abc")

    def test_different_inputs_differ(self):
        assert hash_identity("abc") != hash_identity("def")

    def test_salt_changes_result(self):
        assert hash_identity("abc", salt="x") != hash_identity("abc", salt="y")


class TestHashFunctions:
    def test_hash_teacher_id(self):
        result = hash_teacher_id("teacher-123")
        assert len(result) == 16

    def test_hash_email(self):
        result = hash_email("test@example.com")
        assert len(result) == 16
        assert "test" not in result  # No raw email in hash

    def test_hash_class_id(self):
        result = hash_class_id("class-456")
        assert len(result) == 16


class TestLangfuseSafeMetadata:
    def test_includes_hashed_id(self):
        meta = langfuse_safe_metadata("teacher-123")
        assert "hashed_id" in meta
        assert meta["hashed_id"] == hash_teacher_id("teacher-123")

    def test_includes_hashed_email_when_provided(self):
        meta = langfuse_safe_metadata("t-1", email="test@example.com")
        assert "hashed_email" in meta

    def test_omits_email_when_not_provided(self):
        meta = langfuse_safe_metadata("t-1")
        assert "hashed_email" not in meta

    def test_includes_hashed_class_when_provided(self):
        meta = langfuse_safe_metadata("t-1", class_id="c-1")
        assert "hashed_class" in meta

    def test_includes_hashed_org_when_provided(self):
        meta = langfuse_safe_metadata("t-1", org_id="org-1")
        assert "hashed_org" in meta

    def test_never_includes_raw_pii(self):
        meta = langfuse_safe_metadata(
            "teacher-123",
            email="test@example.com",
            class_id="class-456",
            org_id="org-789",
        )
        meta_str = str(meta)
        assert "teacher-123" not in meta_str
        assert "test@example.com" not in meta_str
        assert "class-456" not in meta_str
        assert "org-789" not in meta_str
"""Test-enforced contracts for export-layer data structures.

These snapshot tests freeze the shape of FORMAT_REQUIREMENTS and
INVERSE_THINKING_FORMAT_SUPPORT so any code change that adds, removes,
or re-keys these dicts is caught immediately — preventing docs-vs-code drift.
"""

from __future__ import annotations


class TestFormatRequirementsSnapshot:
    """FORMAT_REQUIREMENTS maps each export format → required artifact types."""

    def test_format_requirements_keys_are_stable(self) -> None:
        from packages.quality.layer6_export.export_validator import FORMAT_REQUIREMENTS

        expected_keys = frozenset({
            "html",
            "gift",
            "h5p",
            "qti",
            "anki_apkg",
            "flashcard_tsv",
        })
        actual_keys = frozenset(FORMAT_REQUIREMENTS.keys())
        assert actual_keys == expected_keys, (
            f"FORMAT_REQUIREMENTS keys changed: added={actual_keys - expected_keys}, "
            f"removed={expected_keys - actual_keys}"
        )

    def test_html_requires_lesson(self) -> None:
        from packages.quality.layer6_export.export_validator import FORMAT_REQUIREMENTS

        assert FORMAT_REQUIREMENTS["html"] == ["lesson"]

    def test_gift_requires_quiz(self) -> None:
        from packages.quality.layer6_export.export_validator import FORMAT_REQUIREMENTS

        assert FORMAT_REQUIREMENTS["gift"] == ["quiz"]

    def test_h5p_requires_quiz_and_drill(self) -> None:
        from packages.quality.layer6_export.export_validator import FORMAT_REQUIREMENTS

        assert FORMAT_REQUIREMENTS["h5p"] == ["quiz", "drill"]

    def test_qti_requires_quiz(self) -> None:
        from packages.quality.layer6_export.export_validator import FORMAT_REQUIREMENTS

        assert FORMAT_REQUIREMENTS["qti"] == ["quiz"]

    def test_anki_apkg_requires_flashcard_deck(self) -> None:
        from packages.quality.layer6_export.export_validator import FORMAT_REQUIREMENTS

        assert FORMAT_REQUIREMENTS["anki_apkg"] == ["flashcard_deck"]

    def test_flashcard_tsv_requires_flashcard_deck(self) -> None:
        from packages.quality.layer6_export.export_validator import FORMAT_REQUIREMENTS

        assert FORMAT_REQUIREMENTS["flashcard_tsv"] == ["flashcard_deck"]

    def test_all_required_values_are_non_empty_lists(self) -> None:
        from packages.quality.layer6_export.export_validator import FORMAT_REQUIREMENTS

        for fmt, required in FORMAT_REQUIREMENTS.items():
            assert isinstance(required, list), f"{fmt}: expected list, got {type(required)}"
            assert len(required) > 0, f"{fmt}: required artifact types list is empty"
            for artifact_type in required:
                assert isinstance(artifact_type, str), (
                    f"{fmt}: artifact type should be str, got {type(artifact_type)}"
                )

    def test_format_requirements_is_frozen_snapshot(self) -> None:
        """Prevent accidental mutation of the shared constant."""
        from packages.quality.layer6_export.export_validator import FORMAT_REQUIREMENTS

        # Should be a plain dict (not frozen), but this test documents the
        # expectation that no external code mutates it at runtime.
        original = dict(FORMAT_REQUIREMENTS)
        # The snapshot: if this test breaks, someone changed the constant.
        assert original == {
            "html": ["lesson"],
            "gift": ["quiz"],
            "h5p": ["quiz", "drill"],
            "qti": ["quiz"],
            "anki_apkg": ["flashcard_deck"],
            "flashcard_tsv": ["flashcard_deck"],
        }


class TestInverseThinkingFormatSupportSnapshot:
    """INVERSE_THINKING_FORMAT_SUPPORT maps format → support level string."""

    def test_inverse_thinking_format_support_keys_are_stable(self) -> None:
        from packages.quality.layer6_export.export_validator import (
            INVERSE_THINKING_FORMAT_SUPPORT,
        )

        expected_keys = frozenset({
            "html",
            "gift",
            "h5p",
            "qti",
            "google_forms",
        })
        actual_keys = frozenset(INVERSE_THINKING_FORMAT_SUPPORT.keys())
        assert actual_keys == expected_keys, (
            f"INVERSE_THINKING_FORMAT_SUPPORT keys changed: "
            f"added={actual_keys - expected_keys}, removed={expected_keys - actual_keys}"
        )

    def test_html_is_supported(self) -> None:
        from packages.quality.layer6_export.export_validator import (
            INVERSE_THINKING_FORMAT_SUPPORT,
        )

        assert INVERSE_THINKING_FORMAT_SUPPORT["html"] == "supported"

    def test_gift_is_supported(self) -> None:
        from packages.quality.layer6_export.export_validator import (
            INVERSE_THINKING_FORMAT_SUPPORT,
        )

        assert INVERSE_THINKING_FORMAT_SUPPORT["gift"] == "supported"

    def test_h5p_is_unsupported(self) -> None:
        from packages.quality.layer6_export.export_validator import (
            INVERSE_THINKING_FORMAT_SUPPORT,
        )

        assert INVERSE_THINKING_FORMAT_SUPPORT["h5p"] == "unsupported"

    def test_qti_is_supported(self) -> None:
        from packages.quality.layer6_export.export_validator import (
            INVERSE_THINKING_FORMAT_SUPPORT,
        )

        assert INVERSE_THINKING_FORMAT_SUPPORT["qti"] == "supported"

    def test_google_forms_is_lossy(self) -> None:
        from packages.quality.layer6_export.export_validator import (
            INVERSE_THINKING_FORMAT_SUPPORT,
        )

        assert INVERSE_THINKING_FORMAT_SUPPORT["google_forms"] == "lossy"

    def test_all_support_levels_are_valid(self) -> None:
        from packages.quality.layer6_export.export_validator import (
            INVERSE_THINKING_FORMAT_SUPPORT,
        )

        valid_levels = frozenset({"supported", "unsupported", "lossy"})
        for fmt, level in INVERSE_THINKING_FORMAT_SUPPORT.items():
            assert level in valid_levels, (
                f"{fmt}: invalid support level '{level}', expected one of {valid_levels}"
            )

    def test_inverse_thinking_support_is_frozen_snapshot(self) -> None:
        """Full snapshot of the dict — catches any key or value change."""
        from packages.quality.layer6_export.export_validator import (
            INVERSE_THINKING_FORMAT_SUPPORT,
        )

        assert dict(INVERSE_THINKING_FORMAT_SUPPORT) == {
            "html": "supported",
            "gift": "supported",
            "h5p": "unsupported",
            "qti": "supported",
            "google_forms": "lossy",
        }

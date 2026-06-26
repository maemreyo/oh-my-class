"""Tests for artifact — ArtifactContent schema and component validation."""

import pytest
from pydantic import ValidationError

from common.contracts.artifact import ArtifactContent


def _make(**overrides):
    base = {
        "artifact_type": "lesson",
        "title": "Test Lesson",
        "sections": [{"title": "Intro"}],
    }
    base.update(overrides)
    return base


class TestArtifactContentBasics:
    """Minimal ArtifactContent fields still validate."""

    def test_valid_minimal(self):
        art = ArtifactContent(**_make())
        assert art.artifact_type == "lesson"
        assert art.theme == "default"

    def test_rejects_empty_sections(self):
        with pytest.raises(ValidationError):
            ArtifactContent(**_make(sections=[]))

    def test_rejects_short_title(self):
        with pytest.raises(ValidationError):
            ArtifactContent(**_make(title="Hi"))


class TestComponentValidation:
    """Section ``components`` dicts are validated when typed."""

    # ── valid components pass ──────────────────────────────────────────

    def test_valid_heading_component(self):
        art = ArtifactContent(**_make(
            sections=[{
                "title": "Intro",
                "components": [
                    {"type": "heading", "level": 2, "text": "Hello"},
                ],
            }],
        ))
        assert len(art.sections) == 1

    def test_valid_paragraph_component(self):
        art = ArtifactContent(**_make(
            sections=[{
                "title": "Body",
                "components": [
                    {"type": "paragraph", "text": "Some text."},
                ],
            }],
        ))
        assert art.sections[0]["components"][0]["type"] == "paragraph"

    def test_valid_mixed_components(self):
        art = ArtifactContent(**_make(
            sections=[{
                "title": "Mixed",
                "components": [
                    {"type": "heading", "level": 1, "text": "Title"},
                    {"type": "paragraph", "text": "Body text."},
                    {"type": "callout", "variant": "tip", "body": "Tip!"},
                ],
            }],
        ))
        assert len(art.sections[0]["components"]) == 3

    def test_valid_table_component(self):
        art = ArtifactContent(**_make(
            sections=[{
                "title": "Data",
                "components": [
                    {"type": "table", "columns": ["A", "B"], "rows": [["1", "2"]]},
                ],
            }],
        ))
        assert art.sections[0]["components"][0]["type"] == "table"

    def test_valid_stat_grid_component(self):
        art = ArtifactContent(**_make(
            sections=[{
                "title": "Stats",
                "components": [
                    {"type": "stat_grid", "stats": [
                        {"label": "Score", "value": "95"},
                    ]},
                ],
            }],
        ))
        assert art.sections[0]["components"][0]["type"] == "stat_grid"

    # ── backward compatibility: no components / non-list / non-dict ────

    def test_section_without_components(self):
        art = ArtifactContent(**_make(
            sections=[{"title": "Plain section"}],
        ))
        assert "components" not in art.sections[0]

    def test_non_list_components_skipped(self):
        art = ArtifactContent(**_make(
            sections=[{"title": "S", "components": "not a list"}],
        ))
        assert art.sections[0]["components"] == "not a list"

    def test_non_dict_entries_in_components_skipped(self):
        art = ArtifactContent(**_make(
            sections=[{
                "title": "S",
                "components": ["string", 42, None, True],
            }],
        ))
        assert len(art.sections[0]["components"]) == 4

    def test_dict_without_type_field_skipped(self):
        art = ArtifactContent(**_make(
            sections=[{
                "title": "S",
                "components": [{"no_type": "value"}],
            }],
        ))
        assert art.sections[0]["components"][0]["no_type"] == "value"

    def test_multiple_sections_mixed_component_presence(self):
        art = ArtifactContent(**_make(
            sections=[
                {"title": "With", "components": [
                    {"type": "heading", "level": 3, "text": "Hi"},
                ]},
                {"title": "Without"},
                {"title": "String", "components": "skip"},
            ],
        ))
        assert len(art.sections) == 3

    # ── invalid components rejected ────────────────────────────────────

    def test_invalid_component_type_rejected(self):
        with pytest.raises(ValidationError, match="sections\\[0\\]\\.components\\[0\\]"):
            ArtifactContent(**_make(
                sections=[{
                    "title": "S",
                    "components": [
                        {"type": "heading", "level": 99, "text": "Bad level"},
                    ],
                }],
            ))

    def test_missing_required_field_rejected(self):
        with pytest.raises(ValidationError, match="sections\\[0\\]"):
            ArtifactContent(**_make(
                sections=[{
                    "title": "S",
                    "components": [
                        {"type": "paragraph"},
                    ],
                }],
            ))

    def test_unknown_component_type_rejected(self):
        with pytest.raises(ValidationError, match="sections\\[0\\]"):
            ArtifactContent(**_make(
                sections=[{
                    "title": "S",
                    "components": [
                        {"type": "nonexistent_widget"},
                    ],
                }],
            ))

    def test_invalid_enum_value_rejected(self):
        with pytest.raises(ValidationError, match="sections\\[0\\]"):
            ArtifactContent(**_make(
                sections=[{
                    "title": "S",
                    "components": [
                        {"type": "callout", "variant": "banana", "body": "x"},
                    ],
                }],
            ))

    def test_error_message_includes_section_and_component_index(self):
        with pytest.raises(ValidationError, match=r"sections\[2\]\.components\[1\]"):
            ArtifactContent(**_make(
                sections=[
                    {"title": "A"},
                    {"title": "B"},
                    {
                        "title": "C",
                        "components": [
                            {"type": "paragraph", "text": "ok"},
                            {"type": "callout", "variant": "INVALID", "body": "bad"},
                        ],
                    },
                ],
            ))

"""Tests for RCM component registry — completeness, integrity, and helpers."""

from __future__ import annotations

import pytest

from common.contracts.components.registry import (
    COMPONENT_REGISTRY,
    PedagogicalIntent,
    get_component_types_for_intent,
    get_entries_for_artifact,
    get_entry,
    get_minimum_components,
)

# ---------------------------------------------------------------------------
# Registry structural integrity
# ---------------------------------------------------------------------------


class TestRegistryIntegrity:
    """Core invariants that must hold for the registry to be trustworthy."""

    def test_no_duplicate_component_types(self) -> None:
        """Each component type must appear exactly once."""
        types = [e.type for e in COMPONENT_REGISTRY]
        assert len(types) == len(set(types)), (
            f"Duplicate types: {[t for t in types if types.count(t) > 1]}"
        )

    def test_all_entries_have_non_empty_artifact_types(self) -> None:
        """Every entry must be valid in at least one artifact."""
        for entry in COMPONENT_REGISTRY:
            assert len(entry.artifact_types) > 0, (
                f"{entry.type} has no artifact_types"
            )

    def test_all_entries_have_description(self) -> None:
        for entry in COMPONENT_REGISTRY:
            assert entry.description, f"{entry.type} missing description"

    def test_all_entries_have_required_fields(self) -> None:
        for entry in COMPONENT_REGISTRY:
            assert len(entry.required_fields) > 0, (
                f"{entry.type} has no required_fields"
            )

    def test_min_per_artifact_non_negative(self) -> None:
        for entry in COMPONENT_REGISTRY:
            assert entry.min_per_artifact >= 0, (
                f"{entry.type} has negative min_per_artifact"
            )

    def test_max_per_artifact_at_least_min(self) -> None:
        for entry in COMPONENT_REGISTRY:
            if entry.max_per_artifact is not None:
                assert entry.max_per_artifact >= entry.min_per_artifact, (
                    f"{entry.type}: max < min"
                )


# ---------------------------------------------------------------------------
# Template existence — dispatcher-supported types must have templates on disk
# ---------------------------------------------------------------------------

_DISPATCHER_TYPES = {
    "heading", "paragraph", "callout", "table", "stat_grid",
    "pattern_grid", "trait_grid", "taxonomy_grid", "phase_timeline",
    "flow_step", "question_card", "question_list", "alert",
    "vocab_cluster", "contrastive_pairs", "phrasal_verb_cluster",
    "film_clip_activity", "roleplay_script", "active_recall_prompt",
    "hw_list",
}


class TestTemplateExistence:
    """Dispatcher-supported types must have a template file on disk."""

    @pytest.mark.parametrize("ctype", sorted(_DISPATCHER_TYPES))
    def test_dispatcher_type_has_template(self, ctype: str) -> None:
        entry = get_entry(ctype)
        assert entry.template is not None, (
            f"Dispatcher type {ctype!r} has no template in registry"
        )


# ---------------------------------------------------------------------------
# Specific entry metadata
# ---------------------------------------------------------------------------


class TestQuestionCardMetadata:
    def test_required_fields(self) -> None:
        entry = get_entry("question_card")
        assert entry.type == "question_card"
        assert "id" in entry.required_fields
        assert "text" in entry.required_fields
        assert "options" in entry.required_fields
        assert "answer" in entry.required_fields
        assert "explain" in entry.required_fields

    def test_intent_is_assessment(self) -> None:
        entry = get_entry("question_card")
        assert entry.intent == PedagogicalIntent.ASSESSMENT

    def test_artifact_types(self) -> None:
        entry = get_entry("question_card")
        assert "lesson" in entry.artifact_types
        assert "quiz" in entry.artifact_types
        assert "drill" in entry.artifact_types
        assert "worksheet" in entry.artifact_types


# ---------------------------------------------------------------------------
# Lesson artifact entries
# ---------------------------------------------------------------------------


class TestLessonEntries:
    def test_heading_required_in_lesson(self) -> None:
        entry = get_entry("heading")
        assert "lesson" in entry.artifact_types
        assert entry.min_per_artifact >= 1

    def test_lesson_has_structural_components(self) -> None:
        entries = get_entries_for_artifact("lesson")
        intents = {e.intent for e in entries}
        assert PedagogicalIntent.STRUCTURAL in intents
        assert PedagogicalIntent.ASSESSMENT in intents

    def test_lesson_has_all_intents(self) -> None:
        """Lesson is the richest artifact — should touch most intents."""
        entries = get_entries_for_artifact("lesson")
        intents = {e.intent for e in entries}
        assert PedagogicalIntent.KNOWLEDGE_ORGANIZATION in intents
        assert PedagogicalIntent.MEDIA_ACTIVITY in intents
        assert PedagogicalIntent.RECALL in intents
        assert PedagogicalIntent.ADMINISTRATIVE in intents
        assert PedagogicalIntent.TIMELINE_FLOW in intents


# ---------------------------------------------------------------------------
# Minimum component requirements per artifact
# ---------------------------------------------------------------------------


class TestMinimumComponents:
    def test_lesson_requires_heading(self) -> None:
        mins = get_minimum_components("lesson")
        assert "heading" in mins
        assert mins["heading"] >= 1

    def test_quiz_requires_nothing_beyond_heading(self) -> None:
        """Quiz minimum is heading only — questions are 0+."""
        mins = get_minimum_components("quiz")
        assert "heading" in mins

    def test_worksheet_has_heading_minimum(self) -> None:
        mins = get_minimum_components("worksheet")
        assert "heading" in mins

    def test_drill_has_heading_minimum(self) -> None:
        mins = get_minimum_components("drill")
        assert "heading" in mins

    def test_recap_has_heading_minimum(self) -> None:
        mins = get_minimum_components("recap")
        assert "heading" in mins

    def test_infographic_has_heading_minimum(self) -> None:
        mins = get_minimum_components("infographic")
        assert "heading" in mins

    def test_all_artifacts_have_heading(self) -> None:
        """Every student-facing artifact type must allow heading."""
        for artifact in ("lesson", "worksheet", "quiz", "drill", "recap", "infographic"):
            entry = get_entry("heading")
            assert artifact in entry.artifact_types, (
                f"heading not in artifact_types for {artifact}"
            )


# ---------------------------------------------------------------------------
# get_entry helpers
# ---------------------------------------------------------------------------


class TestGetEntry:
    def test_existing_type(self) -> None:
        entry = get_entry("heading")
        assert entry.type == "heading"

    def test_unknown_type_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="Unknown component type"):
            get_entry("nonexistent_widget")

    def test_error_message_lists_available_types(self) -> None:
        with pytest.raises(KeyError, match="Available:"):
            get_entry("fake_type")


class TestGetEntriesForArtifact:
    def test_quiz_entries(self) -> None:
        entries = get_entries_for_artifact("quiz")
        types = {e.type for e in entries}
        assert "question_card" in types
        assert "question_list" in types
        assert "heading" in types

    def test_infographic_entries(self) -> None:
        entries = get_entries_for_artifact("infographic")
        types = {e.type for e in entries}
        assert "stat_grid" in types
        assert "trait_grid" in types
        assert "taxonomy_grid" in types

    def test_unknown_artifact_returns_empty(self) -> None:
        entries = get_entries_for_artifact("nonexistent_artifact")
        assert entries == []


class TestGetComponentTypesForIntent:
    def test_assessment_intent(self) -> None:
        types = get_component_types_for_intent(PedagogicalIntent.ASSESSMENT)
        assert "question_card" in types
        assert "question_list" in types

    def test_structural_intent(self) -> None:
        types = get_component_types_for_intent(PedagogicalIntent.STRUCTURAL)
        assert "heading" in types
        assert "paragraph" in types
        assert "callout" in types
        assert "ordered_list" in types
        assert "unordered_list" in types

    def test_returns_sorted(self) -> None:
        types = get_component_types_for_intent(PedagogicalIntent.DATA_DISPLAY)
        assert types == sorted(types)


# ---------------------------------------------------------------------------
# PedagogicalIntent enum
# ---------------------------------------------------------------------------


class TestPedagogicalIntent:
    def test_all_intents_used(self) -> None:
        """Every intent enum value must be represented in the registry."""
        used = {e.intent for e in COMPONENT_REGISTRY}
        for intent in PedagogicalIntent:
            assert intent in used, f"Intent {intent.value!r} unused in registry"

    def test_is_string_enum(self) -> None:
        assert isinstance(PedagogicalIntent.ASSESSMENT, str)
        assert PedagogicalIntent.ASSESSMENT == "assessment"

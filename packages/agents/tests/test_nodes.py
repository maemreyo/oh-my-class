"""Unit tests for pipeline node functions (preflight, quickstart, pack_scope, visual_engine)."""

from __future__ import annotations

from typing import Any, cast

import pytest

from packages.agents.nodes.finalize import step_12_finalize
from packages.agents.nodes.pack_scope import step_05_pack_scope
from packages.agents.nodes.preflight import step_01_preflight
from packages.agents.nodes.quickstart import step_02_quickstart
from packages.agents.nodes.visual_engine import step_06_visual_engine
from packages.agents.state import OhMyClassState  # noqa: TC001  needed at runtime (cast)


def _base_state(**overrides: Any) -> OhMyClassState:
    base: dict[str, Any] = {
        "raw_request": "Teach photosynthesis in grade 5",
        "teacher_id": "t-001",
        "class_info": {"grade": 5, "subject": "science"},
        "run_id": "run-001",
        "blueprint_approved": False,
        "quality_passed": False,
        "teacher_approved": False,
        "revision_count": 0,
        "artifact_types": [],
        "theme": "default",
        "artifacts": [],
        "export_formats": ["html"],
        "exported_files": [],
        "current_step": 0,
        "tokens_used": 0,
        "cost_usd": 0.0,
        "research_policy": "standard",
    }
    base.update(overrides)
    return cast("OhMyClassState", base)


# ── Preflight ─────────────────────────────────────────────────────────────────


class TestPreflightAccepts:
    def test_accepts_valid_request(self):
        state = _base_state(raw_request="Teach photosynthesis in grade 5")
        result = step_01_preflight(state)
        assert result["current_step"] == 1

    def test_accepts_exactly_ten_chars(self):
        state = _base_state(raw_request="x" * 10)
        result = step_01_preflight(state)
        assert result["current_step"] == 1

    def test_strips_whitespace_before_length_check(self):
        state = _base_state(raw_request="  hi  ")
        with pytest.raises(ValueError, match="at least 10 characters"):
            step_01_preflight(state)


class TestPreflightRejects:
    def test_rejects_empty_request(self):
        state = _base_state(raw_request="")
        with pytest.raises(ValueError, match="raw_request is required"):
            step_01_preflight(state)

    def test_rejects_short_request(self):
        state = _base_state(raw_request="too short")
        with pytest.raises(ValueError, match="at least 10 characters"):
            step_01_preflight(state)

    def test_rejects_whitespace_only(self):
        state = _base_state(raw_request="   ")
        with pytest.raises(ValueError, match="raw_request is required"):
            step_01_preflight(state)

    def test_rejects_missing_raw_request(self):
        state = _base_state()
        state.pop("raw_request", None)
        with pytest.raises(ValueError, match="raw_request is required"):
            step_01_preflight(state)


# ── Quickstart ────────────────────────────────────────────────────────────────


class TestQuickstartSetsDefaults:
    def test_sets_defaults_when_state_is_empty(self):
        state = _base_state()
        # Force empty values for fields under test
        state["artifact_types"] = []
        state["theme"] = ""
        state["research_policy"] = ""

        result = step_02_quickstart(state)
        assert result["artifact_types"] == ["lesson", "worksheet", "quiz"]
        assert result["theme"] == "default"
        assert result["research_policy"] == "standard"
        assert result["current_step"] == 2

    def test_sets_current_step(self):
        state = _base_state()
        result = step_02_quickstart(state)
        assert result["current_step"] == 2


class TestQuickstartPreservesExisting:
    def test_preserves_existing_artifact_types(self):
        state = _base_state(artifact_types=["lesson", "drill"])
        result = step_02_quickstart(state)
        assert "artifact_types" not in result

    def test_preserves_existing_theme(self):
        state = _base_state(theme="ocean")
        result = step_02_quickstart(state)
        assert "theme" not in result

    def test_preserves_existing_research_policy(self):
        state = _base_state(research_policy="rigorous")
        result = step_02_quickstart(state)
        assert "research_policy" not in result

    def test_only_missing_fields_are_set(self):
        state = _base_state(artifact_types=["lesson"], theme="ocean", research_policy="")
        result = step_02_quickstart(state)
        assert "artifact_types" not in result
        assert "theme" not in result
        assert result["research_policy"] == "standard"


# ── Pack Scope ────────────────────────────────────────────────────────────────


class TestPackScopeKeepsExistingTypes:
    def test_keeps_existing_valid_types(self):
        state = _base_state(artifact_types=["lesson", "drill"])
        result = step_05_pack_scope(state)
        assert result["artifact_types"] == ["lesson", "drill"]
        assert result["current_step"] == 5

    def test_keeps_single_valid_type(self):
        state = _base_state(artifact_types=["quiz"])
        result = step_05_pack_scope(state)
        assert result["artifact_types"] == ["quiz"]


class TestPackScopeFiltersUnsupported:
    def test_filters_out_invalid_types(self):
        state = _base_state(artifact_types=["lesson", "INVALID", "quiz", "BOGUS"])
        result = step_05_pack_scope(state)
        assert result["artifact_types"] == ["lesson", "quiz"]

    def test_filters_all_invalid_to_defaults(self):
        state = _base_state(artifact_types=["fake", "also_fake"])
        result = step_05_pack_scope(state)
        assert result["artifact_types"] == ["lesson", "worksheet", "quiz"]

    def test_all_supported_types_accepted(self):
        all_types = ["lesson", "worksheet", "quiz", "drill", "recap", "infographic"]
        state = _base_state(artifact_types=all_types)
        result = step_05_pack_scope(state)
        assert result["artifact_types"] == all_types


class TestPackScopeDefaultsWhenEmpty:
    def test_empty_list_uses_defaults(self):
        state = _base_state(artifact_types=[])
        result = step_05_pack_scope(state)
        assert result["artifact_types"] == ["lesson", "worksheet", "quiz"]

    def test_none_uses_defaults(self):
        state = _base_state()
        state.pop("artifact_types", None)
        result = step_05_pack_scope(state)
        assert result["artifact_types"] == ["lesson", "worksheet", "quiz"]


# ── Visual Engine ──────────────────────────────────────────────────────────────


class TestVisualEngineValidatesTheme:
    def test_valid_theme_kept(self):
        state = _base_state(theme="ocean")
        result = step_06_visual_engine(state)
        assert result["theme"] == "ocean"
        assert result["current_step"] == 6

    def test_forest_theme_kept(self):
        state = _base_state(theme="forest")
        result = step_06_visual_engine(state)
        assert result["theme"] == "forest"

    def test_default_theme_kept(self):
        state = _base_state(theme="default")
        result = step_06_visual_engine(state)
        assert result["theme"] == "default"


class TestVisualEngineFallsBack:
    def test_invalid_theme_falls_back_to_default(self):
        state = _base_state(theme="neon_retro")
        result = step_06_visual_engine(state)
        assert result["theme"] == "default"

    def test_empty_string_theme_falls_back_to_default(self):
        state = _base_state(theme="")
        result = step_06_visual_engine(state)
        assert result["theme"] == "default"

    def test_missing_theme_defaults_to_default(self):
        state = _base_state()
        state.pop("theme", None)
        result = step_06_visual_engine(state)
        assert result["theme"] == "default"


# ── Finalize ────────────────────────────────────────────────────────────────


class TestFinalizeRendersHtml:
    def test_renders_html_from_artifact(self):
        artifact = {
            "artifact_id": "a-1",
            "title": "Photosynthesis Lesson",
            "artifact_type": "lesson",
            "theme": "default",
            "sections": [
                {"title": "Introduction", "content": "Plants use sunlight."},
            ],
        }
        state = _base_state(artifacts=[artifact])
        result = step_12_finalize(state)

        assert len(result["exported_files"]) == 1
        exported = result["exported_files"][0]
        assert exported["artifact_id"] == "a-1"
        assert exported["format"] == "html"
        assert exported["title"] == "Photosynthesis Lesson"
        assert exported["artifact_type"] == "lesson"

    def test_sets_current_step(self):
        artifact = {
            "artifact_id": "a-1",
            "title": "Test",
            "artifact_type": "lesson",
            "sections": [],
        }
        state = _base_state(artifacts=[artifact])
        result = step_12_finalize(state)
        assert result["current_step"] == 12

    def test_empty_artifacts_produces_no_exports(self):
        state = _base_state(artifacts=[])
        result = step_12_finalize(state)
        assert result["exported_files"] == []


class TestFinalizeSkipsTeacherOnly:
    def test_skips_teacher_only_artifact(self):
        artifacts = [
            {
                "artifact_id": "a-1",
                "title": "Student Lesson",
                "artifact_type": "lesson",
                "sections": [],
            },
            {
                "artifact_id": "a-2",
                "title": "Answer Key",
                "artifact_type": "lesson",
                "teacher_only": True,
                "sections": [],
            },
        ]
        state = _base_state(artifacts=artifacts)
        result = step_12_finalize(state)

        assert len(result["exported_files"]) == 1
        assert result["exported_files"][0]["artifact_id"] == "a-1"

    def test_skips_teacher_only_sections_in_html(self):
        artifact = {
            "artifact_id": "a-1",
            "title": "Quiz",
            "artifact_type": "quiz",
            "sections": [
                {"title": "Q1", "content": "What is photosynthesis?"},
                {"title": "Answers", "content": "A1: Green plants.", "teacher_only": True},
            ],
        }
        state = _base_state(artifacts=[artifact])
        result = step_12_finalize(state)

        html_content = result["exported_files"][0]["content"]
        assert "What is photosynthesis?" in html_content
        assert "A1: Green plants." not in html_content


class TestFinalizeHtmlInvariants:
    def _get_html(self, **artifact_overrides: Any) -> str:
        artifact = {
            "artifact_id": "a-1",
            "title": "Test Lesson",
            "artifact_type": "lesson",
            "theme": "default",
            "sections": [{"title": "Intro", "content": "Hello world."}],
        }
        artifact.update(artifact_overrides)
        state = _base_state(artifacts=[artifact])
        result = step_12_finalize(state)
        return result["exported_files"][0]["content"]

    def test_html_starts_with_doctype(self):
        html_content = self._get_html()
        assert html_content.startswith("<!DOCTYPE html>")

    def test_html_contains_brand_string(self):
        html_content = self._get_html()
        assert "oh-my-class" in html_content

    def test_html_has_viewport_meta(self):
        html_content = self._get_html()
        assert 'name="viewport"' in html_content
        assert "width=device-width" in html_content

    def test_html_no_external_http_links(self):
        html_content = self._get_html()
        assert "http://" not in html_content
        assert "https://" not in html_content

    def test_html_has_lang_attribute(self):
        html_content = self._get_html()
        assert 'lang="vi"' in html_content

    def test_html_respects_custom_language(self):
        artifact = {
            "artifact_id": "a-1",
            "title": "Test",
            "artifact_type": "lesson",
            "sections": [],
            "accessibility": {"language": "en"},
        }
        state = _base_state(artifacts=[artifact])
        result = step_12_finalize(state)
        html_content = result["exported_files"][0]["content"]
        assert 'lang="en"' in html_content

    def test_html_escapes_title_xss(self):
        artifact = {
            "artifact_id": "a-1",
            "title": '<script>alert("xss")</script>',
            "artifact_type": "lesson",
            "sections": [],
        }
        state = _base_state(artifacts=[artifact])
        result = step_12_finalize(state)
        html_content = result["exported_files"][0]["content"]
        assert "<script>" not in html_content
        assert "&lt;script&gt;" in html_content

    def test_html_escapes_content_xss(self):
        artifact = {
            "artifact_id": "a-1",
            "title": "Safe",
            "artifact_type": "lesson",
            "sections": [{"title": "X", "content": '<img onerror="alert(1)"}>'}],
        }
        state = _base_state(artifacts=[artifact])
        result = step_12_finalize(state)
        html_content = result["exported_files"][0]["content"]
        assert "onerror" not in html_content or "&lt;" in html_content

    def test_html_contains_system_font_stack(self):
        html_content = self._get_html()
        assert "system-ui" in html_content

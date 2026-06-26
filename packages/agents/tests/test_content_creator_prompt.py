"""Tests for Content Creator system prompt — RCM component catalog requirements."""

from __future__ import annotations

import pytest

from packages.agents.sub_agents.content_creator.prompts import load_system_prompt


@pytest.fixture(scope="module")
def prompt() -> str:
    return load_system_prompt()


# ── RCM header ───────────────────────────────────────────────────────────────


class TestRCMHeader:
    def test_rcm_section_exists(self, prompt: str) -> None:
        assert "## RCM" in prompt

    def test_rcm_explains_component_array(self, prompt: str) -> None:
        assert "components" in prompt

    def test_rcm_prose_fallback_clause(self, prompt: str) -> None:
        """Prose-only sections must be explicitly framed as fallback."""
        assert "fallback" in prompt.lower()


# ── Hard minimums ────────────────────────────────────────────────────────────


class TestHardMinimums:
    @pytest.mark.parametrize(
        ("artifact", "minimum"),
        [
            ("lesson", "\u2265 2"),
            ("quiz", "\u2265 8"),
            ("worksheet", "\u2265 3"),
            ("drill", "\u2265 5"),
            ("recap", "\u2265 3"),
            ("infographic", "\u2265 1"),
        ],
    )
    def test_minimum_line_present(self, prompt: str, artifact: str, minimum: str) -> None:
        """Each artifact type must have its hard minimum documented."""
        assert minimum in prompt, f"Missing minimum {minimum} for {artifact}"
        assert artifact in prompt


# ── Component catalog ────────────────────────────────────────────────────────

EXPECTED_COMPONENTS = [
    "heading",
    "paragraph",
    "callout",
    "table",
    "stat_grid",
    "pattern_grid",
    "trait_grid",
    "taxonomy_grid",
    "phase_timeline",
    "flow_step",
    "question_card",
    "question_list",
    "concept_map",
    "timeline",
    "vocab_cluster",
    "contrastive_pairs",
    "phrasal_verb_cluster",
    "film_clip_activity",
    "roleplay_script",
    "active_recall_prompt",
    "hw_list",
    "alert",
]


class TestComponentCatalog:
    def test_all_component_names_present(self, prompt: str) -> None:
        for comp in EXPECTED_COMPONENTS:
            assert comp in prompt, f"Component catalog missing: {comp}"

    def test_catalog_table_header(self, prompt: str) -> None:
        assert "Component Catalog" in prompt


class TestComponentSelectionRules:
    def test_selection_rules_section_exists(self, prompt: str) -> None:
        assert "Component Selection Rules" in prompt

    @pytest.mark.parametrize(
        ("teaching_job", "components"),
        [
            ("Introduce a concept", ["concept_map", "taxonomy_grid", "trait_grid"]),
            ("Explain a process", ["phase_timeline", "flow_step", "timeline"]),
            ("Compare ideas", ["contrastive_pairs", "table", "pattern_grid"]),
            ("Build vocabulary", ["vocab_cluster", "phrasal_verb_cluster"]),
            ("Check understanding", ["question_card", "question_list", "active_recall_prompt"]),
        ],
    )
    def test_selection_rules_map_pedagogical_jobs(
        self,
        prompt: str,
        teaching_job: str,
        components: list[str],
    ) -> None:
        assert teaching_job in prompt
        for component in components:
            assert component in prompt

    def test_rules_reject_decorative_components(self, prompt: str) -> None:
        assert "decorative components" in prompt
        assert "does not change how the student learns" in prompt

    def test_rules_require_lesson_teaching_and_assessment_mix(self, prompt: str) -> None:
        assert "teaching/organization component" in prompt
        assert "assessment/retrieval component" in prompt

    def test_rules_warn_against_count_stuffing(self, prompt: str) -> None:
        assert "Do not repeat the same component type" in prompt
        assert "diversify by intent" in prompt


# ── JSON section shape ───────────────────────────────────────────────────────


class TestJSONSectionShape:
    def test_section_shape_has_components_key(self, prompt: str) -> None:
        assert '"components"' in prompt

    def test_lesson_example_uses_components(self, prompt: str) -> None:
        """The lesson JSON example must show components array usage."""
        assert "Lesson Section Example" in prompt
        # The example must contain components array with a question_card
        assert "question_card" in prompt

    def test_quiz_example_uses_question_card(self, prompt: str) -> None:
        assert "Quiz Section Example" in prompt
        assert "question_card" in prompt


# ── Existing constraints preserved ───────────────────────────────────────────


class TestExistingConstraintsPreserved:
    def test_json_only_constraint(self, prompt: str) -> None:
        assert "JSON ONLY" in prompt or "JSON only" in prompt

    def test_no_cdn_constraint(self, prompt: str) -> None:
        assert "CDN" in prompt

    def test_no_pii_constraint(self, prompt: str) -> None:
        assert "PII" in prompt or "pii" in prompt.lower()

    def test_teacher_only_constraint(self, prompt: str) -> None:
        assert "teacher_only" in prompt

    def test_no_raw_html(self, prompt: str) -> None:
        assert "raw HTML" in prompt or "never produce raw HTML" in prompt

    def test_section_payload_allows_content_or_components(self, prompt: str) -> None:
        assert "either `components`, `content`, or both" in prompt
        assert "must have a `type` and `content` field" not in prompt

    def test_vocabulary_methodology_preserved(self, prompt: str) -> None:
        assert "Vocabulary Lesson Methodology" in prompt
        assert "vocab_cluster" in prompt
        assert "contrastive_pairs" in prompt
        assert "film_clip_activity" in prompt
        assert "roleplay_script" in prompt
        assert "active_recall_prompt" in prompt

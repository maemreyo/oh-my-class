"""Tests for Layer 1 component minimums hard gate."""

import pytest

from packages.quality.layer1_schema.component_gate import (
    ComponentGateError,
    assert_component_minimums,
    validate_component_minimums,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _section(component_type: str, **extra: object) -> dict[str, object]:
    """Build a minimal component dict."""
    d: dict[str, object] = {"type": component_type}
    d.update(extra)
    return d


def _question_list(questions: int) -> dict[str, object]:
    """Build a question_list component with *questions* nested items."""
    return {
        "type": "question_list",
        "questions": [{"type": "question_card", "id": f"q{i}"} for i in range(questions)],
    }


def _container(*components: dict[str, object]) -> dict[str, object]:
    return {"title": "Section", "components": list(components)}


# ---------------------------------------------------------------------------
# lesson — at least 2 non-structural components
# ---------------------------------------------------------------------------


class TestLessonMinimums:
    def test_passes_with_two_non_structural(self):
        artifact = {
            "artifact_type": "lesson",
            "sections": [
                _container(
                    _section("heading", text="Intro"),
                    _section("table", columns=["a"], rows=[["b"]]),
                    _section("stat_grid", stats=[{"label": "x", "value": "1"}]),
                ),
            ],
        }
        assert validate_component_minimums(artifact) == []

    def test_passes_with_direct_component_sections(self):
        artifact = {
            "artifact_type": "lesson",
            "sections": [
                _section("table", columns=["a"], rows=[["b"]]),
                _section("stat_grid", stats=[{"label": "x", "value": "1"}]),
            ],
        }
        assert validate_component_minimums(artifact) == []

    def test_fails_with_only_structural(self):
        artifact = {
            "artifact_type": "lesson",
            "sections": [
                _container(
                    _section("heading", text="Intro"),
                    _section("paragraph", text="Hello"),
                    _section("callout", variant="tip", body="Hi"),
                ),
            ],
        }
        issues = validate_component_minimums(artifact)
        assert len(issues) == 1
        assert "lesson" in issues[0]
        assert "≥2" in issues[0]

    def test_fails_with_one_non_structural(self):
        artifact = {
            "artifact_type": "lesson",
            "sections": [
                _container(
                    _section("heading", text="Intro"),
                    _section("table", columns=["a"], rows=[[]]),
                ),
            ],
        }
        issues = validate_component_minimums(artifact)
        assert len(issues) == 1
        assert "found 1" in issues[0]

    def test_question_list_counts_individual_questions(self):
        """A question_list with 2 questions counts as 2 non-structural."""
        artifact = {
            "artifact_type": "lesson",
            "sections": [
                _container(_section("heading", text="Intro"), _question_list(2)),
            ],
        }
        # question_list is non-structural but we count at section level, not nested
        issues = validate_component_minimums(artifact)
        # question_list itself is 1 non-structural component
        assert len(issues) == 1
        assert "found 1" in issues[0]

    def test_mixed_structural_and_non_structural(self):
        artifact = {
            "artifact_type": "lesson",
            "sections": [
                _container(
                    _section("heading", text="H"),
                    _section("paragraph", text="P"),
                    _section("concept_map", nodes=[{"id": "a"}]),
                    _section("timeline", events=[{"date": "2020"}]),
                ),
            ],
        }
        assert validate_component_minimums(artifact) == []


# ---------------------------------------------------------------------------
# quiz — at least 8 question components
# ---------------------------------------------------------------------------


class TestQuizMinimums:
    def test_passes_with_eight_question_cards(self):
        sections = [_section("heading", text="Q")] + [
            _section("question_card", id=f"q{i}", text="?", options=[], answer="a", explain="")
            for i in range(8)
        ]
        artifact = {"artifact_type": "quiz", "sections": sections}
        assert validate_component_minimums(artifact) == []

    def test_passes_with_question_list_containing_questions(self):
        sections = [
            _section("heading", text="Q"),
            _question_list(6),
            _section("question_card", id="q1", text="?", options=[], answer="a", explain=""),
            _section("question_card", id="q2", text="?", options=[], answer="a", explain=""),
        ]
        artifact = {"artifact_type": "quiz", "sections": sections}
        assert validate_component_minimums(artifact) == []

    def test_fails_with_seven(self):
        sections = [
            _section("question_card", id=f"q{i}", text="?", options=[], answer="a", explain="")
            for i in range(7)
        ]
        artifact = {"artifact_type": "quiz", "sections": sections}
        issues = validate_component_minimums(artifact)
        assert len(issues) == 1
        assert "found 7" in issues[0]
        assert "≥8" in issues[0]

    def test_fails_with_zero_questions(self):
        artifact = {
            "artifact_type": "quiz",
            "sections": [_section("heading", text="Q")],
        }
        issues = validate_component_minimums(artifact)
        assert len(issues) == 1
        assert "found 0" in issues[0]

    def test_question_list_with_empty_questions_list(self):
        sections = [_question_list(0)]
        artifact = {"artifact_type": "quiz", "sections": sections}
        issues = validate_component_minimums(artifact)
        assert len(issues) == 1
        assert "found 0" in issues[0]

    def test_question_list_with_non_list_questions_field(self):
        """question_list with malformed questions field (not a list) → counts 0 from that list."""
        sections = [
            {
                "type": "question_list",
                "questions": "not a list",  # malformed
            },
            _section("question_card", id="q1", text="?", options=[], answer="a", explain=""),
        ]
        artifact = {"artifact_type": "quiz", "sections": sections}
        issues = validate_component_minimums(artifact)
        assert len(issues) == 1
        assert "found 1" in issues[0]

    def test_passes_exactly_eight(self):
        sections = [
            _section("question_card", id=f"q{i}", text="?", options=[], answer="a", explain="")
            for i in range(8)
        ]
        artifact = {"artifact_type": "quiz", "sections": sections}
        assert validate_component_minimums(artifact) == []


# ---------------------------------------------------------------------------
# worksheet — at least 3 question components
# ---------------------------------------------------------------------------


class TestWorksheetMinimums:
    def test_passes_with_three_questions(self):
        artifact = {
            "artifact_type": "worksheet",
            "sections": [
                _question_list(3),
            ],
        }
        assert validate_component_minimums(artifact) == []

    def test_fails_with_two_questions(self):
        artifact = {
            "artifact_type": "worksheet",
            "sections": [
                _section("question_card", id="q1", text="?", options=[], answer="a", explain=""),
                _section("question_card", id="q2", text="?", options=[], answer="b", explain=""),
            ],
        }
        issues = validate_component_minimums(artifact)
        assert len(issues) == 1
        assert "found 2" in issues[0]
        assert "≥3" in issues[0]


# ---------------------------------------------------------------------------
# drill — at least 5 question components
# ---------------------------------------------------------------------------


class TestDrillMinimums:
    def test_passes_with_five(self):
        sections = [
            _section("question_card", id=f"q{i}", text="?", options=[], answer="a", explain="")
            for i in range(5)
        ]
        artifact = {"artifact_type": "drill", "sections": sections}
        assert validate_component_minimums(artifact) == []

    def test_fails_with_four(self):
        sections = [_question_list(4)]
        artifact = {"artifact_type": "drill", "sections": sections}
        issues = validate_component_minimums(artifact)
        assert len(issues) == 1
        assert "found 4" in issues[0]
        assert "≥5" in issues[0]


# ---------------------------------------------------------------------------
# recap — at least 3 question components
# ---------------------------------------------------------------------------


class TestRecapMinimums:
    def test_passes_with_three(self):
        artifact = {
            "artifact_type": "recap",
            "sections": [
                _question_list(2),
                _section("question_card", id="q1", text="?", options=[], answer="a", explain=""),
            ],
        }
        assert validate_component_minimums(artifact) == []

    def test_fails_with_two(self):
        artifact = {
            "artifact_type": "recap",
            "sections": [_question_list(2)],
        }
        issues = validate_component_minimums(artifact)
        assert len(issues) == 1
        assert "found 2" in issues[0]
        assert "≥3" in issues[0]


# ---------------------------------------------------------------------------
# infographic — at least 1 visual/data-display component
# ---------------------------------------------------------------------------


class TestInfographicMinimums:
    @pytest.mark.parametrize(
        "visual_type",
        ["stat_grid", "pattern_grid", "trait_grid", "taxonomy_grid", "concept_map", "timeline"],
    )
    def test_passes_with_each_visual_type(self, visual_type: str):
        artifact = {
            "artifact_type": "infographic",
            "sections": [_section(visual_type)],
        }
        assert validate_component_minimums(artifact) == []

    def test_fails_with_only_structural(self):
        artifact = {
            "artifact_type": "infographic",
            "sections": [
                _section("heading", text="Title"),
                _section("paragraph", text="Body"),
            ],
        }
        issues = validate_component_minimums(artifact)
        assert len(issues) == 1
        assert "found 0" in issues[0]
        assert "≥1" in issues[0]


# ---------------------------------------------------------------------------
# Skip types — answer_key and roadmap always pass
# ---------------------------------------------------------------------------


class TestSkipTypes:
    def test_answer_key_always_passes(self):
        artifact = {"artifact_type": "answer_key", "sections": []}
        assert validate_component_minimums(artifact) == []

    def test_roadmap_always_passes(self):
        artifact = {"artifact_type": "roadmap", "sections": []}
        assert validate_component_minimums(artifact) == []


# ---------------------------------------------------------------------------
# Unknown artifact type — no minimum → pass
# ---------------------------------------------------------------------------


class TestUnknownType:
    def test_unknown_type_passes(self):
        artifact = {"artifact_type": "flashcard_deck", "sections": []}
        assert validate_component_minimums(artifact) == []


# ---------------------------------------------------------------------------
# Malformed / edge cases — must not crash
# ---------------------------------------------------------------------------


class TestMalformedArtifacts:
    def test_no_sections_key(self):
        artifact = {"artifact_type": "quiz"}
        issues = validate_component_minimums(artifact)
        assert len(issues) == 1
        assert "no typed components" in issues[0]

    def test_sections_not_a_list(self):
        artifact = {"artifact_type": "quiz", "sections": "bad"}
        issues = validate_component_minimums(artifact)
        assert len(issues) == 1
        assert "not a list" in issues[0]

    def test_empty_sections(self):
        artifact = {"artifact_type": "quiz", "sections": []}
        issues = validate_component_minimums(artifact)
        assert len(issues) == 1
        assert "no typed components" in issues[0]

    def test_sections_with_non_dicts(self):
        artifact = {"artifact_type": "quiz", "sections": ["plain text", 42, None]}
        issues = validate_component_minimums(artifact)
        assert len(issues) == 1
        assert "no typed components" in issues[0]

    def test_sections_with_dicts_missing_type(self):
        artifact = {
            "artifact_type": "quiz",
            "sections": [{"text": "hello"}, {"content": "world"}],
        }
        issues = validate_component_minimums(artifact)
        assert len(issues) == 1
        assert "no typed components" in issues[0]

    def test_nested_components_are_counted(self):
        artifact = {
            "artifact_type": "quiz",
            "sections": [
                _container(*[
                    _section(
                        "question_card",
                        id=f"q{i}",
                        text="?",
                        options=[],
                        answer="a",
                        explain="",
                    )
                    for i in range(8)
                ]),
            ],
        }
        assert validate_component_minimums(artifact) == []

    def test_non_list_nested_components_are_skipped(self):
        artifact = {
            "artifact_type": "quiz",
            "sections": [{"title": "Bad", "components": "not a list"}],
        }
        issues = validate_component_minimums(artifact)
        assert len(issues) == 1
        assert "no typed components" in issues[0]

    def test_sections_with_non_string_type(self):
        artifact = {
            "artifact_type": "quiz",
            "sections": [{"type": 123}, {"type": None}],
        }
        issues = validate_component_minimums(artifact)
        assert len(issues) == 1
        assert "no typed components" in issues[0]

    def test_no_artifact_type_key(self):
        artifact = {"sections": [_section("heading", text="Hi")]}
        # artifact_type defaults to "" → not in _MINIMUMS → pass
        assert validate_component_minimums(artifact) == []

    def test_none_sections(self):
        artifact = {"artifact_type": "quiz", "sections": None}
        issues = validate_component_minimums(artifact)
        assert len(issues) == 1
        assert "not a list" in issues[0]


# ---------------------------------------------------------------------------
# assert_component_minimums — raises ComponentGateError
# ---------------------------------------------------------------------------


class TestAssertComponentMinimums:
    def test_passes_when_minimum_met(self):
        artifact = {
            "artifact_type": "quiz",
            "sections": [
                _section("question_card", id=f"q{i}", text="?", options=[], answer="a", explain="")
                for i in range(8)
            ],
        }
        # Should not raise
        assert_component_minimums(artifact)

    def test_raises_when_minimum_not_met(self):
        artifact = {
            "artifact_type": "quiz",
            "sections": [
                _section("question_card", id="q1", text="?", options=[], answer="a", explain="")
            ],
        }
        with pytest.raises(ComponentGateError) as exc_info:
            assert_component_minimums(artifact)
        assert exc_info.value.artifact_type == "quiz"
        assert len(exc_info.value.issues) == 1
        assert "found 1" in exc_info.value.issues[0]

    def test_error_message_contains_type_and_issues(self):
        artifact = {"artifact_type": "drill", "sections": []}
        with pytest.raises(ComponentGateError) as exc_info:
            assert_component_minimums(artifact)
        assert "drill" in str(exc_info.value)
        assert len(exc_info.value.issues) >= 1

    def test_skip_type_does_not_raise(self):
        assert_component_minimums({"artifact_type": "answer_key", "sections": []})
        assert_component_minimums({"artifact_type": "roadmap", "sections": []})

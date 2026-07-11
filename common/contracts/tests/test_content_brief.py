from __future__ import annotations

from common.contracts.content_brief import (
    ContentBrief,
    is_choice_within_bounds,
    resolve_methodology,
)


def test_teacher_pin_always_wins_methodology_precedence() -> None:
    methodology, source = resolve_methodology(
        teacher_pin="inquiry_based", strategy_recommendation="direct_instruction",
    )

    assert methodology == "inquiry_based"
    assert source == "teacher_pin"


def test_strategy_recommendation_wins_without_a_teacher_pin() -> None:
    methodology, source = resolve_methodology(
        teacher_pin=None, strategy_recommendation="direct_instruction",
    )

    assert methodology == "direct_instruction"
    assert source == "strategy_recommendation"


def test_default_methodology_when_nothing_else_is_set() -> None:
    methodology, source = resolve_methodology(teacher_pin=None, strategy_recommendation=None)

    assert methodology == "direct_instruction"
    assert source == "default"


def test_blank_strings_are_treated_as_unset() -> None:
    methodology, source = resolve_methodology(teacher_pin="  ", strategy_recommendation="  ")

    assert methodology == "direct_instruction"
    assert source == "default"


def _brief(**overrides: object) -> ContentBrief:
    defaults: dict[str, object] = {
        "content_brief_id": "brief-1",
        "run_id": "run-1",
        "artifact_type": "recap",
        "objectives": ["explain photosynthesis"],
        "methodology": "direct_instruction",
        "methodology_source": "teacher_pin",
    }
    defaults.update(overrides)
    return ContentBrief(**defaults)


def test_any_choice_is_within_bounds_when_no_variant_menu_is_declared() -> None:
    brief = _brief()

    assert is_choice_within_bounds(brief, "anything") is True
    assert brief.education_policy_version == "education_policy.v1"


def test_choice_must_be_listed_when_a_variant_menu_is_declared() -> None:
    brief = _brief(eligible_component_variants=["multiple_choice", "short_answer"])

    assert is_choice_within_bounds(brief, "multiple_choice") is True
    assert is_choice_within_bounds(brief, "essay") is False


def test_knowledge_db_version_defaults_to_none_for_a_teacher_authored_brief() -> None:
    brief = _brief()

    assert brief.knowledge_db_version is None


def test_knowledge_db_version_is_pinned_when_a_graph_snapshot_backs_the_brief() -> None:
    brief = _brief(knowledge_db_version="knowledge-db-2026.07.1")

    assert brief.knowledge_db_version == "knowledge-db-2026.07.1"

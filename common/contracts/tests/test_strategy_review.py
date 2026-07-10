from __future__ import annotations

import pytest

from common.contracts.content_brief import ContentBrief
from common.contracts.strategy_review import (
    SpecialistComplianceError,
    SpecialistOutputDeclaration,
    enforce_content_brief_compliance,
)


def _brief(**overrides: object) -> ContentBrief:
    defaults: dict[str, object] = {
        "content_brief_id": "brief-1",
        "run_id": "run-1",
        "artifact_type": "recap",
        "objectives": ["explain photosynthesis", "explain respiration"],
        "methodology": "direct_instruction",
        "methodology_source": "teacher_pin",
        "learning_moves": ["explain", "model", "check_understanding"],
    }
    defaults.update(overrides)
    return ContentBrief(**defaults)


def test_compliant_output_raises_nothing() -> None:
    brief = _brief()
    produced = SpecialistOutputDeclaration(
        methodology="direct_instruction",
        objectives_covered=["explain photosynthesis"],
        learning_moves_used=["explain", "model"],
    )

    enforce_content_brief_compliance(brief, produced)  # must not raise


def test_methodology_substitution_is_a_violation() -> None:
    brief = _brief()
    produced = SpecialistOutputDeclaration(
        methodology="inquiry_based",
        objectives_covered=["explain photosynthesis"],
    )

    with pytest.raises(SpecialistComplianceError) as excinfo:
        enforce_content_brief_compliance(brief, produced)
    assert any("methodology" in v for v in excinfo.value.violations)


def test_objective_outside_the_brief_is_a_violation() -> None:
    brief = _brief()
    produced = SpecialistOutputDeclaration(
        methodology="direct_instruction",
        objectives_covered=["explain photosynthesis", "explain the water cycle"],
    )

    with pytest.raises(SpecialistComplianceError) as excinfo:
        enforce_content_brief_compliance(brief, produced)
    assert any("objectives" in v for v in excinfo.value.violations)


def test_learning_move_outside_the_brief_is_a_violation() -> None:
    brief = _brief()
    produced = SpecialistOutputDeclaration(
        methodology="direct_instruction",
        objectives_covered=["explain photosynthesis"],
        learning_moves_used=["explain", "debate"],
    )

    with pytest.raises(SpecialistComplianceError) as excinfo:
        enforce_content_brief_compliance(brief, produced)
    assert any("learning moves" in v for v in excinfo.value.violations)


def test_covering_fewer_objectives_than_approved_is_not_a_violation() -> None:
    brief = _brief()
    produced = SpecialistOutputDeclaration(
        methodology="direct_instruction",
        objectives_covered=["explain photosynthesis"],
    )

    enforce_content_brief_compliance(brief, produced)  # a fill-failure concern, not this check

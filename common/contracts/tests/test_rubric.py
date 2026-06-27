"""Tests for canonical rubric registry contracts.

Covers: weight validation (non-negative, sum=1.0±0.001), version immutability,
hashability, RubricRegistry dedup, and roundtrip serialization.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.rubric import (
    Rubric,
    RubricCriterion,
    RubricLevel,
    RubricRegistry,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_valid_rubric(**overrides: object) -> Rubric:
    """Build a G-Eval standard rubric with 3 layers summing to 1.0."""
    criteria = overrides.pop("criteria", [
        RubricCriterion(
            name="format_compliance",
            weight=0.15,
            levels=[RubricLevel(score=10, description="Perfect")],
        ),
        RubricCriterion(
            name="content_quality",
            weight=0.55,
            levels=[RubricLevel(score=10, description="Perfect")],
        ),
        RubricCriterion(
            name="presentation",
            weight=0.30,
            levels=[RubricLevel(score=10, description="Perfect")],
        ),
    ])
    version_id = overrides.pop("version_id", "v1")
    return Rubric(
        criteria=criteria, version_id=version_id, **overrides  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# RubricLevel
# ---------------------------------------------------------------------------

class TestRubricLevel:
    def test_creates_with_score_and_description(self) -> None:
        level = RubricLevel(score=8.5, description="Good")
        assert level.score == 8.5
        assert level.description == "Good"

    def test_is_frozen(self) -> None:
        level = RubricLevel(score=5, description="Fair")
        with pytest.raises(ValidationError):
            level.score = 6  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RubricCriterion
# ---------------------------------------------------------------------------

class TestRubricCriterion:
    def test_accepts_non_negative_weight(self) -> None:
        c = RubricCriterion(name="accuracy", weight=0.0)
        assert c.weight == 0.0

    def test_rejects_negative_weight(self) -> None:
        with pytest.raises(ValidationError):
            RubricCriterion(name="accuracy", weight=-0.1)

    def test_accepts_weight_up_to_one(self) -> None:
        c = RubricCriterion(name="accuracy", weight=1.0)
        assert c.weight == 1.0

    def test_rejects_weight_above_one(self) -> None:
        with pytest.raises(ValidationError):
            RubricCriterion(name="accuracy", weight=1.5)

    def test_optional_levels_and_descriptors(self) -> None:
        c = RubricCriterion(name="clarity", weight=0.5)
        assert c.levels == []
        assert c.descriptors is None


# ---------------------------------------------------------------------------
# Rubric — weight-sum invariant
# ---------------------------------------------------------------------------

class TestRubricWeightSum:
    def test_valid_when_weights_sum_to_one(self) -> None:
        rubric = _make_valid_rubric()
        assert rubric.version_id == "v1"
        assert len(rubric.criteria) == 3

    def test_valid_at_lower_bound(self) -> None:
        """0.9995 rounds within tolerance."""
        rubric = _make_valid_rubric(criteria=[
            RubricCriterion(name="a", weight=0.9995),
            RubricCriterion(name="b", weight=0.0005),
        ])
        assert len(rubric.criteria) == 2

    def test_valid_at_upper_bound(self) -> None:
        """1.0005 is within ±0.001 tolerance."""
        rubric = _make_valid_rubric(criteria=[
            RubricCriterion(name="a", weight=1.000),
            RubricCriterion(name="b", weight=0.001),
        ])
        assert len(rubric.criteria) == 2

    def test_rejects_weights_summing_too_low(self) -> None:
        with pytest.raises(ValidationError, match="1.0"):
            _make_valid_rubric(criteria=[
                RubricCriterion(name="a", weight=0.50),
                RubricCriterion(name="b", weight=0.40),
            ])

    def test_rejects_weights_summing_too_high(self) -> None:
        with pytest.raises(ValidationError, match="1.0"):
            _make_valid_rubric(criteria=[
                RubricCriterion(name="a", weight=0.60),
                RubricCriterion(name="b", weight=0.50),
            ])

    def test_rejects_empty_criteria(self) -> None:
        with pytest.raises(ValidationError):
            Rubric(criteria=[], version_id="v1")


# ---------------------------------------------------------------------------
# Rubric — criterion name uniqueness
# ---------------------------------------------------------------------------

class TestRubricCriterionUniqueness:
    def test_rejects_duplicate_criterion_names(self) -> None:
        with pytest.raises(ValidationError, match="unique"):
            _make_valid_rubric(criteria=[
                RubricCriterion(name="format", weight=0.50),
                RubricCriterion(name="format", weight=0.50),
            ])


# ---------------------------------------------------------------------------
# Rubric — immutability and hashability
# ---------------------------------------------------------------------------

class TestRubricImmutability:
    def test_rubric_is_frozen(self) -> None:
        rubric = _make_valid_rubric()
        with pytest.raises(ValidationError):
            rubric.version_id = "v2"  # type: ignore[misc]

    def test_rubric_is_hashable(self) -> None:
        rubric = _make_valid_rubric()
        # Must not raise TypeError
        hash(rubric)

    def test_two_identical_rubrics_have_same_hash(self) -> None:
        r1 = _make_valid_rubric(version_id="same")
        r2 = _make_valid_rubric(version_id="same")
        assert hash(r1) == hash(r2)


# ---------------------------------------------------------------------------
# Rubric — model_dump roundtrip
# ---------------------------------------------------------------------------

class TestRubricRoundtrip:
    def test_dump_and_validate(self) -> None:
        rubric = _make_valid_rubric()
        data = rubric.model_dump(mode="python")
        restored = Rubric.model_validate(data)
        assert restored == rubric

    def test_json_roundtrip(self) -> None:
        rubric = _make_valid_rubric()
        json_str = rubric.model_dump_json()
        restored = Rubric.model_validate_json(json_str)
        assert restored == rubric


# ---------------------------------------------------------------------------
# RubricRegistry
# ---------------------------------------------------------------------------

class TestRubricRegistry:
    def test_register_and_lookup(self) -> None:
        reg = RubricRegistry()
        rubric = _make_valid_rubric(version_id="geval-v1")
        reg.register(rubric)
        assert reg.get("geval-v1") == rubric

    def test_rejects_duplicate_version_id(self) -> None:
        reg = RubricRegistry()
        rubric = _make_valid_rubric(version_id="geval-v1")
        reg.register(rubric)
        with pytest.raises(ValueError, match="Duplicate"):
            reg.register(rubric)

    def test_lookup_returns_none_for_missing(self) -> None:
        reg = RubricRegistry()
        assert reg.get("nonexistent") is None

    def test_list_versions(self) -> None:
        reg = RubricRegistry()
        r1 = _make_valid_rubric(version_id="v1")
        r2 = _make_valid_rubric(version_id="v2", criteria=[
            RubricCriterion(name="x", weight=1.0),
        ])
        reg.register(r1)
        reg.register(r2)
        assert sorted(reg.list_versions()) == ["v1", "v2"]

    def test_register_rejects_non_rubric(self) -> None:
        reg = RubricRegistry()
        with pytest.raises(TypeError):
            reg.register("not a rubric")  # type: ignore[arg-type]

    def test_remove(self) -> None:
        reg = RubricRegistry()
        rubric = _make_valid_rubric(version_id="temp")
        reg.register(rubric)
        reg.remove("temp")
        assert reg.get("temp") is None

    def test_remove_nonexistent_raises(self) -> None:
        reg = RubricRegistry()
        with pytest.raises(KeyError):
            reg.remove("nonexistent")


# ---------------------------------------------------------------------------
# Adaptivity helpers
# ---------------------------------------------------------------------------

class TestRubricAdaptivity:
    def test_registry_can_iterate_all_rubrics(self) -> None:
        reg = RubricRegistry()
        for vid in ("r1", "r2", "r3"):
            reg.register(_make_valid_rubric(version_id=vid))
        all_rubrics = list(reg)
        assert len(all_rubrics) == 3

    def test_registry_len(self) -> None:
        reg = RubricRegistry()
        assert len(reg) == 0
        reg.register(_make_valid_rubric(version_id="a"))
        assert len(reg) == 1

    def test_registry_contains(self) -> None:
        reg = RubricRegistry()
        rubric = _make_valid_rubric(version_id="check")
        assert "check" not in reg
        reg.register(rubric)
        assert "check" in reg

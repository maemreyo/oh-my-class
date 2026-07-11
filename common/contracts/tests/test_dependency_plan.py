from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.dependency_plan import DEFAULT_DEPENDENCY_PLAN, DependencyPlan


def test_default_plan_matches_adr_053_wave_structure() -> None:
    assert DEFAULT_DEPENDENCY_PLAN.wave_index_of("lesson") == 0
    assert DEFAULT_DEPENDENCY_PLAN.wave_index_of("quiz") == 1
    assert DEFAULT_DEPENDENCY_PLAN.wave_index_of("slide_deck") == 1
    assert DEFAULT_DEPENDENCY_PLAN.wave_index_of("recap") == 2
    assert DEFAULT_DEPENDENCY_PLAN.wave_index_of("answer_key") == 2
    assert DEFAULT_DEPENDENCY_PLAN.wave_index_of("unknown_type") is None


def test_default_plan_dependencies_are_exposed() -> None:
    assert DEFAULT_DEPENDENCY_PLAN.dependencies_of("recap") == ("lesson", "quiz")
    assert DEFAULT_DEPENDENCY_PLAN.dependencies_of("lesson") == ()


def test_plan_rejects_a_dependency_on_an_unknown_artifact_type() -> None:
    with pytest.raises(ValidationError, match="not in any wave"):
        DependencyPlan(
            plan_version="v-test",
            waves=(("lesson",), ("quiz",)),
            dependencies={"quiz": ("nonexistent_type",)},
        )


def test_plan_rejects_a_same_wave_dependency() -> None:
    with pytest.raises(ValidationError, match="not in a strictly earlier wave"):
        DependencyPlan(
            plan_version="v-test",
            waves=(("lesson",), ("quiz", "worksheet")),
            dependencies={"quiz": ("worksheet",)},
        )


def test_plan_rejects_a_forward_dependency() -> None:
    with pytest.raises(ValidationError, match="not in a strictly earlier wave"):
        DependencyPlan(
            plan_version="v-test",
            waves=(("lesson",), ("quiz",), ("recap",)),
            dependencies={"lesson": ("recap",)},
        )


def test_plan_is_immutable() -> None:
    with pytest.raises(Exception, match="frozen|immutable"):
        DEFAULT_DEPENDENCY_PLAN.plan_version = "v2"  # type: ignore[misc]


def test_plan_requires_at_least_one_wave() -> None:
    with pytest.raises(Exception, match="at least 1 item|too_short"):
        DependencyPlan(plan_version="v-test", waves=())

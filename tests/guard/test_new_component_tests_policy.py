from __future__ import annotations

from scripts.verify_new_component_tests import missing_component_tests


def test_added_component_with_matching_test_passes() -> None:
    missing = missing_component_tests(
        added_paths=["packages/agents/new_component.py"],
        all_paths=["packages/agents/tests/test_new_component.py"],
        changed_paths=[],
    )

    assert missing == []


def test_added_component_without_test_fails() -> None:
    missing = missing_component_tests(
        added_paths=["services/gateway/new_component.py"],
        all_paths=["services/gateway/main.py"],
        changed_paths=[],
    )

    assert missing == ["services/gateway/new_component.py"]


def test_added_generated_component_is_ignored() -> None:
    missing = missing_component_tests(
        added_paths=["common/schemas/src/generated/models.ts"],
        all_paths=[],
        changed_paths=[],
    )

    assert missing == []

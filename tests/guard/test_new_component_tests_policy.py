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


def test_partial_substring_test_name_does_not_satisfy_component() -> None:
    missing = missing_component_tests(
        added_paths=["packages/agents/new.py"],
        all_paths=["packages/agents/tests/test_new_component.py"],
        changed_paths=[],
    )

    assert missing == ["packages/agents/new.py"]


def test_colocated_typescript_component_test_passes() -> None:
    missing = missing_component_tests(
        added_paths=["apps/web/src/components/teacher-gate.tsx"],
        all_paths=["apps/web/src/components/__tests__/teacher-gate.test.tsx"],
        changed_paths=[],
    )

    assert missing == []


def test_changed_matching_test_satisfies_new_component() -> None:
    missing = missing_component_tests(
        added_paths=["packages/quality/component_gate.py"],
        all_paths=[],
        changed_paths=["packages/quality/tests/test_component_gate.py"],
    )

    assert missing == []

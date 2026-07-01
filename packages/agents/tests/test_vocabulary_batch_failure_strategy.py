from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    ("failure", "action"),
    [
        ("parse_ambiguity", "teacher_review"),
        ("source_insufficiency", "teacher_review"),
        ("schema_invalidity", "retry_then_fail"),
        ("leakage", "fail_cluster"),
        ("renderer_failure", "retry_then_fail"),
        ("unsupported_export", "skip_export"),
    ],
)
def test_typed_failure_strategy_maps_to_expected_action(failure: str, action: str) -> None:
    from packages.agents.teaching_pack.vocabulary_batch_orchestrator import vocabulary_failure_action

    assert vocabulary_failure_action(failure) == action

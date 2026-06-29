from __future__ import annotations

import pytest

from scripts.verify_registry_drift import (
    RegistryDriftError,
    assert_all_registry_hashes_clean,
    build_registry_drift_snapshot,
)


def test_all_seeded_registries_validate_hashes_when_clean() -> None:
    snapshot = build_registry_drift_snapshot()

    assert_all_registry_hashes_clean(snapshot)


def test_repair_prompt_registry_hashes_are_part_of_aggregate_guard() -> None:
    snapshot = build_registry_drift_snapshot()
    module_ids = {module.id for module in snapshot.prompts.list_all()}

    assert "repair_answer_key_v1" in module_ids
    assert "repair_schema_v1" in module_ids


def test_guard_fails_when_registered_prompt_body_drifts() -> None:
    snapshot = build_registry_drift_snapshot()
    prompt = snapshot.prompts.get("planner_v1", "1.0.0")
    object.__setattr__(prompt, "body", f"{prompt.body}\nDrift")

    with pytest.raises(RegistryDriftError, match="prompt:planner_v1@1.0.0"):
        assert_all_registry_hashes_clean(snapshot)


def test_guard_fails_when_registered_template_content_drifts() -> None:
    snapshot = build_registry_drift_snapshot()
    template = snapshot.templates[0]

    with pytest.raises(RegistryDriftError, match=f"template:{template.module.id}@{template.module.version}"):
        assert_all_registry_hashes_clean(
            snapshot.with_template_content(template.module.id, "template drift"),
        )


def test_guard_fails_when_registered_rubric_content_drifts() -> None:
    snapshot = build_registry_drift_snapshot()
    rubric = next(iter(snapshot.rubrics))
    rubric.criteria.append(rubric.criteria[0])

    with pytest.raises(RegistryDriftError, match=f"rubric:{rubric.version_id}"):
        assert_all_registry_hashes_clean(snapshot)

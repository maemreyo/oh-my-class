from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from common.contracts.component_strategy_knowledge import (
    DEFAULT_KNOWLEDGE_SOURCE_PATH,
    KnowledgeQuery,
    KnowledgeValidationError,
    StaleKnowledgeIndexError,
    build_knowledge_index,
    default_capability_manifest_path,
    load_knowledge_source,
    open_knowledge_index,
    resolve_knowledge_ref,
    validate_knowledge_source,
)


def test_default_knowledge_source_covers_required_strategy_families() -> None:
    source = load_knowledge_source(DEFAULT_KNOWLEDGE_SOURCE_PATH)
    report = validate_knowledge_source(source)

    family_ids = {family.family_id for family in report.production_families}
    assert family_ids == {
        "concept_math_science",
        "exam_assessment_prep",
        "vocabulary_language",
    }


def test_default_knowledge_manifest_declares_capability_checksums() -> None:
    source = load_knowledge_source(DEFAULT_KNOWLEDGE_SOURCE_PATH)

    assert source.manifest.manifest_checksum != "computed-at-build"
    assert source.manifest.renderer_capability_checksum != "computed-at-build"
    assert source.manifest.exporter_capability_checksum != "computed-at-build"
    assert default_capability_manifest_path("renderer").exists()
    assert default_capability_manifest_path("exporter").exists()


def test_validation_rejects_stale_renderer_capability_checksum() -> None:
    source = load_knowledge_source(DEFAULT_KNOWLEDGE_SOURCE_PATH)
    broken = source.model_copy(update={"manifest": source.manifest.model_copy(update={"renderer_capability_checksum": "stale"})})

    with pytest.raises(KnowledgeValidationError, match="renderer capability checksum"):
        validate_knowledge_source(broken)


def test_validation_rejects_production_binding_missing_capability() -> None:
    source = load_knowledge_source(DEFAULT_KNOWLEDGE_SOURCE_PATH)
    broken = source.model_copy(
        update={
            "component_bindings": (
                source.component_bindings[0].model_copy(update={"component_type": "hw_list"}),
                *source.component_bindings[1:],
            )
        }
    )

    with pytest.raises(KnowledgeValidationError, match="unsupported renderer capability"):
        validate_knowledge_source(broken)


def test_validation_rejects_draft_entries_in_production_mode() -> None:
    source = load_knowledge_source(DEFAULT_KNOWLEDGE_SOURCE_PATH)
    broken = source.model_copy(
        update={"component_bindings": (source.component_bindings[0].model_copy(update={"lifecycle": "draft"}), *source.component_bindings[1:])}
    )

    with pytest.raises(KnowledgeValidationError, match="draft entry"):
        validate_knowledge_source(broken)

    report = validate_knowledge_source(broken, allow_draft=True)

    assert source.component_bindings[0].binding_id not in {binding.binding_id for binding in report.production_bindings}


def test_deprecated_entries_are_replay_resolvable_but_not_new_selectable() -> None:
    source = load_knowledge_source(DEFAULT_KNOWLEDGE_SOURCE_PATH)
    deprecated = source.component_bindings[0].model_copy(update={"lifecycle": "deprecated", "production_selectable": False})
    replay_source = source.model_copy(update={"component_bindings": (deprecated, *source.component_bindings[1:])})

    report = validate_knowledge_source(replay_source)
    resolved = resolve_knowledge_ref(replay_source, kind="component_binding", entry_id=deprecated.binding_id, version=deprecated.version)

    assert deprecated.binding_id not in {binding.binding_id for binding in report.production_bindings}
    assert resolved == deprecated


def test_validation_rejects_unknown_component_type() -> None:
    source = load_knowledge_source(DEFAULT_KNOWLEDGE_SOURCE_PATH)
    broken = source.model_copy(
        update={
            "component_bindings": (
                source.component_bindings[0].model_copy(update={"component_type": "missing_widget"}),
                *source.component_bindings[1:],
            )
        }
    )

    with pytest.raises(KnowledgeValidationError, match="unknown component"):
        validate_knowledge_source(broken)


def test_validation_rejects_required_binding_without_fallback_path() -> None:
    source = load_knowledge_source(DEFAULT_KNOWLEDGE_SOURCE_PATH)
    broken = source.model_copy(
        update={
            "fallback_policies": (
                source.fallback_policies[0].model_copy(update={"from_component_type": "active_recall_prompt"}),
                *source.fallback_policies[1:],
            )
        }
    )

    with pytest.raises(KnowledgeValidationError, match="missing required fallback"):
        validate_knowledge_source(broken)


def test_validation_rejects_circular_fallback_path() -> None:
    source = load_knowledge_source(DEFAULT_KNOWLEDGE_SOURCE_PATH)
    broken = source.model_copy(
        update={
            "fallback_policies": (
                source.fallback_policies[0].model_copy(update={"from_component_type": "table", "to_component_type": "flow_step"}),
                source.fallback_policies[1].model_copy(update={"from_component_type": "flow_step", "to_component_type": "table"}),
                *source.fallback_policies[2:],
            )
        }
    )

    with pytest.raises(KnowledgeValidationError, match="circular fallback"):
        validate_knowledge_source(broken)


def test_validation_rejects_no_fallback_policy_without_teacher_options() -> None:
    source = load_knowledge_source(DEFAULT_KNOWLEDGE_SOURCE_PATH)
    broken = source.model_copy(
        update={
            "fallback_policies": (
                source.fallback_policies[0].model_copy(
                    update={
                        "fallback_policy": "no_fallback_allowed",
                        "reason_code": "",
                        "severity": "",
                        "teacher_options": (),
                    }
                ),
                *source.fallback_policies[1:],
            )
        }
    )

    with pytest.raises(KnowledgeValidationError, match="no-fallback policy"):
        validate_knowledge_source(broken)


def test_sqlite_index_build_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.sqlite"
    second = tmp_path / "second.sqlite"

    first_manifest = build_knowledge_index(
        source_path=DEFAULT_KNOWLEDGE_SOURCE_PATH,
        output_path=first,
    )
    second_manifest = build_knowledge_index(
        source_path=DEFAULT_KNOWLEDGE_SOURCE_PATH,
        output_path=second,
    )

    assert first.read_bytes() == second.read_bytes()
    assert first_manifest.sqlite_checksum == second_manifest.sqlite_checksum


def test_read_only_runtime_query_filters_vocabulary_bindings(tmp_path: Path) -> None:
    index_path = tmp_path / "knowledge.sqlite"
    build_knowledge_index(source_path=DEFAULT_KNOWLEDGE_SOURCE_PATH, output_path=index_path)

    index = open_knowledge_index(
        index_path=index_path,
        source_path=DEFAULT_KNOWLEDGE_SOURCE_PATH,
    )
    results = index.query_bindings(
        KnowledgeQuery(
            artifact_type="lesson",
            subject_tag="language",
            grade_band="grade_4_6",
            bloom_level="understand",
            gagne_event="present_content",
            udl_tag="representation",
            max_duration_minutes=15,
            compliance_risk="low",
            strategy_family_id="vocabulary_language",
        )
    )

    assert {result.component_type for result in results} >= {
        "contrastive_pairs",
        "vocab_cluster",
    }


def test_runtime_fails_closed_when_yaml_source_is_stale(tmp_path: Path) -> None:
    source_path = tmp_path / "knowledge.yaml"
    index_path = tmp_path / "knowledge.sqlite"
    shutil.copyfile(DEFAULT_KNOWLEDGE_SOURCE_PATH, source_path)
    build_knowledge_index(source_path=source_path, output_path=index_path)
    source_path.write_text(source_path.read_text() + "\nextra_field: stale\n")

    with pytest.raises(StaleKnowledgeIndexError):
        open_knowledge_index(index_path=index_path, source_path=source_path)

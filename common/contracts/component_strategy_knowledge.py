from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import yaml

from common.contracts.components.registry import get_entry
from common.contracts.component_strategy_capabilities import (
    CapabilityValidationError,
    capability_manifest_path,
    require_renderer_capability,
    validate_manifest_checksums,
)
from common.contracts.component_strategy_fallback_validation import (
    FallbackKnowledgeValidationError,
    validate_fallback_graph,
)
from common.contracts.component_strategy_knowledge_models import (
    BuiltKnowledgeManifest,
    ComponentBindingEntry,
    ComponentKnowledgeSource,
    KnowledgeQuery,
    KnowledgeValidationReport,
    StrategyFamilyEntry,
)
from common.contracts.component_strategy_knowledge_index import (
    KnowledgeIndex,
    connect_read_only,
    create_schema,
    insert_bindings,
    insert_metadata,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KNOWLEDGE_SOURCE_PATH = PROJECT_ROOT / "common" / "component_strategy_knowledge" / "knowledge.yaml"

__all__ = [
    "DEFAULT_KNOWLEDGE_SOURCE_PATH",
    "KnowledgeIndex",
    "KnowledgeQuery",
    "KnowledgeValidationError",
    "StaleKnowledgeIndexError",
    "build_knowledge_index",
    "default_capability_manifest_path",
    "load_knowledge_source",
    "open_knowledge_index",
    "resolve_knowledge_ref",
    "validate_knowledge_source",
]


class KnowledgeValidationError(ValueError):
    pass


class StaleKnowledgeIndexError(ValueError):
    pass


def load_knowledge_source(path: Path = DEFAULT_KNOWLEDGE_SOURCE_PATH) -> ComponentKnowledgeSource:
    data = yaml.safe_load(path.read_text())
    return ComponentKnowledgeSource.model_validate(data)


def default_capability_manifest_path(kind: str) -> Path:
    return capability_manifest_path(PROJECT_ROOT, kind)


def validate_knowledge_source(
    source: ComponentKnowledgeSource,
    *,
    allow_draft: bool = False,
) -> KnowledgeValidationReport:
    try:
        renderer_capabilities, _exporter_capabilities = validate_manifest_checksums(
            source.manifest,
            default_capability_manifest_path("renderer"),
            default_capability_manifest_path("exporter"),
        )
    except CapabilityValidationError as exc:
        raise KnowledgeValidationError(str(exc)) from exc
    evidence_ids = {source.evidence_id for source in source.evidence_sources}
    move_ids = {move.move_id for move in source.learning_moves}
    family_ids = {family.family_id for family in source.strategy_families}
    profile_ids = {profile.scoring_profile_id for profile in source.scoring_profiles}
    fallback_ids = {policy.policy_id for policy in source.fallback_policies}
    supported_locales = set(source.manifest.supported_locales)

    for move in source.learning_moves:
        _require_lifecycle("learning move", move.move_id, move.lifecycle, move.production_selectable, allow_draft)
        _require_labels(move.move_id, move.labels, supported_locales, move.lifecycle)
        _require_known_ids("evidence", move.move_id, move.evidence_ids, evidence_ids)
        if move.lifecycle == "production" and move.production_selectable and not move.fill_validation_policy:
            raise KnowledgeValidationError(f"learning move {move.move_id} missing validation policy")

    for binding in source.component_bindings:
        _require_lifecycle("binding", binding.binding_id, binding.lifecycle, binding.production_selectable, allow_draft)
        _require_renderable_component(binding.component_type)
        try:
            require_renderer_capability(binding.component_type, renderer_capabilities)
        except CapabilityValidationError as exc:
            raise KnowledgeValidationError(str(exc)) from exc
        _require_labels(binding.binding_id, binding.labels, supported_locales, binding.lifecycle)
        _require_labels(binding.binding_id, binding.rationale_template, supported_locales, binding.lifecycle)
        _require_known_ids("evidence", binding.binding_id, binding.evidence_ids, evidence_ids)
        _require_known_ids("learning move", binding.binding_id, (binding.learning_move_id,), move_ids)
        _require_known_ids("strategy family", binding.binding_id, binding.strategy_family_ids, family_ids)
        _require_known_ids("fallback policy", binding.binding_id, (binding.fallback_policy_id,), fallback_ids)

    for family in source.strategy_families:
        _require_lifecycle("strategy family", family.family_id, family.lifecycle, family.production_selectable, allow_draft)
        _require_labels(family.family_id, family.labels, supported_locales, family.lifecycle)
        _require_known_ids("learning move", family.family_id, family.required_learning_move_ids, move_ids)
        _require_known_ids("scoring profile", family.family_id, (family.scoring_profile_id,), profile_ids)
        if family.lifecycle == "production" and family.production_selectable:
            _require_family_coverage(family, source.component_bindings)

    try:
        validate_fallback_graph(source.component_bindings, source.fallback_policies, _require_renderable_component)
    except FallbackKnowledgeValidationError as exc:
        raise KnowledgeValidationError(str(exc)) from exc

    for rule in source.contraindications:
        _require_lifecycle("rule", rule.rule_id, rule.lifecycle, True, allow_draft)
        _require_renderable_component(rule.component_type)
        if rule.priority is None and not rule.override_allowed:
            raise KnowledgeValidationError(f"rule {rule.rule_id} needs priority or override")

    return KnowledgeValidationReport(
        manifest=source.manifest,
        production_families=tuple(
            family for family in source.strategy_families if _is_selectable(family.lifecycle, family.production_selectable)
        ),
        production_bindings=tuple(
            binding for binding in source.component_bindings if _is_selectable(binding.lifecycle, binding.production_selectable)
        ),
    )


def resolve_knowledge_ref(
    source: ComponentKnowledgeSource,
    *,
    kind: str,
    entry_id: str,
    version: str,
) -> ComponentBindingEntry | StrategyFamilyEntry:
    if kind == "component_binding":
        for binding in source.component_bindings:
            if binding.binding_id == entry_id and binding.version == version:
                return binding
    if kind == "strategy_family":
        for family in source.strategy_families:
            if family.family_id == entry_id and family.version == version:
                return family
    raise KnowledgeValidationError(f"unknown knowledge ref {kind}:{entry_id}@{version}")


def build_knowledge_index(source_path: Path, output_path: Path) -> BuiltKnowledgeManifest:
    source = load_knowledge_source(source_path)
    report = validate_knowledge_source(source)
    source_checksum = _sha256_bytes(source_path.read_bytes())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()
    connection = sqlite3.connect(output_path)
    try:
        create_schema(connection)
        insert_metadata(connection, report.manifest, source_checksum)
        insert_bindings(connection, report.production_bindings)
        connection.commit()
        connection.execute("VACUUM")
    finally:
        connection.close()
    return BuiltKnowledgeManifest(
        knowledge_db_version=source.manifest.knowledge_db_version,
        source_checksum=source_checksum,
        sqlite_checksum=_sha256_bytes(output_path.read_bytes()),
        output_path=str(output_path),
    )


def open_knowledge_index(index_path: Path, source_path: Path) -> KnowledgeIndex:
    source_checksum = _sha256_bytes(source_path.read_bytes())
    connection = connect_read_only(index_path)
    try:
        stored_checksum = connection.execute(
            "SELECT value FROM metadata WHERE key = 'source_checksum'"
        ).fetchone()
    finally:
        connection.close()
    if stored_checksum is None or stored_checksum[0] != source_checksum:
        raise StaleKnowledgeIndexError("component strategy knowledge index is stale")
    return KnowledgeIndex(index_path=str(index_path))


def _require_renderable_component(component_type: str) -> None:
    try:
        entry = get_entry(component_type)
    except KeyError as exc:
        raise KnowledgeValidationError(f"unknown component {component_type}") from exc
    if entry.template is None:
        raise KnowledgeValidationError(f"non-renderable component {component_type}")


def _require_lifecycle(
    kind: str,
    entry_id: str,
    lifecycle: str,
    production_selectable: bool,
    allow_draft: bool,
) -> None:
    if lifecycle == "draft" and not allow_draft:
        raise KnowledgeValidationError(f"draft entry {kind} {entry_id} cannot pass production validation")
    if lifecycle == "deprecated" and production_selectable:
        raise KnowledgeValidationError(f"deprecated entry {kind} {entry_id} cannot be production selectable")


def _require_labels(
    entry_id: str,
    labels: dict[str, str],
    supported_locales: set[str],
    lifecycle: str,
) -> None:
    if lifecycle != "production":
        return
    missing = supported_locales.difference(labels)
    if missing:
        raise KnowledgeValidationError(f"{entry_id} missing locale copy: {sorted(missing)}")


def _require_known_ids(kind: str, owner_id: str, ids: tuple[str, ...], known_ids: set[str]) -> None:
    missing = [value for value in ids if value not in known_ids]
    if missing:
        raise KnowledgeValidationError(f"{owner_id} references unknown {kind}: {missing}")


def _require_family_coverage(
    family: StrategyFamilyEntry,
    bindings: tuple[ComponentBindingEntry, ...],
) -> None:
    covered_moves = {
        binding.learning_move_id
        for binding in bindings
        if family.family_id in binding.strategy_family_ids
        and _is_selectable(binding.lifecycle, binding.production_selectable)
    }
    missing = set(family.required_learning_move_ids).difference(covered_moves)
    if missing:
        raise KnowledgeValidationError(f"family {family.family_id} lacks coverage for {sorted(missing)}")


def _is_selectable(lifecycle: str, production_selectable: bool) -> bool:
    return lifecycle == "production" and production_selectable


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

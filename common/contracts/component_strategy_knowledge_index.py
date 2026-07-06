from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from common.contracts.component_strategy_knowledge_models import (
    ComponentBindingEntry,
    KnowledgeBindingResult,
    KnowledgeManifest,
    KnowledgeQuery,
)


@dataclass(frozen=True, slots=True)
class KnowledgeRuntimePolicy:
    query_only: bool
    immutable: bool


class KnowledgeIndex:
    def __init__(self, index_path: str, runtime_policy: KnowledgeRuntimePolicy | None = None) -> None:
        self.index_path = index_path
        self.runtime_policy = runtime_policy or KnowledgeRuntimePolicy(query_only=True, immutable=False)

    def query_bindings(self, query: KnowledgeQuery) -> tuple[KnowledgeBindingResult, ...]:
        connection = connect_read_only(Path(self.index_path), immutable=self.runtime_policy.immutable)
        try:
            rows = connection.execute(
                "SELECT binding_json FROM component_bindings ORDER BY binding_id"
            ).fetchall()
        finally:
            connection.close()
        bindings = [ComponentBindingEntry.model_validate_json(row[0]) for row in rows]
        return tuple(_to_result(binding) for binding in bindings if _matches(binding, query))

    def assert_mutation_blocked(self) -> None:
        connection = connect_read_only(Path(self.index_path), immutable=self.runtime_policy.immutable)
        try:
            connection.execute("CREATE TABLE mutation_probe (id TEXT)")
        except sqlite3.DatabaseError as exc:
            raise PermissionError("component strategy knowledge index is read-only") from exc
        finally:
            connection.close()


def connect_read_only(path: Path, *, immutable: bool = False) -> sqlite3.Connection:
    immutable_arg = "&immutable=1" if immutable else ""
    connection = sqlite3.connect(f"file:{path}?mode=ro{immutable_arg}", uri=True)
    connection.execute("PRAGMA query_only=ON")
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE component_bindings (
            binding_id TEXT PRIMARY KEY,
            component_type TEXT NOT NULL,
            learning_move_id TEXT NOT NULL,
            binding_json TEXT NOT NULL
        );
        """
    )


def insert_metadata(
    connection: sqlite3.Connection,
    manifest: KnowledgeManifest,
    source_checksum: str,
) -> None:
    values = {
        "knowledge_db_version": manifest.knowledge_db_version,
        "manifest_checksum": manifest.manifest_checksum,
        "source_checksum": source_checksum,
        "renderer_capability_checksum": manifest.renderer_capability_checksum,
        "exporter_capability_checksum": manifest.exporter_capability_checksum,
        "compatible_strategy_schema_versions": json.dumps(manifest.compatible_strategy_schema_versions),
        "compatible_selector_versions": json.dumps(manifest.compatible_selector_versions),
        "supported_locales": json.dumps(manifest.supported_locales),
    }
    connection.executemany(
        "INSERT INTO metadata (key, value) VALUES (?, ?)",
        sorted(values.items()),
    )


def insert_bindings(
    connection: sqlite3.Connection,
    bindings: tuple[ComponentBindingEntry, ...],
) -> None:
    rows = [
        (
            binding.binding_id,
            binding.component_type,
            binding.learning_move_id,
            binding.model_dump_json(),
        )
        for binding in sorted(bindings, key=lambda item: item.binding_id)
    ]
    connection.executemany("INSERT INTO component_bindings VALUES (?, ?, ?, ?)", rows)


def _matches(binding: ComponentBindingEntry, query: KnowledgeQuery) -> bool:
    return (
        _contains_or_empty(binding.artifact_types, query.artifact_type)
        and _contains_or_empty(binding.subject_tags, query.subject_tag)
        and _contains_or_empty(binding.grade_bands, query.grade_band)
        and _contains_or_empty(binding.bloom_levels, query.bloom_level)
        and _contains_or_empty(binding.moet_levels, query.moet_level)
        and _contains_or_empty(binding.gagne_events, query.gagne_event)
        and _contains_or_empty(binding.udl_tags, query.udl_tag)
        and _contains_or_empty(binding.strategy_family_ids, query.strategy_family_id)
        and (query.max_duration_minutes is None or binding.duration_min_minutes <= query.max_duration_minutes)
        and (query.compliance_risk is None or binding.compliance_risk == query.compliance_risk)
    )


def _contains_or_empty(values: tuple[str, ...], expected: str | None) -> bool:
    return expected is None or expected in values


def _to_result(binding: ComponentBindingEntry) -> KnowledgeBindingResult:
    return KnowledgeBindingResult(
        binding_id=binding.binding_id,
        component_type=binding.component_type,
        learning_move_id=binding.learning_move_id,
        strategy_family_ids=binding.strategy_family_ids,
        artifact_types=binding.artifact_types,
        duration_max_minutes=binding.duration_max_minutes,
        compliance_risk=binding.compliance_risk,
    )

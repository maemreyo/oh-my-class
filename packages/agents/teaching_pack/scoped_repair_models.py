from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypedDict

from common.contracts.quality import QualityFailureClass

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]

type RepairStrategy = Literal[
    "schema_repair",
    "answer_key_repair",
    "pii_removal",
    "presentation_repair",
    "accessibility_repair",
    "research_enrichment",
    "replan_blueprint",
    "inject_required_component",
    "regenerate_artifact",
]


class RepairDiff(TypedDict):
    status: str
    changed_path: str
    previous_hash: str
    next_hash: str


class RepairEvent(TypedDict):
    event_name: str
    payload: JsonObject


@dataclass(frozen=True, slots=True)
class RepairScope:
    artifact_id: str
    section_index: int | None = None
    component_index: int | None = None


@dataclass(frozen=True, slots=True)
class ScopedRepairPlan:
    scope: RepairScope
    failure_class: QualityFailureClass
    strategy: RepairStrategy
    message: str


@dataclass(frozen=True, slots=True)
class ContentVersion:
    artifact_id: str
    content_hash: str
    parent_hash: str | None
    revision: int
    reason: str


@dataclass(frozen=True, slots=True)
class ScopedRepairUpdate:
    artifact: JsonObject
    version: ContentVersion
    diff: RepairDiff
    event: RepairEvent
    escalate_to_teacher: bool


@dataclass(slots=True)
class ContentVersionStore:  # noqa: MUTABLE_OK
    _versions: dict[str, list[ContentVersion]] = field(default_factory=dict)

    def snapshot(self, artifact: JsonObject, reason: str) -> ContentVersion:
        from packages.agents.teaching_pack.scoped_repair_hashing import content_hash

        artifact_id = artifact_identifier(artifact)
        parent = self.latest(artifact_id)
        version = ContentVersion(
            artifact_id=artifact_id,
            content_hash=content_hash(artifact),
            parent_hash=parent.content_hash if parent else None,
            revision=len(self._versions.get(artifact_id, [])) + 1,
            reason=reason,
        )
        self._versions.setdefault(artifact_id, []).append(version)
        return version

    def latest(self, artifact_id: str) -> ContentVersion | None:
        versions = self._versions.get(artifact_id, [])
        if versions:
            return versions[-1]
        return None


def artifact_identifier(artifact: JsonObject) -> str:
    value = artifact.get("artifact_id", artifact.get("id", "artifact"))
    return str(value)

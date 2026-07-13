"""Stable-ID, dependency-aware Pack Coherence report."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

JsonObject = dict[str, Any]
Severity = Literal["info", "warning", "critical"]

_TEACHER_ONLY_KEYS = frozenset({"answer", "correct_answer", "correct_option_ids", "rationale", "teacher_notes"})


class PackCoherenceFinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    finding_id: str = Field(min_length=1, max_length=160)
    code: str = Field(min_length=1, max_length=120)
    severity: Severity
    affected_entity_ids: tuple[str, ...] = Field(min_length=1)
    evidence: tuple[str, ...] = Field(min_length=1)
    owner: str = Field(min_length=1, max_length=80)
    repair_scope: tuple[str, ...] = Field(min_length=1)
    teacher_options: tuple[str, ...] = Field(min_length=1)


class PackCoherenceReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    report_version: str = "pack_coherence.v1"
    passed: bool
    input_document_ids: tuple[str, ...]
    findings: tuple[PackCoherenceFinding, ...] = ()
    blocked_exports: tuple[str, ...] = ()

    @property
    def issue_messages(self) -> list[str]:
        return [
            f"pack.coherence:{finding.code}:{','.join(finding.affected_entity_ids)}"
            for finding in self.findings
            if finding.severity == "critical"
        ]


def evaluate_pack_coherence(artifacts: list[JsonObject]) -> PackCoherenceReport:
    findings: list[PackCoherenceFinding] = []
    document_ids = tuple(
        str(artifact.get("document_id") or artifact.get("artifact_id") or f"artifact-{index}")
        for index, artifact in enumerate(artifacts, start=1)
    )
    by_type = {str(artifact.get("artifact_type")): artifact for artifact in artifacts}
    lesson_objectives = _lesson_objective_ids(by_type.get("lesson"))
    if lesson_objectives:
        for artifact in artifacts:
            artifact_type = str(artifact.get("artifact_type") or "unknown")
            if artifact_type in {"lesson", "answer_key"}:
                continue
            used = _artifact_objective_ids(artifact)
            unknown = sorted(used - lesson_objectives)
            if unknown:
                findings.append(_finding(
                    code="unknown_objective_lineage",
                    severity="critical",
                    entity_ids=tuple(unknown),
                    evidence=(f"{artifact_type} references objectives absent from approved lesson",),
                    owner=artifact_type,
                    repair_scope=(artifact_type,),
                ))
    if "answer_key" in by_type and "quiz" not in by_type:
        findings.append(_finding(
            code="answer_key_without_quiz",
            severity="critical",
            entity_ids=("answer_key",),
            evidence=("answer_key has no quiz dependency",),
            owner="assessment",
            repair_scope=("answer_key",),
        ))
    for artifact in artifacts:
        artifact_id = str(artifact.get("artifact_id") or artifact.get("artifact_type") or "artifact")
        leaked = _first_teacher_only_path(artifact.get("sections"), "sections")
        if leaked is not None:
            findings.append(_finding(
                code="student_projection_leakage",
                severity="critical",
                entity_ids=(artifact_id,),
                evidence=(leaked,),
                owner="projection",
                repair_scope=(artifact_id,),
            ))
    definitions: dict[str, tuple[str, str]] = {}
    for artifact in artifacts:
        metadata = artifact.get("metadata")
        if not isinstance(metadata, dict):
            continue
        raw = metadata.get("terminology_definitions")
        if not isinstance(raw, dict):
            continue
        artifact_id = str(artifact.get("artifact_id") or artifact.get("artifact_type") or "artifact")
        for term, definition in raw.items():
            normalized_term = str(term).strip().casefold()
            normalized_definition = " ".join(str(definition).strip().casefold().split())
            previous = definitions.get(normalized_term)
            if previous is not None and previous[0] != normalized_definition:
                findings.append(_finding(
                    code="terminology_contradiction",
                    severity="critical",
                    entity_ids=(previous[1], artifact_id, normalized_term),
                    evidence=(previous[0], normalized_definition),
                    owner="synthesis",
                    repair_scope=(artifact_id,),
                ))
            else:
                definitions[normalized_term] = (normalized_definition, artifact_id)
    versions = {
        str(metadata.get("knowledge_db_version"))
        for artifact in artifacts
        if isinstance((metadata := artifact.get("metadata")), dict) and metadata.get("knowledge_db_version")
    }
    if len(versions) > 1:
        findings.append(_finding(
            code="mixed_knowledge_snapshot",
            severity="critical",
            entity_ids=tuple(sorted(versions)),
            evidence=("pack artifacts pin different Content Intelligence Graph snapshots",),
            owner="orchestrator",
            repair_scope=tuple(document_ids),
        ))
    blocked = ("composite_export", "live_publication") if any(
        finding.severity == "critical" for finding in findings
    ) else ()
    return PackCoherenceReport(
        passed=not blocked,
        input_document_ids=document_ids,
        findings=tuple(findings),
        blocked_exports=blocked,
    )


def _finding(
    *,
    code: str,
    severity: Severity,
    entity_ids: tuple[str, ...],
    evidence: tuple[str, ...],
    owner: str,
    repair_scope: tuple[str, ...],
) -> PackCoherenceFinding:
    return PackCoherenceFinding(
        finding_id=f"coherence:{code}:{':'.join(entity_ids)}",
        code=code,
        severity=severity,
        affected_entity_ids=entity_ids,
        evidence=evidence,
        owner=owner,
        repair_scope=repair_scope,
        teacher_options=("review", "repair_scope", "keep_blocked"),
    )


def _lesson_objective_ids(lesson: JsonObject | None) -> set[str]:
    if lesson is None:
        return set()
    metadata = lesson.get("metadata")
    if isinstance(metadata, dict):
        approved = metadata.get("approved_objective_ids")
        if isinstance(approved, list):
            return {str(value) for value in approved}
    return _artifact_objective_ids(lesson)


def _artifact_objective_ids(artifact: JsonObject) -> set[str]:
    metadata = artifact.get("metadata")
    if not isinstance(metadata, dict):
        return set()
    result: set[str] = set()
    lineage = metadata.get("objective_lineage")
    if isinstance(lineage, list):
        for entry in lineage:
            if isinstance(entry, dict) and entry.get("objective_id"):
                result.add(str(entry["objective_id"]))
    blueprints = metadata.get("item_blueprints")
    if isinstance(blueprints, list):
        for entry in blueprints:
            if isinstance(entry, dict) and entry.get("objective_id"):
                result.add(str(entry["objective_id"]))
    return result


def _first_teacher_only_path(value: Any, path: str) -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            nested_path = f"{path}.{key}"
            if str(key).casefold() in _TEACHER_ONLY_KEYS:
                return nested_path
            found = _first_teacher_only_path(nested, nested_path)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found = _first_teacher_only_path(nested, f"{path}[{index}]")
            if found is not None:
                return found
    return None

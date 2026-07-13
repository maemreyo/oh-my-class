"""#496: typed Artifact Compiler Framework over shared Program/Semantic IR."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from pydantic import Field

from common.contracts.pedagogical_compiler.common import FrozenContract, stable_hash, stable_id
from common.contracts.pedagogical_compiler.program_ir import PedagogicalProgramIR
from common.contracts.pedagogical_compiler.semantic_ir import SemanticContentIR, SemanticEntity

ProjectionDisposition = Literal["preserved", "transformed", "split", "merged", "omitted_teacher_only", "unsupported", "failed"]


class SurfaceConstraint(FrozenContract):
    constraint_id: str
    key: str
    value: Any
    hard: bool = True


class EntityProjection(FrozenContract):
    semantic_id: str
    disposition: ProjectionDisposition
    target_entity_ids: tuple[str, ...] = ()
    rationale: str


class CompileDiagnostic(FrozenContract):
    code: str
    severity: Literal["info", "warning", "critical"]
    semantic_ids: tuple[str, ...]
    message: str


class ArtifactCompileRequest(FrozenContract):
    request_id: str
    artifact_type: str
    audience: Literal["student", "teacher", "shared"]
    program_id: str
    program_hash: str
    semantic_ir_id: str
    semantic_hash: str
    compiler_version: str
    policy_version: str
    surface_constraints: tuple[SurfaceConstraint, ...] = ()


class ArtifactCompileResult(FrozenContract):
    request: ArtifactCompileRequest
    artifact: dict[str, Any]
    projections: tuple[EntityProjection, ...]
    diagnostics: tuple[CompileDiagnostic, ...] = ()
    compile_hash: str


def compile_existing_artifact(
    artifact: dict[str, Any],
    *,
    program: PedagogicalProgramIR,
    semantic_ir: SemanticContentIR,
    compiler_version: str = "artifact_compiler.v1",
    policy_version: str = "artifact_projection_policy.v1",
    audience: Literal["student", "teacher", "shared"] = "student",
) -> ArtifactCompileResult:
    artifact_type = str(artifact.get("artifact_type") or "")
    if not artifact_type:
        raise ValueError("artifact compiler requires artifact_type")
    request = ArtifactCompileRequest(
        request_id=stable_id("artifact-compile", program.program_hash, semantic_ir.semantic_hash, artifact_type, audience),
        artifact_type=artifact_type,
        audience=audience,
        program_id=program.program_id,
        program_hash=program.program_hash,
        semantic_ir_id=semantic_ir.semantic_ir_id,
        semantic_hash=semantic_ir.semantic_hash,
        compiler_version=compiler_version,
        policy_version=policy_version,
        surface_constraints=(
            SurfaceConstraint(constraint_id="surface:answer-separation", key="student_answer_separation", value=True),
            SurfaceConstraint(constraint_id="surface:semantic-accounting", key="entity_projection_required", value=True),
        ),
    )
    projections = tuple(_projection(entity, artifact_type, audience) for entity in semantic_ir.entities)
    unaccounted = [item.semantic_id for item in projections if item.disposition in {"unsupported", "failed"}]
    if unaccounted:
        raise ValueError(f"artifact compiler left semantic entities unaccounted: {unaccounted}")
    compiled = deepcopy(artifact)
    metadata = compiled.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        compiled["metadata"] = metadata
    metadata["pedagogical_compiler"] = {
        "program_id": program.program_id,
        "program_hash": program.program_hash,
        "semantic_ir_id": semantic_ir.semantic_ir_id,
        "semantic_hash": semantic_ir.semantic_hash,
        "compiler_version": compiler_version,
        "policy_version": policy_version,
        "move_ids": [move.move_id for phase in program.phases for move in phase.moves],
        "entity_projection_map": [projection.model_dump(mode="json") for projection in projections],
    }
    payload = {
        "request": request,
        "artifact": compiled,
        "projections": projections,
        "diagnostics": (),
    }
    payload["compile_hash"] = stable_hash("artifact-compile", payload)
    return ArtifactCompileResult.model_validate(payload)


def _projection(entity: SemanticEntity, artifact_type: str, audience: str) -> EntityProjection:
    if entity.kind in {"answer_derivation", "distractor_rationale"} and audience == "student":
        return EntityProjection(
            semantic_id=entity.semantic_id,
            disposition="omitted_teacher_only",
            rationale="teacher-only semantic authority remains in AnswerSet/teacher projection",
        )
    if artifact_type in entity.artifact_eligibility:
        return EntityProjection(
            semantic_id=entity.semantic_id,
            disposition="transformed",
            target_entity_ids=(stable_id("projection", artifact_type, entity.semantic_id),),
            rationale="surface wording may change while stable semantic lineage is preserved",
        )
    return EntityProjection(
        semantic_id=entity.semantic_id,
        disposition="preserved",
        target_entity_ids=(),
        rationale="entity retained in shared semantic authority but intentionally absent from this surface",
    )

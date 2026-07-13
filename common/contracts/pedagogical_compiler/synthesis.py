"""#495: verification-guided, multi-pass semantic synthesis."""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from common.contracts.pedagogical_compiler.common import FrozenContract, stable_hash, stable_id
from common.contracts.pedagogical_compiler.program_ir import PedagogicalProgramIR
from common.contracts.pedagogical_compiler.semantic_ir import SemanticContentIR, SemanticEntity
from common.contracts.pedagogical_compiler.tools import (
    DomainToolRuntime,
    ToolPolicy,
    ToolReceipt,
    ToolRequest,
)


class EntityRequirement(FrozenContract):
    requirement_id: str
    semantic_kind: str
    objective_ids: tuple[str, ...]
    hard: bool
    verification_rules: tuple[str, ...]


class SynthesisPlan(FrozenContract):
    plan_id: str
    program_id: str
    semantic_ir_id: str
    requirements: tuple[EntityRequirement, ...]
    max_candidates_per_requirement: int = Field(default=2, ge=1, le=8)
    max_repairs_per_entity: int = Field(default=1, ge=0, le=4)


class CandidateEntity(FrozenContract):
    candidate_id: str
    requirement_id: str
    semantic_id: str
    content_hash: str
    source: Literal["deterministic", "model_candidate", "teacher"]


class VerificationResult(FrozenContract):
    candidate_id: str
    passed: bool
    hard_failures: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    tool_receipt_ids: tuple[str, ...] = ()


class SelectionResult(FrozenContract):
    requirement_id: str
    selected_candidate_id: str | None
    rejected_candidate_ids: tuple[str, ...]
    review_required: bool = False


class RepairPlan(FrozenContract):
    repair_id: str
    semantic_id: str
    failure_codes: tuple[str, ...]
    preserved_semantic_ids: tuple[str, ...]
    attempt: int = Field(ge=1)


class SynthesisReceipt(FrozenContract):
    receipt_id: str
    requirement: EntityRequirement
    candidates: tuple[CandidateEntity, ...]
    verifications: tuple[VerificationResult, ...]
    selection: SelectionResult
    repairs: tuple[RepairPlan, ...] = ()
    receipt_hash: str


class MultiPassSynthesisResult(FrozenContract):
    plan: SynthesisPlan
    selected_semantic_ir: SemanticContentIR
    receipts: tuple[SynthesisReceipt, ...]
    tool_receipts: tuple[ToolReceipt, ...] = ()


def synthesize_semantic_content(
    program: PedagogicalProgramIR,
    semantic_ir: SemanticContentIR,
    *,
    tool_runtime: DomainToolRuntime | None = None,
    tenant_scope: str = "system",
    tool_policy_version: str = "domain_tools.v1",
) -> MultiPassSynthesisResult:
    requirements = tuple(
        EntityRequirement(
            requirement_id=stable_id("entity-requirement", program.program_hash, entity.semantic_id),
            semantic_kind=entity.kind,
            objective_ids=entity.objective_ids,
            hard=entity.kind in {"claim", "definition", "question_stem", "answer_derivation"},
            verification_rules=_verification_rules(entity),
        )
        for entity in semantic_ir.entities
    )
    plan = SynthesisPlan(
        plan_id=stable_id("synthesis-plan", program.program_hash, semantic_ir.semantic_hash),
        program_id=program.program_id,
        semantic_ir_id=semantic_ir.semantic_ir_id,
        requirements=requirements,
    )
    receipts: list[SynthesisReceipt] = []
    tool_receipts: list[ToolReceipt] = []
    for requirement, entity in zip(requirements, semantic_ir.entities, strict=True):
        candidate = CandidateEntity(
            candidate_id=stable_id("candidate-entity", requirement.requirement_id, entity.semantic_id, entity.text),
            requirement_id=requirement.requirement_id,
            semantic_id=entity.semantic_id,
            content_hash=stable_hash("entity", entity),
            source="deterministic",
        )
        failures = _hard_failures(entity)
        receipt_ids: list[str] = []
        if tool_runtime is not None:
            tool_result, tool_receipt = tool_runtime.execute(ToolRequest(
                request_id=stable_id("tool-request", plan.plan_id, entity.semantic_id, "readability"),
                tool_id="readability",
                input={"text": entity.text},
                tenant_scope=tenant_scope,
                policy=ToolPolicy(policy_version=tool_policy_version),
            ))
            tool_receipts.append(tool_receipt)
            receipt_ids.append(tool_receipt.receipt_id)
            if tool_result.status not in {"verified", "unsupported"} and requirement.hard:
                failures.append(f"tool:{tool_result.status}")
        passed = not failures
        verification = VerificationResult(
            candidate_id=candidate.candidate_id,
            passed=passed,
            hard_failures=tuple(failures),
            evidence_ids=entity.source_evidence_ids,
            tool_receipt_ids=tuple(receipt_ids),
        )
        selection = SelectionResult(
            requirement_id=requirement.requirement_id,
            selected_candidate_id=candidate.candidate_id if passed or entity.authority == "review_required" else None,
            rejected_candidate_ids=() if passed or entity.authority == "review_required" else (candidate.candidate_id,),
            review_required=entity.authority == "review_required",
        )
        base = {
            "receipt_id": stable_id("synthesis-receipt", plan.plan_id, requirement.requirement_id),
            "requirement": requirement,
            "candidates": (candidate,),
            "verifications": (verification,),
            "selection": selection,
            "repairs": (),
        }
        base["receipt_hash"] = stable_hash("synthesis-receipt", base)
        receipts.append(SynthesisReceipt.model_validate(base))
    return MultiPassSynthesisResult(
        plan=plan,
        selected_semantic_ir=semantic_ir,
        receipts=tuple(receipts),
        tool_receipts=tuple(tool_receipts),
    )


def scoped_repair(
    result: MultiPassSynthesisResult,
    *,
    semantic_id: str,
    replacement: SemanticEntity,
    failure_codes: tuple[str, ...],
) -> MultiPassSynthesisResult:
    if replacement.semantic_id != semantic_id:
        raise ValueError("scoped repair replacement must preserve semantic ID")
    original = result.selected_semantic_ir.entity(semantic_id)
    if original.objective_ids != replacement.objective_ids or original.kc_ids != replacement.kc_ids:
        raise ValueError("scoped repair cannot change objective/KC lineage")
    entities = tuple(replacement if entity.semantic_id == semantic_id else entity for entity in result.selected_semantic_ir.entities)
    base = result.selected_semantic_ir.model_dump(mode="python", exclude={"semantic_hash"})
    base["entities"] = entities
    base["version"] = result.selected_semantic_ir.version + 1
    base["semantic_hash"] = stable_hash("semantic-ir", base)
    updated_ir = SemanticContentIR.model_validate(base)
    preserved = tuple(sorted(entity.semantic_id for entity in entities if entity.semantic_id != semantic_id))
    updated_receipts: list[SynthesisReceipt] = []
    for receipt in result.receipts:
        if receipt.selection.selected_candidate_id and any(candidate.semantic_id == semantic_id for candidate in receipt.candidates):
            repair = RepairPlan(
                repair_id=stable_id("repair", receipt.receipt_id, updated_ir.version), semantic_id=semantic_id,
                failure_codes=failure_codes, preserved_semantic_ids=preserved, attempt=1,
            )
            payload = receipt.model_dump(mode="python", exclude={"receipt_hash"})
            payload["repairs"] = (*receipt.repairs, repair)
            payload["receipt_hash"] = stable_hash("synthesis-receipt", payload)
            updated_receipts.append(SynthesisReceipt.model_validate(payload))
        else:
            updated_receipts.append(receipt)
    return result.model_copy(update={"selected_semantic_ir": updated_ir, "receipts": tuple(updated_receipts)})


def _verification_rules(entity: SemanticEntity) -> tuple[str, ...]:
    rules = ["schema", "objective_kc_lineage", "terminology", "age_language", "semantic_duplication"]
    if entity.kind in {"claim", "definition"}:
        rules.append("evidence_entailment")
    if entity.kind == "answer_derivation":
        rules.extend(["answer_derivation", "teacher_only_separation"])
    return tuple(rules)


def _hard_failures(entity: SemanticEntity) -> list[str]:
    failures: list[str] = []
    if entity.kind in {"claim", "definition"} and entity.authority == "verified" and not entity.source_evidence_ids:
        failures.append("missing_evidence")
    if entity.kind == "answer_derivation" and entity.audience != "teacher":
        failures.append("answer_leakage")
    if entity.authority == "unsupported":
        failures.append("unsupported_authority")
    return failures

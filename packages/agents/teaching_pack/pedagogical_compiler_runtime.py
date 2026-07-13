"""Live adapter from typed Content Orchestrator requests to compiler authority."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from common.contracts.pedagogical_compiler import (
    MultiPassSynthesisResult,
    ObjectiveGraph,
    OptimizationPolicy,
    PedagogicalProgramIR,
    SelectionDecision,
    SemanticContentIR,
    TeachingIntent,
    build_objective_graph,
    build_program_ir,
    build_semantic_ir,
    candidate_from_program,
    compile_existing_artifact,
    compile_teaching_intent,
    default_tool_runtime,
    optimize_programs,
    synthesize_semantic_content,
)


@dataclass(frozen=True, slots=True)
class CompilerContext:
    intent: TeachingIntent
    objective_graph: ObjectiveGraph
    program: PedagogicalProgramIR
    semantic_ir: SemanticContentIR
    optimization: SelectionDecision
    synthesis: MultiPassSynthesisResult


def compile_intelligence_context(request: Any) -> CompilerContext:
    lesson_plan = dict(request.lesson_plan)
    brief = {
        "topic": lesson_plan.get("topic") or lesson_plan.get("title") or "Teaching pack",
        "grade": lesson_plan.get("grade") or lesson_plan.get("grade_level") or _grade_for_band(getattr(request, "grade_band", "grades_3_5")),
        "subject": lesson_plan.get("subject") or getattr(request, "subject", "general") or "general",
        "target_language": lesson_plan.get("target_language") or lesson_plan.get("locale") or "en",
        "instruction_language": lesson_plan.get("instruction_language") or lesson_plan.get("locale") or "en",
        "curriculum": lesson_plan.get("curriculum"),
        "duration_minutes": lesson_plan.get("duration_minutes") or 45,
        "artifact_types": (request.artifact_type,),
        "export_formats": ("html",),
        "learning_objectives": [
            {"description": objective} for objective in request.content_brief.objectives
        ],
        "research_policy": "rigorous" if request.content_brief.source_citation_ids else "standard",
    }
    intent = compile_teaching_intent(brief)
    if not intent.is_ready:
        fields = ", ".join(item.field for item in intent.clarifications if item.blocking)
        raise ValueError(f"TeachingIntent requires clarification before generation: {fields}")
    graph = build_objective_graph(
        intent,
        knowledge_snapshot_version=request.content_brief.knowledge_db_version or "knowledge-unpinned",
        objective_nodes=_objective_nodes(request),
    )
    program = build_program_ir(
        intent,
        graph,
        methodology=request.content_brief.methodology,
    )
    policy = OptimizationPolicy(
        policy_version="pedagogical_optimizer.v1",
        seed=0,
        metric_weights={"coverage": 0.45, "evidence_density": 0.35, "sequencing": 0.20},
        lexicographic_priority=("coverage", "sequencing"),
    )
    optimization = optimize_programs((candidate_from_program(program),), policy)
    if optimization.selected_candidate_id is None:
        raise ValueError("Pedagogical optimizer found no feasible program")
    semantic_ir = build_semantic_ir(
        program,
        graph,
        language=intent.instruction_language or "en",
    )
    synthesis = synthesize_semantic_content(
        program,
        semantic_ir,
        tool_runtime=default_tool_runtime(),
        tenant_scope=request.tenant.organization_id,
    )
    return CompilerContext(
        intent=intent,
        objective_graph=graph,
        program=program,
        semantic_ir=semantic_ir,
        optimization=optimization,
        synthesis=synthesis,
    )


def compile_artifact_with_context(artifact: dict[str, Any], context: CompilerContext) -> dict[str, Any]:
    result = compile_existing_artifact(
        artifact,
        program=context.program,
        semantic_ir=context.synthesis.selected_semantic_ir,
        audience="teacher" if artifact.get("artifact_type") == "answer_key" else "student",
    )
    compiled = result.artifact
    metadata = compiled.setdefault("metadata", {})
    if isinstance(metadata, dict):
        metadata["teaching_intent_id"] = context.intent.intent_id
        metadata["teaching_intent_hash"] = context.intent.intent_hash
        metadata["objective_graph_id"] = context.objective_graph.graph_id
        metadata["objective_graph_hash"] = context.objective_graph.graph_hash
        metadata["optimizer_decision_id"] = context.optimization.decision_id
        metadata["optimizer_decision_hash"] = context.optimization.decision_hash
        metadata["synthesis_plan_id"] = context.synthesis.plan.plan_id
        metadata["synthesis_receipt_ids"] = [receipt.receipt_id for receipt in context.synthesis.receipts]
        metadata["artifact_compile_hash"] = result.compile_hash
    return compiled


def _objective_nodes(request: Any) -> tuple[dict[str, Any], ...]:
    research = dict(request.research_brief)
    sources = research.get("sources")
    evidence_ids = tuple(
        str(source.get("source_id") or source.get("title") or source.get("url"))
        for source in sources
        if isinstance(source, dict) and source.get("excerpt")
    ) if isinstance(sources, list) else ()
    return tuple(
        {
            "objective_id": f"brief:{request.content_brief.content_brief_id}:{index}",
            "description": objective,
            "knowledge_component_ids": (f"brief-kc:{request.content_brief.content_brief_id}:{index}",),
            "evidence_ids": evidence_ids,
            "review_status": "reviewed" if evidence_ids else "candidate",
            "source_node_id": request.content_brief.knowledge_db_version,
        }
        for index, objective in enumerate(request.content_brief.objectives, start=1)
    )


def _grade_for_band(value: str) -> int:
    return {
        "k_2": 2,
        "grades_3_5": 5,
        "grades_6_8": 8,
        "grades_9_12": 12,
    }.get(str(value), 5)

from __future__ import annotations

from common.contracts.pedagogical_compiler import (
    CandidateProgram,
    ConstraintResult,
    OptimizationPolicy,
    ToolPolicy,
    ToolRequest,
    build_objective_graph,
    build_program_ir,
    build_semantic_ir,
    candidate_from_program,
    compile_existing_artifact,
    compile_teaching_intent,
    default_tool_runtime,
    optimize_programs,
    scoped_repair,
    synthesize_semantic_content,
)


def _brief() -> dict[str, object]:
    return {
        "topic": "Equivalent Fractions!",
        "grade": 5,
        "subject": "Math",
        "target_language": "English",
        "instruction_language": "English",
        "duration_minutes": 45,
        "artifact_types": ["lesson", "quiz"],
        "learning_objectives": [
            {"description": "Identify equivalent fractions and generate an equivalent fraction."},
        ],
    }


def _kernel():
    intent = compile_teaching_intent(_brief())
    graph = build_objective_graph(intent, knowledge_snapshot_version="graph-v1")
    program = build_program_ir(intent, graph)
    semantic = build_semantic_ir(program, graph, language="en")
    return intent, graph, program, semantic


def test_teaching_intent_is_deterministic_and_punctuation_invariant() -> None:
    first = compile_teaching_intent(_brief())
    second_brief = _brief()
    second_brief["topic"] = "  Equivalent   Fractions  "
    second = compile_teaching_intent(second_brief)

    assert first.intent_hash == second.intent_hash
    assert first.grade_band == "grades_3_5"
    assert first.is_ready


def test_teaching_intent_material_ambiguity_blocks() -> None:
    intent = compile_teaching_intent({"topic": "Fractions", "artifact_types": ["lesson"]})

    assert not intent.is_ready
    assert {item.field for item in intent.clarifications} >= {"grade", "subject", "target_language", "instruction_language"}


def test_objective_graph_decomposes_atomic_objectives_without_session_kc_ids() -> None:
    intent, graph, _program, _semantic = _kernel()

    assert len(graph.objectives) == 2
    assert all(not kc.kc_id.startswith("KC-S") for objective in graph.objectives for kc in objective.knowledge_components)
    assert {claim.objective_id for claim in graph.mastery_claims} == {item.objective_id for item in graph.objectives}
    assert graph.intent_id == intent.intent_id


def test_program_ir_has_objective_evidence_and_exact_duration() -> None:
    _intent, graph, program, _semantic = _kernel()

    assert sum(phase.time_budget.minutes for phase in program.phases) == program.total_duration_minutes
    assert {objective_id for phase in program.phases for move in phase.moves for objective_id in move.objective_ids} == {
        item.objective_id for item in graph.objectives
    }
    assert all(move.evidence_opportunities for phase in program.phases for move in phase.moves)


def test_semantic_ir_structurally_separates_answers() -> None:
    _intent, _graph, _program, semantic = _kernel()

    answers = [entity for entity in semantic.entities if entity.kind == "answer_derivation"]
    assert answers
    assert all(entity.audience == "teacher" and entity.reuse_policy == "teacher_only" for entity in answers)
    assert all(entity.kind != "answer_derivation" for entity in semantic.entities if entity.audience == "student")


def test_optimizer_never_selects_hard_constraint_failure() -> None:
    _intent, _graph, program, _semantic = _kernel()
    good = candidate_from_program(program)
    bad = CandidateProgram(
        candidate_id="candidate-bad",
        program=program,
        constraint_results=(ConstraintResult(constraint_id="hard:duration", passed=False, evidence="too long"),),
        metrics=good.metrics,
        generation_cost_units=0,
    )
    decision = optimize_programs((bad, good), OptimizationPolicy(
        policy_version="optimizer.v1",
        metric_weights={"coverage": 1.0},
    ))

    assert decision.selected_candidate_id == good.candidate_id
    assert decision.selected_candidate_id != bad.candidate_id


def test_domain_tool_receipts_are_deterministic_and_tenant_scoped() -> None:
    runtime = default_tool_runtime()
    request = ToolRequest(
        request_id="request-1",
        tool_id="arithmetic",
        input={"expression": "2 + 3 * 4"},
        tenant_scope="org-a",
        policy=ToolPolicy(policy_version="tools.v1"),
    )
    first = runtime.execute(request)
    second = runtime.execute(request)

    assert first == second
    assert first[0].status == "verified"
    assert first[0].output == {"expression": "2 + 3 * 4", "value": 14}
    assert first[1].tenant_scope == "org-a"


def test_domain_tool_rejects_arbitrary_python_execution() -> None:
    runtime = default_tool_runtime()
    result, receipt = runtime.execute(ToolRequest(
        request_id="request-2",
        tool_id="arithmetic",
        input={"expression": "__import__('os').environ"},
        tenant_scope="org-a",
        policy=ToolPolicy(policy_version="tools.v1"),
    ))

    assert result.status == "invalid_input"
    assert receipt.reusable is False


def test_synthesis_scoped_repair_preserves_unrelated_entity_hashes() -> None:
    _intent, _graph, program, semantic = _kernel()
    result = synthesize_semantic_content(program, semantic)
    target = semantic.entities[0]
    before = {entity.semantic_id: entity.model_dump_json() for entity in semantic.entities if entity.semantic_id != target.semantic_id}
    replacement = target.model_copy(update={"text": target.text + " Clarified."})

    repaired = scoped_repair(result, semantic_id=target.semantic_id, replacement=replacement, failure_codes=("clarity",))
    after = {entity.semantic_id: entity.model_dump_json() for entity in repaired.selected_semantic_ir.entities if entity.semantic_id != target.semantic_id}

    assert before == after
    assert repaired.selected_semantic_ir.version == semantic.version + 1


def test_artifact_compiler_accounts_for_every_semantic_entity() -> None:
    _intent, _graph, program, semantic = _kernel()
    artifact = {
        "artifact_type": "lesson",
        "title": "Equivalent Fractions",
        "theme": "default",
        "sections": [{"id": "intro", "title": "Introduction", "content": "Equivalent fractions can name the same value."}],
        "metadata": {},
        "accessibility": {"language": "en"},
    }
    result = compile_existing_artifact(artifact, program=program, semantic_ir=semantic)

    assert len(result.projections) == len(semantic.entities)
    assert all(item.disposition not in {"unsupported", "failed"} for item in result.projections)
    assert result.artifact["metadata"]["pedagogical_compiler"]["program_id"] == program.program_id

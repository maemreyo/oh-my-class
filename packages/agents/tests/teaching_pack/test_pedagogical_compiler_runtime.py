from __future__ import annotations

from types import SimpleNamespace

from common.contracts.content_brief import ContentBrief
from common.contracts.content_factory.tenancy import personal_tenant_context
from packages.agents.teaching_pack.pedagogical_compiler_runtime import (
    compile_artifact_with_context,
    compile_intelligence_context,
)


def _request():
    return SimpleNamespace(
        run_id="run-1",
        artifact_type="lesson",
        lesson_plan={
            "topic": "Equivalent Fractions",
            "grade_level": "Grade 5",
            "subject": "math",
            "locale": "en",
            "duration_minutes": 45,
        },
        research_brief={
            "sources": [{"source_id": "source-1", "title": "Fractions guide", "excerpt": "Equivalent fractions name the same value."}],
        },
        content_brief=ContentBrief(
            content_brief_id="brief-1",
            run_id="run-1",
            artifact_type="lesson",
            objectives=["Identify equivalent fractions.", "Generate an equivalent fraction."],
            methodology="direct_instruction",
            methodology_source="teacher_pin",
            source_citation_ids=["source-1"],
            knowledge_db_version="knowledge-v1",
        ),
        tenant=personal_tenant_context(teacher_id="teacher-1", principal_id="teacher-1"),
    )


def test_runtime_compiles_one_shared_intelligence_context() -> None:
    context = compile_intelligence_context(_request())

    assert context.intent.is_ready
    assert context.objective_graph.knowledge_snapshot_version == "knowledge-v1"
    assert context.program.objective_graph_id == context.objective_graph.graph_id
    assert context.semantic_ir.program_id == context.program.program_id
    assert context.optimization.selected_candidate_id is not None


def test_runtime_stamps_compiler_lineage_on_artifact() -> None:
    context = compile_intelligence_context(_request())
    compiled = compile_artifact_with_context({
        "artifact_type": "lesson",
        "title": "Equivalent Fractions",
        "theme": "default",
        "sections": [{"id": "intro", "title": "Introduction", "content": "Equivalent fractions can name the same value."}],
        "metadata": {},
        "accessibility": {"language": "en"},
    }, context)

    metadata = compiled["metadata"]
    assert metadata["teaching_intent_hash"] == context.intent.intent_hash
    assert metadata["objective_graph_hash"] == context.objective_graph.graph_hash
    assert metadata["pedagogical_compiler"]["semantic_ir_id"] == context.semantic_ir.semantic_ir_id
    assert len(metadata["pedagogical_compiler"]["entity_projection_map"]) == len(context.semantic_ir.entities)

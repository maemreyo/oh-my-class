from __future__ import annotations

from common.contracts.content_factory.orchestration import build_content_brief
from packages.agents.teaching_pack.specialist_depth import deepen_specialist_output


def _lesson_plan() -> dict[str, object]:
    return {
        "topic": "Equivalent fractions",
        "subject": "Math",
        "grade_level": "Grade 5",
        "duration_minutes": 45,
        "methodology": "concrete-representational-abstract",
        "learning_objectives": [
            {"objective_id": "obj-identify", "description": "Identify equivalent fractions."},
            {"objective_id": "obj-generate", "description": "Generate an equivalent fraction."},
        ],
        "learning_plan": {
            "launch": "Compare fraction strips.",
            "model": "Model an equivalence.",
            "practice": "Generate and justify an equivalence.",
            "closure": "Explain the invariant.",
        },
        "prerequisite_edges": [{"source": "obj-identify", "target": "obj-generate"}],
    }


def _research() -> dict[str, object]:
    return {
        "content_intelligence": {"snapshot_version": "graph-v1"},
        "sources": [
            {
                "source_id": "source-a",
                "claim_id": "claim-equivalence",
                "excerpt": "Equivalent fractions name the same value.",
                "verification_status": "verified",
            },
            {
                "source_id": "source-b",
                "claim_id": "claim-equivalence",
                "excerpt": "Equivalent fractions name the same value.",
                "verification_status": "verified",
            },
        ],
    }


def _brief(artifact_type: str):
    return build_content_brief(
        run_id="run-1",
        artifact_type=artifact_type,
        lesson_plan=_lesson_plan(),
        research_brief=_research(),
    )


def test_lesson_family_adds_observable_phase_contract_and_lineage() -> None:
    artifact = deepen_specialist_output({
        "artifact_type": "lesson",
        "theme": "default",
        "title": "Lesson",
        "sections": [
            {"id": "objective-1", "title": "Objective", "content": "Identify equivalent fractions."},
            {"id": "phase-1", "title": "Launch", "content": "Compare fraction strips."},
        ],
        "metadata": {},
    }, family="lesson_design", content_brief=_brief("lesson"), lesson_plan=_lesson_plan(), research_brief=_research())

    plan = artifact["metadata"]["instructional_design_plan"]
    assert plan["allocated_minutes"] + plan["transition_reserve_minutes"] + plan["contingency_minutes"] <= 45
    assert artifact["metadata"]["approved_objective_ids"] == ["obj-identify", "obj-generate"]
    phase = next(section for section in artifact["sections"] if section["id"] == "phase-1")
    assert phase["teacher_actions"]
    assert phase["student_actions"]
    assert phase["checks_for_understanding"]
    assert phase["anticipated_responses"]
    assert phase["misconception_responses"]
    assert phase["differentiation"]
    assert phase["transition"]
    assert phase["closure"]


def test_assessment_family_attaches_item_blueprint_and_solver_trace() -> None:
    artifact = deepen_specialist_output({
        "artifact_type": "quiz",
        "theme": "default",
        "title": "Quiz",
        "sections": [{"id": "questions", "components": [{
            "type": "question_card",
            "id": "q1",
            "text": "Which pair is equivalent?",
            "options": {"A": "1/2 and 2/4", "B": "1/2 and 2/3", "C": "1/2 and 3/4", "D": "1/2 and 1/4"},
            "answer": "A",
            "explain": "Solved deterministically from equal-value fractions.",
        }]}],
        "metadata": {},
    }, family="assessment", content_brief=_brief("quiz"), lesson_plan=_lesson_plan(), research_brief=_research())

    card = artifact["sections"][0]["components"][0]
    assert card["objective_id"] == "obj-identify"
    assert card["verification_method"] == "solver"
    assert card["verification"]["method"] == "deterministic_solver"
    assert artifact["metadata"]["item_blueprints"][0]["misconception_target_id"]


def test_practice_family_builds_full_progression_instead_of_three_generic_prompts() -> None:
    artifact = deepen_specialist_output({
        "artifact_type": "worksheet",
        "theme": "default",
        "title": "Worksheet",
        "sections": [{"id": "practice", "components": []}],
        "metadata": {},
    }, family="practice", content_brief=_brief("worksheet"), lesson_plan=_lesson_plan(), research_brief=_research())

    assert artifact["metadata"]["practice_progression"] == [
        "worked_example", "guided", "independent", "retrieval", "interleaved", "transfer",
    ]
    assert len(artifact["sections"][0]["components"]) == 6
    assert all(item["verification_method"] == "rubric" for item in artifact["sections"][0]["components"])


def test_synthesis_family_triangulates_claims_and_orders_roadmap_by_prerequisite() -> None:
    artifact = deepen_specialist_output({
        "artifact_type": "roadmap",
        "theme": "default",
        "title": "Roadmap",
        "sections": [
            {"id": "milestone-1", "objective_id": "obj-generate", "title": "Generate"},
            {"id": "milestone-2", "objective_id": "obj-identify", "title": "Identify"},
        ],
        "metadata": {},
    }, family="synthesis", content_brief=_brief("roadmap"), lesson_plan=_lesson_plan(), research_brief=_research())

    assert artifact["metadata"]["prerequisite_order"] == ["obj-identify", "obj-generate"]
    assert [section["objective_id"] for section in artifact["sections"]] == ["obj-identify", "obj-generate"]
    claim = next(
        item for item in artifact["metadata"]["synthesis_plan"]["retained_claims"]
        if item["claim_id"] == "claim-equivalence"
    )
    assert claim["evidence_ids"] == ["source-a", "source-b"]
    assert claim["authority"] == "verified"

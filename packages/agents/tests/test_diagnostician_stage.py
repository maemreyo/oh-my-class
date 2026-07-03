from __future__ import annotations

import pytest

from packages.agents.teaching_pack.nodes import TeachingPackState, _planning_blueprint


@pytest.mark.anyio
async def test_diagnostic_runs_before_planning_when_student_evidence_present() -> None:
    result = await _planning_blueprint(TeachingPackState(
        run_id="run-diagnose",
        contract={
            "mode": "diagnose_then_generate",
            "topic": "Fractions",
            "raw_request": "Teach equivalent fractions",
            "grade_band": "Grade 5",
            "subject": "math",
            "instruction_language": "en",
            "student_count": 1,
            "student_evidence": _student_evidence(),
        },
    ))

    assert result["diagnostic_report"]["student_id"] == "student-1"
    assert result["kt_mastery"]["Fraction equivalence"]["confidence"] == "high"
    assert "mastery=reteach" in result["lesson_plan"]["methodology"]["student_profile_notes"]


@pytest.mark.anyio
async def test_diagnostic_skips_without_student_evidence() -> None:
    result = await _planning_blueprint(TeachingPackState(
        run_id="run-no-diagnose",
        contract={
            "mode": "diagnose_then_generate",
            "topic": "Fractions",
            "raw_request": "Teach equivalent fractions",
            "grade_band": "Grade 5",
            "subject": "math",
            "instruction_language": "en",
            "student_count": 1,
        },
    ))

    assert "diagnostic_report" not in result
    assert "kt_mastery" not in result


def test_diagnostician_and_kt_share_knowledge_state_store() -> None:
    from packages.agents.sub_agents.diagnostician.knowledge_state import KnowledgeStateStore

    store = KnowledgeStateStore()
    report = store.record_diagnostic("student-1", _diagnostic_report())
    store.record_kt_update("student-1", "Fraction equivalence", mastery=0.8, confidence="high")

    unified = store.planner_mastery("student-1")

    assert report["knowledge_gaps"][0]["confidence"] == 0.8
    assert unified["Fraction equivalence"]["mastery"] == 0.8


@pytest.mark.anyio
async def test_diagnostician_repairs_malformed_dimension_without_crashing() -> None:
    from packages.agents.sub_agents.diagnostician.nodes import diagnostician_node
    from packages.agents.teaching_pack.stages import StageEnum

    result = await diagnostician_node({
        "student_responses": {**_student_evidence(), "force_malformed_dimension": True},
        "run_id": "run-diagnostic-repair",
        "current_step": StageEnum.PLANNING_BLUEPRINT,
        "diagnostic_report": None,
        "use_structured_diagnostic": True,
    })

    assert result["diagnostic_report"]["misconception_patterns"][0]["systematicity"] == "systematic"


def _student_evidence() -> dict[str, object]:
    return {
        "student_id": "student-1",
        "answers": [
            {"question_id": "q1", "section": "Fraction equivalence", "bloom_level": "understand", "correct": False, "error": "denominator focus"},
            {"question_id": "q2", "section": "Fraction equivalence", "bloom_level": "apply", "correct": False, "error": "denominator focus"},
            {"question_id": "q3", "section": "Fraction comparison", "bloom_level": "remember", "correct": True},
        ],
        "wrong_question_ids": ["q1", "q2"],
    }


def _diagnostic_report() -> dict[str, object]:
    return {
        "student_id": "student-1",
        "knowledge_gaps": [
            {"category": "Fraction equivalence", "error_count": 2, "error_rate": 0.8, "severity": "critical", "question_ids": ["q1", "q2"], "confidence": 0.8},
        ],
    }

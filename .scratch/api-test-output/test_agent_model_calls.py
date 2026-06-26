#!/usr/bin/env python3
"""Direct LLM model-call test for each agent via 4omc model.

Calls each agent's node function with minimal valid state, validates output
against Pydantic schema. No full pipeline, no gateway, no LangGraph.
"""

from __future__ import annotations

import asyncio
import json
import time
import traceback

# Set env before imports
import os
os.environ.setdefault("LLM_BASE_URL", "http://localhost:20128/v1")
os.environ.setdefault("LLM_TIMEOUT", "120")


async def test_planner():
    """Planner agent: raw_request + class_info → LessonPlan JSON"""
    from packages.agents.sub_agents.planner.nodes import planner_node

    state = {
        "raw_request": "Dạy phân số cho lớp 5, tập trung vào phép cộng phân số khác mẫu số",
        "class_info": {
            "grade": "5",
            "subject": "math",
            "student_count": 30,
            "language": "vi",
        },
        "run_id": "test-planner-001",
        "current_step": 3,
        "lesson_plan": None,
    }

    started = time.monotonic()
    result = await planner_node(state)
    duration = time.monotonic() - started

    assert "lesson_plan" in result, "Missing lesson_plan in result"
    plan = result["lesson_plan"]
    assert "topic" in plan, "Missing topic"
    assert "learning_objectives" in plan, "Missing learning_objectives"
    assert len(plan["learning_objectives"]) >= 1, "Need ≥1 objective"
    # Check Bloom levels
    bloom_levels = {lo.get("bloom_level") for lo in plan["learning_objectives"]}
    assert len(bloom_levels) >= 2, f"Need ≥2 Bloom levels, got: {bloom_levels}"

    # Validate with Pydantic
    from common.contracts.lesson_plan import LessonPlan
    LessonPlan.model_validate(plan)

    return {
        "agent": "planner",
        "model": os.environ.get("MODEL_PLANNER", "4omc"),
        "duration_s": round(duration, 1),
        "bloom_levels": sorted(bloom_levels),
        "topic": plan.get("topic", ""),
        "objectives_count": len(plan.get("learning_objectives", [])),
        "schema_valid": True,
    }


async def test_researcher():
    """Researcher agent: lesson_plan → ResearchBundle JSON.
    
    Note: This also calls web_search + web_fetch internally.
    """
    from packages.agents.sub_agents.researcher.nodes import researcher_node

    # Minimal valid lesson_plan for researcher input
    lesson_plan = {
        "topic": "Phân số - phép cộng phân số khác mẫu số",
        "grade_level": "Grade 5",
        "subject": "math",
        "duration_minutes": 45,
        "learning_objectives": [
            {"description": "Hiểu cách cộng phân số khác mẫu số", "bloom_level": "understand"},
            {"description": "Thực hiện phép cộng phân số khác mẫu số", "bloom_level": "apply"},
        ],
    }

    state = {
        "lesson_plan": lesson_plan,
        "research_policy": "basic",
        "run_id": "test-researcher-001",
        "current_step": 7,
        "research_bundle": None,
    }

    started = time.monotonic()
    result = await researcher_node(state)
    duration = time.monotonic() - started

    assert "research_bundle" in result, "Missing research_bundle in result"
    bundle = result["research_bundle"]
    assert "topic" in bundle, "Missing topic"
    assert "sources" in bundle, "Missing sources"
    assert len(bundle["sources"]) >= 2, f"Need ≥2 sources, got {len(bundle['sources'])}"

    # Validate with Pydantic
    from common.contracts.research_bundle import ResearchBundle
    ResearchBundle.model_validate(bundle)

    return {
        "agent": "researcher",
        "model": os.environ.get("MODEL_RESEARCHER", "4omc"),
        "duration_s": round(duration, 1),
        "sources_count": len(bundle.get("sources", [])),
        "topic": bundle.get("topic", ""),
        "schema_valid": True,
    }


async def test_content_creator():
    """Content Creator agent: lesson_plan + research_bundle → ArtifactContent JSON"""
    from packages.agents.sub_agents.content_creator.nodes import content_creator_node

    # Realistic lesson_plan
    lesson_plan = {
        "topic": "Phân số - phép cộng phân số khác mẫu số",
        "grade_level": "Grade 5",
        "subject": "math",
        "duration_minutes": 45,
        "language": "vi",
        "learning_objectives": [
            {"description": "Hiểu cách tìm mẫu số chung", "bloom_level": "understand", "assessment_method": "Quiz"},
            {"description": "Cộng phân số khác mẫu số", "bloom_level": "apply", "assessment_method": "Bài tập thực hành"},
            {"description": "Phân tích tình huống thực tế", "bloom_level": "analyze", "assessment_method": "Bài tập tình huống"},
        ],
        "learning_plan": {
            "gain_attention": {"title": "Khởi động", "duration": 5, "activities": ["Hỏi về pizza"]},
            "present_content": {"title": "Trình bày nội dung", "duration": 15, "activities": ["Giải thích mẫu số chung"]},
        },
        "assessment_checkpoints": [
            {"type": "exit_ticket", "description": "Câu hỏi cuối giờ"}
        ],
        "prerequisite_knowledge": ["Phân số là gì", "Phân số cùng mẫu số"],
    }

    # Realistic research_bundle
    research_bundle = {
        "topic": "Phân số - phép cộng phân số khác mẫu số",
        "sources": [
            {"title": "Cộng phân số - Toán lớp 5", "url": "https://example.com/math5", "credibility_score": 0.9, "verification_status": "VERIFIED"},
            {"title": "Phương pháp dạy phân số", "url": "https://example.com/teach", "credibility_score": 0.8, "verification_status": "VERIFIED"},
        ],
        "key_findings": ["Dạy mẫu số chung trước khi cộng"],
        "research_policy": "basic",
    }

    state = {
        "lesson_plan": lesson_plan,
        "research_bundle": research_bundle,
        "artifact_types": ["lesson"],
        "theme": "default",
        "run_id": "test-content-creator-001",
        "current_step": 8,
        "artifacts": None,
    }

    started = time.monotonic()
    result = await content_creator_node(state)
    duration = time.monotonic() - started

    assert "artifacts" in result, "Missing artifacts in result"
    artifacts = result["artifacts"]
    assert len(artifacts) >= 1, f"Need ≥1 artifact, got {len(artifacts)}"

    # Validate with Pydantic
    from common.contracts.artifact import ArtifactContent
    for art in artifacts:
        ArtifactContent.model_validate(art)

    first = artifacts[0]
    return {
        "agent": "content_creator",
        "model": os.environ.get("MODEL_CONTENT_CREATOR", "4omc"),
        "duration_s": round(duration, 1),
        "artifacts_count": len(artifacts),
        "artifact_type": first.get("artifact_type", ""),
        "sections_count": len(first.get("sections", [])),
        "title": first.get("title", "")[:60],
        "schema_valid": True,
    }


async def test_diagnostician():
    """Diagnostician agent: student_responses → DiagnosticReport JSON"""
    from packages.agents.sub_agents.diagnostician.nodes import diagnostician_node

    state = {
        "student_responses": {
            "student_id": "SV001",
            "answers": [
                {"question_id": 1, "section": "Phân số", "correct": False, "user_answer": "1/3 + 1/2 = 2/5", "correct_answer": "5/6"},
                {"question_id": 2, "section": "Phân số", "correct": True, "user_answer": "1/2 + 1/2 = 1", "correct_answer": "1"},
                {"question_id": 3, "section": "Phân số", "correct": False, "user_answer": "2/3 + 1/4 = 3/7", "correct_answer": "11/12"},
            ],
            "wrong_question_ids": [1, 3],
        },
        "run_id": "test-diag-001",
        "current_step": 5,
        "diagnostic_report": None,
    }

    started = time.monotonic()
    result = await diagnostician_node(state)
    duration = time.monotonic() - started

    assert "diagnostic_report" in result, "Missing diagnostic_report in result"
    report = result["diagnostic_report"]
    assert "student_id" in report, "Missing student_id"

    # Validate with Pydantic
    from common.contracts.diagnostic_report import DiagnosticReport
    DiagnosticReport.model_validate(report)

    return {
        "agent": "diagnostician",
        "model": os.environ.get("MODEL_DIAGNOSTICIAN", "4omc"),
        "duration_s": round(duration, 1),
        "student_id": report.get("student_id", ""),
        "knowledge_gaps_count": len(report.get("knowledge_gaps", [])),
        "bloom_gaps_count": len(report.get("bloom_gaps", [])),
        "schema_valid": True,
    }


async def test_reviewer():
    """Reviewer/Judge agent: artifact HTML content → JudgeOutput JSON
    
    Uses complete_json_chat directly since reviewer_node has complex state.
    """
    from packages.agents.llm import chat_messages, complete_json_chat
    from packages.agents.config.models import MODELS

    system_prompt = """You are a quality judge for educational content.
Evaluate the following artifact and return a JudgeOutput JSON with:
- overall_score (0-10)
- layer_scores: list of {layer, score (0-10), weight (0-1), issues}
- critical_issues: list of strings
- passed: bool (true if overall_score >= 7.0 and no critical issues)
- rationale: string explaining your scores

Return ONLY the JSON object. No prose."""

    user_prompt = """Evaluate this educational artifact:

Title: Bài học về phân số - Phép cộng phân số khác mẫu số
Grade: 5
Type: lesson
Language: Vietnamese

Content:
- Section 1: Learning objectives (understand, apply, analyze Bloom levels)
- Section 2: Warm-up activity with pizza example
- Section 3: Main content - finding common denominators
- Section 4: Practice exercises
- Section 5: Assessment

Quality criteria:
1. Format: has proper structure, no external assets
2. Content: accurate math, age-appropriate, complete
3. Presentation: clear, engaging, accessible

Return JudgeOutput JSON."""

    messages = chat_messages(system_prompt, user_prompt)

    started = time.monotonic()
    content = await complete_json_chat(
        model=MODELS.reviewer,
        messages=messages,
        temperature=0.3,
        tags=["agent:reviewer", "step:10", "run:test-reviewer-001", "pipeline:oh-my-class"],
    )
    duration = time.monotonic() - started

    # Parse JSON
    from packages.agents.llm import extract_json_text
    json_str = extract_json_text(content)
    judge_data = json.loads(json_str)

    # Validate with Pydantic
    from common.contracts.judge_output import JudgeOutput
    JudgeOutput.model_validate(judge_data)

    return {
        "agent": "reviewer (judge)",
        "model": MODELS.reviewer,
        "duration_s": round(duration, 1),
        "overall_score": judge_data.get("overall_score", 0),
        "passed": judge_data.get("passed", False),
        "critical_issues_count": len(judge_data.get("critical_issues", [])),
        "schema_valid": True,
    }


async def test_planner_direct():
    """Planner via direct complete_json_chat (no node wrapper)"""
    from packages.agents.llm import chat_messages, complete_json_chat, extract_json_text
    from packages.agents.config.models import MODELS
    from packages.agents.sub_agents.planner.prompts import load_system_prompt

    system = load_system_prompt() + "\n\nCRITICAL: Respond ONLY with a single JSON object. No prose."
    user = """Teacher request: Dạy phân số lớp 5 - cộng phân số khác mẫu số
Class: Grade 5, math, 30 students, Vietnamese"""

    messages = chat_messages(system, user)
    started = time.monotonic()
    content = await complete_json_chat(
        model=MODELS.planner, messages=messages, temperature=0.7,
        tags=["agent:planner", "step:3", "run:test-direct-001", "pipeline:oh-my-class"],
    )
    duration = time.monotonic() - started
    json_str = extract_json_text(content)
    plan = json.loads(json_str)

    from common.contracts.lesson_plan import LessonPlan
    validated = LessonPlan.model_validate(plan)

    return {
        "agent": "planner (direct)",
        "model": MODELS.planner,
        "duration_s": round(duration, 1),
        "topic": validated.topic,
        "objectives": len(validated.learning_objectives),
        "bloom_levels": sorted({lo.bloom_level for lo in validated.learning_objectives}),
        "schema_valid": True,
    }


AGENT_TESTS = {
    "planner": test_planner,
    "planner_direct": test_planner_direct,
    "researcher": test_researcher,
    "content_creator": test_content_creator,
    "diagnostician": test_diagnostician,
    "reviewer": test_reviewer,
}


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--agents", nargs="*", help="Specific agents to test (default: all)")
    parser.add_argument("--timeout", type=int, default=300, help="Per-agent timeout in seconds")
    args = parser.parse_args()

    agents = args.agents or list(AGENT_TESTS.keys())
    results = []
    errors = []

    print(f"\n{'='*60}")
    print(f"  Direct Agent Model Call Test — 4omc via 9Router")
    print(f"  Base URL: {os.environ.get('LLM_BASE_URL')}")
    print(f"  Timeout: {args.timeout}s per agent")
    print(f"  Agents: {', '.join(agents)}")
    print(f"{'='*60}\n")

    for agent_name in agents:
        if agent_name not in AGENT_TESTS:
            print(f"  ⚠ Unknown agent: {agent_name}")
            continue

        print(f"▶ Testing {agent_name}...", end=" ", flush=True)
        try:
            result = await asyncio.wait_for(
                AGENT_TESTS[agent_name](),
                timeout=args.timeout,
            )
            results.append(result)
            print(f"✅ {result['duration_s']}s — schema valid")
            # Print key details
            for k, v in result.items():
                if k not in ("schema_valid",) and k != "agent":
                    print(f"    {k}: {v}")
        except asyncio.TimeoutError:
            err = f"TIMEOUT after {args.timeout}s"
            errors.append({"agent": agent_name, "error": err})
            print(f"❌ {err}")
        except Exception as e:
            tb = traceback.format_exc()
            errors.append({"agent": agent_name, "error": str(e), "traceback": tb})
            print(f"❌ {e}")
        print()

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  Passed: {len(results)}/{len(agents)}")
    print(f"  Failed: {len(errors)}/{len(agents)}")
    if results:
        total_time = sum(r["duration_s"] for r in results)
        print(f"  Total time: {total_time:.1f}s")
    if errors:
        print(f"\n  FAILURES:")
        for e in errors:
            print(f"    - {e['agent']}: {e['error']}")
    print()

    # Write results to JSON
    output_path = os.path.join(os.path.dirname(__file__), "agent_model_call_results.json")
    with open(output_path, "w") as f:
        json.dump({"results": results, "errors": errors}, f, indent=2, ensure_ascii=False)
    print(f"  Results saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())

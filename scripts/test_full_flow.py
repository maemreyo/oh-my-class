"""Full flow E2E smoke test using TestClient (no external server needed).

Patches complete_json_chat at import time to return mock responses,
then drives the full pipeline via FastAPI TestClient.

Usage:
    uv run python scripts/test_full_flow.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

_PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

os.environ.setdefault("JWT_SECRET", "test-secret-for-e2e-smoke-32bytes!!")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class")

# ── Mock responses keyed by prompt substring ──────────────────────────────────

MOCK_DIAGNOSTIC = json.dumps({"skip_remaining": False, "reason": "normal flow"})

MOCK_PLAN = json.dumps({
    "topic": "Phân số bằng nhau",
    "grade_level": "Grade 5",
    "subject": "math",
    "duration_minutes": 45,
    "learning_objectives": [
        {"description": "Understand equivalent fractions", "bloom_level": "understand"},
        {"description": "Apply fraction comparison", "bloom_level": "apply"},
    ],
    "prerequisite_knowledge": ["basic fractions", "numerator and denominator"],
    "learning_plan": {
        "phases": [
            {"phase": "gain_attention", "activity": "Fraction pizza puzzle"},
            {"phase": "inform_objectives", "activity": "State learning goals"},
            {"phase": "stimulate_recall", "activity": "Review basic fractions"},
            {"phase": "present_content", "activity": "Equivalent fractions demo"},
            {"phase": "provide_guidance", "activity": "Guided practice"},
            {"phase": "elicit_performance", "activity": "Independent practice"},
            {"phase": "provide_feedback", "activity": "Peer review"},
            {"phase": "assess_performance", "activity": "Quiz"},
            {"phase": "enhance_retention", "activity": "Real-world application"},
        ]
    },
    "assessment_checkpoints": [
        {"type": "formative", "description": "Check understanding during activities", "method": "observation"},
        {"type": "summative", "description": "Final quiz on equivalent fractions", "method": "quiz"},
    ],
})

MOCK_ROADMAP = json.dumps({
    "artifact_sequence": [
        {"artifact_type": "lesson", "priority": 1},
        {"artifact_type": "worksheet", "priority": 2},
        {"artifact_type": "quiz", "priority": 3},
    ],
    "research_focus": "equivalent fractions for Grade 5",
    "estimated_complexity": "medium",
})

MOCK_RESEARCH = json.dumps({
    "topic": "Phân số bằng nhau",
    "sources": [
        {"title": "Equivalent Fractions", "url": "https://example.com/ef", "credibility_score": 0.9, "verification_status": "VERIFIED"},
        {"title": "Teaching Fractions", "url": "https://example.com/tf", "credibility_score": 0.85, "verification_status": "VERIFIED"},
    ],
    "key_findings": [
        "Equivalent fractions have the same value but different numerators and denominators",
        "Multiply or divide numerator and denominator by the same number",
    ],
    "cross_references": [],
    "research_policy": "standard",
})

MOCK_CONTENT = json.dumps([
    {
        "artifact_type": "lesson",
        "theme": "default",
        "title": "Phân số bằng nhau - Grade 5",
        "sections": [
            {"title": "Mục tiêu học tập", "content": "Học sinh sẽ hiểu và áp dụng phân số bằng nhau."},
            {"title": "Hoạt động khởi động", "content": "Cho học sinh xem pizza cắt thành nhiều phần."},
            {"title": "Nội dung chính", "content": "Phân số bằng nhau là các phân số có giá trị như nhau. Ví dụ: 1/2 = 2/4 = 3/6."},
            {"title": "Bài tập", "content": "Tìm phân số bằng nhau: 2/3 = ?/6 = 4/?", "teacher_only": False},
            {"title": "Đáp án cho giáo viên", "content": "2/3 = 4/6 = 6/9", "teacher_only": True},
        ],
        "metadata": {"grade": 5, "subject": "math", "language": "vi"},
        "accessibility": {"language": "vi", "reading_level": "grade_5"},
    },
    {
        "artifact_type": "worksheet",
        "theme": "default",
        "title": "Worksheet - Phân số bằng nhau",
        "sections": [
            {"title": "Bài 1", "content": "Liệt kê 3 phân số bằng nhau với 1/2."},
            {"title": "Bài 2", "content": "So sánh: 2/5 và 4/10"},
        ],
        "metadata": {"grade": 5, "subject": "math", "language": "vi"},
        "accessibility": {"language": "vi", "reading_level": "grade_5"},
    },
    {
        "artifact_type": "quiz",
        "theme": "default",
        "title": "Quiz - Phân số bằng nhau",
        "sections": [
            {"title": "Câu 1", "content": "Phân số nào bằng 1/3?",
             "options": ["2/6", "2/5", "3/4", "1/4"], "correct_answer": "2/6", "teacher_only": False},
        ],
        "metadata": {"grade": 5, "subject": "math", "language": "vi"},
        "accessibility": {"language": "vi", "reading_level": "grade_5"},
    },
])

MOCK_JUDGE = json.dumps({
    "overall_score": 8.5,
    "format_compliance": 9.0,
    "content_quality": 8.0,
    "presentation": 8.5,
    "critical_issues": [],
    "rationale": "Good content with clear structure and appropriate difficulty.",
})

RESPONSE_MAP = [
    ("diagnostic", MOCK_DIAGNOSTIC),
    ("artifact_sequence", MOCK_ROADMAP),
    ("roadmap", MOCK_ROADMAP),
    ("ResearchBundle", MOCK_RESEARCH),
    ("research", MOCK_RESEARCH),
    ("source", MOCK_RESEARCH),
    ("content generation", MOCK_CONTENT),
    ("Generate structured", MOCK_CONTENT),
    ("ArtifactContent", MOCK_CONTENT),
    ("LLM-as-Judge", MOCK_JUDGE),
    ("G-Eval", MOCK_JUDGE),
    ("judge", MOCK_JUDGE),
    ("overall_score", MOCK_JUDGE),
]


def pick_response(messages: list[dict]) -> str:
    combined = " ".join(str(m.get("content", "")) for m in messages)
    for keyword, resp in RESPONSE_MAP:
        if keyword.lower() in combined.lower():
            return resp
    return MOCK_PLAN


_call_count = 0


async def mock_complete_json_chat(
    model: str,
    messages: list[dict],
    temperature: float,
    tags: list[str],
    max_tokens: int | None = None,
) -> str:
    global _call_count
    _call_count += 1
    agent = "?"
    for t in tags:
        if t.startswith("agent:"):
            agent = t.split(":", 1)[1]
    combined = " ".join(str(m.get("content", "")) for m in messages)
    preview = combined[:120].replace("\n", " ")
    print(f"  🤖 LLM call #{_call_count} agent={agent} prompt=...{preview}...")

    agent_responses = {
        "planner": MOCK_PLAN,
        "diagnostician": MOCK_DIAGNOSTIC,
        "roadmap": MOCK_ROADMAP,
        "researcher": MOCK_RESEARCH,
        "content_creator": MOCK_CONTENT,
        "reviewer": MOCK_JUDGE,
        "healing": MOCK_CONTENT,
    }
    if agent in agent_responses:
        return agent_responses[agent]
    return pick_response(messages)


def drive_flow() -> None:
    global _call_count
    _call_count = 0

    print("=" * 60)
    print("  Teaching Pack — Full Flow E2E Test")
    print("=" * 60)

    from fastapi.testclient import TestClient
    from services.gateway.main import app

    passed = 0
    failed = 0
    skipped = 0

    def record(step: str, ok: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if ok:
            passed += 1
            print(f"  ✅ {step}: PASS {detail}")
        else:
            failed += 1
            print(f"  ❌ {step}: FAIL {detail}")

    def skip(step: str, detail: str = "") -> None:
        nonlocal skipped
        skipped += 1
        print(f"  ⏭️  {step}: SKIP {detail}")

    with (
        patch("packages.agents.llm.chat.complete_json_chat", side_effect=mock_complete_json_chat),
        patch("packages.agents.llm.compiled_chat.complete_json_chat", side_effect=mock_complete_json_chat),
        patch("packages.agents.llm.complete_json_chat", side_effect=mock_complete_json_chat),
        TestClient(app) as client,
    ):
        # ── 1. Health ─────────────────────────────────────────────────────
        print("\n🏥 1. Health check")
        r = client.get("/health")
        record("Health", r.status_code == 200, f"status={r.status_code}")

        # ── 2. Login ──────────────────────────────────────────────────────
        print("\n🔐 2. Login")
        r = client.post("/auth/login", json={"username": "teacher1", "password": "any"})
        record("Login", r.status_code == 200, f"status={r.status_code}")
        if r.status_code != 200:
            print(f"    body: {r.text[:300]}")
            return
        token = r.json().get("access_token", "")
        headers = {"Authorization": f"Bearer {token}"}

        # ── 3. Create run → pipeline to Gate 1 ────────────────────────────
        print("\n📝 3. Create run → pipeline runs to Gate 1")
        t0 = time.monotonic()
        r = client.post(
            "/run",
            json={
                "raw_request": "Dạy phân số bằng nhau cho lớp 5. Thời lượng 45 phút.",
                "class_info": {"grade": 5, "subject": "math", "student_count": 30},
                "teacher_id": "u-001",
            },
            headers=headers,
        )
        elapsed = round(time.monotonic() - t0, 1)

        if r.status_code == 200:
            data = r.json()
            run_id = data.get("run_id", "")
            status = data.get("status", "")
            state = data.get("state", {})
            has_plan = bool(state.get("lesson_plan"))
            record(
                "Create run",
                status == "awaiting_approval",
                f"status={status}, has_plan={has_plan}, elapsed={elapsed}s",
            )
        else:
            record("Create run", False, f"status={r.status_code}")
            print(f"    body: {r.text[:500]}")
            return

        # ── 4. Status check ───────────────────────────────────────────────
        print("\n🔍 4. Status check")
        r = client.get(f"/run/{run_id}", headers=headers)
        print(f"    GET /run/{run_id[:12]}... → {r.status_code} body_len={len(r.content)}")
        if r.status_code == 200 and r.content:
            s = r.json()
            record("Status", s.get("status") == "awaiting_approval",
                   f"status={s.get('status')}")
        else:
            record("Status", r.status_code == 200, f"status={r.status_code}, empty={not r.content}")

        # ── 5. Approve Gate 1 → pipeline to Gate 2 ────────────────────────
        print("\n👍 5. Approve blueprint (Gate 1) → pipeline to Gate 2")
        t0 = time.monotonic()
        r = client.post(
            f"/run/{run_id}/approve",
            json={"action": "approve", "feedback": "Looks good!"},
            headers=headers,
        )
        elapsed = round(time.monotonic() - t0, 1)
        if r.status_code == 200:
            data = r.json()
            record("Approve Gate 1", data.get("status") == "resumed",
                   f"elapsed={elapsed}s")
        else:
            record("Approve Gate 1", False, f"status={r.status_code}")
            print(f"    body: {r.text[:500]}")

        # ── 6. Status after Gate 1 ────────────────────────────────────────
        print("\n🔍 6. Status after Gate 1")
        r = client.get(f"/run/{run_id}", headers=headers)
        at_gate_2 = False
        if r.status_code == 200:
            s = r.json()
            status = s.get("status", "")
            state = s.get("state", {})
            has_artifacts = bool(state.get("artifacts"))
            at_gate_2 = status == "awaiting_approval"
            record("Status after Gate 1", at_gate_2 or status == "completed",
                   f"status={status}, has_artifacts={has_artifacts}")
        else:
            record("Status after Gate 1", False, f"status={r.status_code}")

        # ── 7. Approve Gate 2 → pipeline to export ────────────────────────
        if at_gate_2:
            print("\n👍 7. Approve content (Gate 2) → pipeline to export")
            t0 = time.monotonic()
            r = client.post(
                f"/run/{run_id}/approve",
                json={"action": "approve", "feedback": "Content approved"},
                headers=headers,
            )
            elapsed = round(time.monotonic() - t0, 1)
            if r.status_code == 200:
                data = r.json()
                record("Approve Gate 2", data.get("status") == "resumed",
                       f"elapsed={elapsed}s")
            else:
                record("Approve Gate 2", False, f"status={r.status_code}")
                print(f"    body: {r.text[:500]}")
        else:
            skip("Approve Gate 2", "not at gate 2")

        # ── 8. Final status ───────────────────────────────────────────────
        print("\n🏁 8. Final status")
        r = client.get(f"/run/{run_id}", headers=headers)
        final_status = "?"
        if r.status_code == 200:
            s = r.json()
            final_status = s.get("status", "")
            record("Final status", final_status in ("completed", "awaiting_approval"),
                   f"status={final_status}")
        else:
            record("Final status", False, f"status={r.status_code}")

        # ── 9. Artifacts ──────────────────────────────────────────────────
        print("\n📦 9. Get artifacts")
        r = client.get(f"/run/{run_id}/artifacts", headers=headers)
        if r.status_code == 200:
            artifacts = r.json()
            count = len(artifacts)
            types = [a.get("artifact_type", "?") for a in artifacts]
            record("Artifacts", count > 0, f"count={count}, types={types}")
        else:
            record("Artifacts", False, f"status={r.status_code}")

        # ── 10. Old route 404 ─────────────────────────────────────────────
        print("\n🚫 10. Old /pipeline-v2/run → 404")
        r = client.post("/pipeline-v2/run", json={"raw_request": "test"}, headers=headers)
        record("Old route 404", r.status_code == 404, f"status={r.status_code}")

        # ── Summary ───────────────────────────────────────────────────────
        print(f"\n{'=' * 60}")
        print(f"  LLM calls: {_call_count}")
        print(f"  RESULT: {passed} passed, {failed} failed, {skipped} skipped")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    drive_flow()

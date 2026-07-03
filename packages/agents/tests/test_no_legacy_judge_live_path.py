from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from common.contracts.judge_output import JudgeOutput, LayerScore

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LIVE_PATHS = (
    PROJECT_ROOT / "packages" / "agents",
    PROJECT_ROOT / "packages" / "quality",
    PROJECT_ROOT / "services",
)
LEGACY_JUDGE_IMPORTS = (
    "layer4_judge/geval.py",
    "packages.quality.layer4_judge.geval",
    "GEvalScorer",
    "layer4_judge/pedagogical_scorer.py",
    "packages.quality.layer4_judge.pedagogical_scorer",
    "score_pedagogical",
    "PedagogicalScore",
)


def test_legacy_judges_do_not_enter_live_paths() -> None:
    offenders: list[str] = []
    for root in LIVE_PATHS:
        for path in root.rglob("*.py"):
            if "tests" in path.parts:
                continue
            relative_path = path.relative_to(PROJECT_ROOT).as_posix()
            if any(forbidden in relative_path for forbidden in LEGACY_JUDGE_IMPORTS):
                offenders.append(relative_path)
            text = path.read_text(encoding="utf-8")
            for forbidden in LEGACY_JUDGE_IMPORTS:
                if forbidden in text:
                    offenders.append(f"{path.relative_to(PROJECT_ROOT)} contains {forbidden}")

    assert offenders == []


@pytest.mark.asyncio
async def test_reviewer_node_uses_adaptive_judge(monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.agents.sub_agents.reviewer.nodes import reviewer_node
    from packages.agents import llm

    async def fake_complete_json_chat(
        *,
        model: str,
        messages: list[Any],
        temperature: float,
        tags: list[str],
    ) -> str:
        assert model == "4omc"
        assert messages
        assert temperature == 0.3
        assert any(tag.startswith("rubric:") for tag in tags)
        return JudgeOutput(
            overall_score=8.0,
            layer_scores=[
                LayerScore(layer="format_compliance", score=8.0, weight=0.15),
                LayerScore(layer="content_quality", score=8.0, weight=0.55),
                LayerScore(layer="presentation", score=8.0, weight=0.30),
            ],
            critical_issues=[],
            passed=True,
            rationale="Rationale",
            teacher_facing_summary="Ready for teacher review.",
        ).model_dump_json()

    monkeypatch.setattr(llm, "complete_json_chat", fake_complete_json_chat)

    result = await reviewer_node({
        "artifacts": [{"artifact_type": "quiz", "title": "Fractions"}],
        "lesson_plan": {"topic": "Fractions"},
        "run_id": "reviewer-runtime-test",
    })

    assert result["quality_passed"] is True
    assert result["quality_scores"]["teacher_facing_summary"] == "Ready for teacher review."
    assert result["quality_scores"]["rubric_version"] == "rubric-quiz"

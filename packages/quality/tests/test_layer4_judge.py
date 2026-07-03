from __future__ import annotations

import pytest

from common.contracts.judge_output import JudgeOutput, LayerScore
from packages.quality.layer4_judge.majority_vote import majority_vote

# ── helpers ───────────────────────────────────────────────────────────────────

def make_judge_output(passed: bool = True, score: float = 8.0, critical_issues: list[str] | None = None) -> JudgeOutput:  # noqa: E501
    return JudgeOutput(
        overall_score=score,
        layer_scores=[
            LayerScore(layer="format_compliance", score=score, weight=0.15, issues=[]),
            LayerScore(layer="content_quality", score=score, weight=0.55, issues=[]),
            LayerScore(layer="presentation", score=score, weight=0.30, issues=[]),
        ],
        critical_issues=critical_issues or [],
        passed=passed,
        rationale="Test rationale",
        teacher_facing_summary="Teacher summary",
    )


# ── MajorityVote ──────────────────────────────────────────────────────────────

class TestMajorityVote:
    def test_all_pass(self):
        outputs = [make_judge_output(passed=True) for _ in range(3)]
        result = majority_vote(outputs)
        assert result.passed is True

    def test_two_pass_one_fail(self):
        outputs = [
            make_judge_output(passed=True),
            make_judge_output(passed=True),
            make_judge_output(passed=False),
        ]
        result = majority_vote(outputs)
        assert result.passed is True

    def test_one_pass_two_fail(self):
        outputs = [
            make_judge_output(passed=True),
            make_judge_output(passed=False),
            make_judge_output(passed=False),
        ]
        result = majority_vote(outputs)
        assert result.passed is False

    def test_score_below_threshold(self):
        outputs = [make_judge_output(passed=True, score=6.0) for _ in range(3)]
        result = majority_vote(outputs)
        assert result.passed is False
        assert result.overall_score < 7.0

    def test_score_at_threshold_passes(self):
        outputs = [make_judge_output(passed=True, score=7.0) for _ in range(3)]
        result = majority_vote(outputs)
        assert result.passed is True
        assert result.overall_score == pytest.approx(7.0)

    def test_critical_issues_force_fail(self):
        outputs = [
            make_judge_output(passed=True, critical_issues=["missing_doctype"]),
            make_judge_output(passed=True),
            make_judge_output(passed=True),
        ]
        result = majority_vote(outputs)
        assert result.passed is False
        assert "missing_doctype" in result.critical_issues

    def test_averages_overall_score(self):
        outputs = [
            make_judge_output(score=8.0),
            make_judge_output(score=6.0),
            make_judge_output(score=7.0),
        ]
        result = majority_vote(outputs)
        assert result.overall_score == pytest.approx(7.0)

    def test_deduplicates_critical_issues(self):
        outputs = [
            make_judge_output(critical_issues=["missing_doctype"]),
            make_judge_output(critical_issues=["missing_doctype"]),
            make_judge_output(critical_issues=["missing_doctype"]),
        ]
        result = majority_vote(outputs)
        assert result.critical_issues.count("missing_doctype") == 1

    def test_unions_distinct_critical_issues(self):
        outputs = [
            make_judge_output(critical_issues=["issue_a"]),
            make_judge_output(critical_issues=["issue_b"]),
            make_judge_output(critical_issues=[]),
        ]
        result = majority_vote(outputs)
        assert "issue_a" in result.critical_issues
        assert "issue_b" in result.critical_issues

    def test_raises_on_fewer_than_two(self):
        with pytest.raises(ValueError, match="at least 2"):
            majority_vote([make_judge_output()])

    def test_averages_layer_scores(self):
        j1 = make_judge_output(score=10.0)
        j2 = make_judge_output(score=6.0)
        result = majority_vote([j1, j2])
        for ls in result.layer_scores:
            assert ls.score == pytest.approx(8.0)

    def test_uses_rationale_from_first_judge(self):
        j1 = make_judge_output()
        j1.rationale = "First judge rationale"
        j2 = make_judge_output()
        j2.rationale = "Second judge rationale"
        result = majority_vote([j1, j2])
        assert result.rationale == "First judge rationale"

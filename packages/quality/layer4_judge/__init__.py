"""Layer 4 — LLM-as-Judge (G-Eval).

3-layer scoring framework with majority vote across 3 independent judges.
Generator model ≠ judge model for bias mitigation.

Includes adaptive judge interface (task 6) that selects rubrics by
artifact type, enforces deterministic hard blocks, and tracks provenance.
"""

from packages.quality.layer4_judge.judge_interface import (
    AdaptiveJudge,
    JudgeResult,
    JudgeUnavailableError,
    UnavailableStrategy,
)
from packages.quality.layer4_judge.majority_vote import majority_vote
from packages.quality.layer4_judge.rubric_selector import RubricSelector

__all__ = [
    "AdaptiveJudge",
    "JudgeResult",
    "JudgeUnavailableError",
    "RubricSelector",
    "UnavailableStrategy",
    "majority_vote",
]

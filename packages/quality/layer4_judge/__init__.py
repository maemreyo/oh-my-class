"""Layer 4 — LLM-as-Judge (G-Eval).

3-layer scoring framework with majority vote across 3 independent judges.
Generator model ≠ judge model for bias mitigation.
"""

from packages.quality.layer4_judge.geval import GEvalScorer
from packages.quality.layer4_judge.majority_vote import majority_vote
from packages.quality.layer4_judge.pedagogical_scorer import PedagogicalScore, score_pedagogical

__all__ = ["GEvalScorer", "majority_vote", "PedagogicalScore", "score_pedagogical"]

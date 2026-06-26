"""Layer 2 — Content-Type Rules.

FACT hallucination protocol, age-appropriateness checks,
and 7 binary pedagogical metrics.
"""

from packages.quality.layer2_content.age_band import (
    AGE_BANDS,
    AgeBand,
    build_grade_prompt_section,
    get_age_band,
)
from packages.quality.layer2_content.age_check import check_age_appropriateness
from packages.quality.layer2_content.component_scorer import (
    ComponentScoringResult,
    score_component_usage,
)
from packages.quality.layer2_content.fact_check import FACTChecker
from packages.quality.layer2_content.methodology import (
    MethodologyGateResult,
    MethodologyViolation,
    check_methodology_compliance,
)
from packages.quality.layer2_content.pedagogical import check_pedagogical_metrics
from packages.quality.layer2_content.readability_checker import (
    MAX_DEVIATION,
    ReadabilityResult,
    check_readability,
)

__all__ = [
    "FACTChecker",
    "check_age_appropriateness",
    "check_pedagogical_metrics",
    "AgeBand",
    "AGE_BANDS",
    "get_age_band",
    "build_grade_prompt_section",
    "ReadabilityResult",
    "check_readability",
    "MAX_DEVIATION",
    "MethodologyGateResult",
    "MethodologyViolation",
    "check_methodology_compliance",
    "ComponentScoringResult",
    "score_component_usage",
]

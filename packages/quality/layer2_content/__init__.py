"""Layer 2 — Content-Type Rules.

FACT hallucination protocol, age-appropriateness checks,
and 7 binary pedagogical metrics.
"""

from packages.quality.layer2_content.age_check import check_age_appropriateness
from packages.quality.layer2_content.fact_check import FACTChecker
from packages.quality.layer2_content.pedagogical import check_pedagogical_metrics
from packages.quality.layer2_content.age_band import AgeBand, AGE_BANDS, get_age_band, build_grade_prompt_section
from packages.quality.layer2_content.readability_checker import ReadabilityResult, check_readability, MAX_DEVIATION
from packages.quality.layer2_content.methodology import (
    MethodologyGateResult,
    MethodologyViolation,
    check_methodology_compliance,
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
]

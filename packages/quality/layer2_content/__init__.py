"""Layer 2 — Content-Type Rules.

FACT hallucination protocol, age-appropriateness checks,
and 7 binary pedagogical metrics.
"""

from packages.quality.layer2_content.age_check import check_age_appropriateness
from packages.quality.layer2_content.fact_check import FACTChecker
from packages.quality.layer2_content.pedagogical import check_pedagogical_metrics

__all__ = ["FACTChecker", "check_age_appropriateness", "check_pedagogical_metrics"]

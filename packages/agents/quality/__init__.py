"""Quality modules for educational content validation.

AF4: Age-aware prompt injection (preventive) + Flesch-Kincaid readability (detective).
QG2: 5-dimension pedagogical scoring via f.pro LLM.
"""
from .age_band import AgeBand, AGE_BANDS, get_age_band, build_grade_prompt_section
from .readability_checker import ReadabilityResult, check_readability, MAX_DEVIATION
from .pedagogical_scorer import PedagogicalScore, score_pedagogical

__all__ = [
    "AgeBand",
    "AGE_BANDS",
    "get_age_band",
    "build_grade_prompt_section",
    "ReadabilityResult",
    "check_readability",
    "MAX_DEVIATION",
    "PedagogicalScore",
    "score_pedagogical",
]

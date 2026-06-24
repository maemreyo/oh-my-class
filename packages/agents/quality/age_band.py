"""ACIF age band config for grade-aware prompt injection (AF4)."""
from __future__ import annotations

from dataclasses import dataclass

# Bloom ceiling values aligned with contracts/questions/base.ts BloomLevel
BloomLevel = str   # "remember" | "understand" | "apply" | "analyze" | "evaluate" | "create"


@dataclass(frozen=True)
class AgeBand:
    label:                  str
    grade_range:            tuple[int, int]   # inclusive [min, max]
    max_lexile:             int               # Lexile measure ceiling
    max_words_per_sentence: int               # sentence complexity ceiling
    bloom_ceiling:          BloomLevel        # max Bloom level allowed
    sensitive_topic_tier:   int               # ACIF tier 1-4


# 6 bands per ACIF specification (§4.3 in research report)
AGE_BANDS: list[AgeBand] = [
    AgeBand('Early Childhood', (0, 0),   200,  8,  'understand', 1),
    AgeBand('Lower Primary',   (1, 3),   400,  12, 'understand', 1),
    AgeBand('Upper Primary',   (4, 5),   700,  18, 'apply',      2),
    AgeBand('Lower Secondary', (6, 9),   1000, 22, 'analyze',    2),
    AgeBand('Upper Secondary', (10, 12), 1300, 28, 'evaluate',   3),
    AgeBand('Pre-Tertiary',    (13, 13), 1600, 35, 'create',     4),
]


def get_age_band(grade: int) -> AgeBand:
    """Return the AgeBand for a given grade number (0=preschool, 13=pre-tertiary)."""
    for band in AGE_BANDS:
        if band.grade_range[0] <= grade <= band.grade_range[1]:
            return band
    # Fallback: grades above 13 use Pre-Tertiary band
    return AGE_BANDS[-1]


def build_grade_prompt_section(grade: int) -> str:
    """Build a prompt section for grade-aware content generation.

    Returns a multi-line string suitable for injection into LLM prompts.
    Controls vocabulary, sentence length, Bloom ceiling, and content sensitivity.
    """
    band = get_age_band(grade)
    return (
        f"Grade level: Grade {grade} ({band.label})\n"
        f"Vocabulary: max {band.max_lexile} Lexile (keep words simple and grade-appropriate)\n"
        f"Sentence length: max {band.max_words_per_sentence} words per sentence\n"
        f"Bloom ceiling: up to '{band.bloom_ceiling}' level only\n"
        f"Sensitive topics: Tier {band.sensitive_topic_tier} handling required"
    )

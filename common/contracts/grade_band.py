"""Canonical K-12 Grade Band taxonomy for Subject Capability Packs (ADR-053).

Four bands -- K-2, 3-5, 6-8, 9-12 -- are what every Subject Capability Pack
(#447-450) certifies progression, notation, misconception, and readability
scenarios against.

Two other grade-banding schemes already exist in this codebase, each serving
a different, narrower purpose and each baked into call sites that match on
its specific string values:

- `common.contracts.component_strategy_selector_support.grade_band_for`
  returns `"grade_4_6" | "grade_7_9" | "grade_10_12"` (three bands, no K-3
  coverage) -- a key into the component-strategy knowledge base, not a
  general grade taxonomy.
- `packages.agents.teaching_pack.specialist_registry._grade_band` returns
  `"elementary" | "middle" | "high"` -- used only to tag flashcard-deck
  generation difficulty.

Neither matches ADR-053's four bands, and unifying them would mean touching
strategy-selection and flashcard-generation call sites that are out of scope
for Subject Capability Pack work. This module does not attempt that
unification -- it is the canonical scheme for NEW subject-pack code, not a
replacement for the other two.
"""

from __future__ import annotations

import re
from enum import StrEnum

_KINDERGARTEN_PATTERN = re.compile(r"\bk(indergarten)?\b", re.IGNORECASE)
_GRADE_NUMBER_PATTERN = re.compile(r"\d+")


class GradeBand(StrEnum):
    K_2 = "k_2"
    GRADES_3_5 = "grades_3_5"
    GRADES_6_8 = "grades_6_8"
    GRADES_9_12 = "grades_9_12"


def grade_band_for_grade(grade: int) -> GradeBand:
    """Canonical band for a numeric grade (0 == kindergarten)."""
    if grade <= 2:
        return GradeBand.K_2
    if grade <= 5:
        return GradeBand.GRADES_3_5
    if grade <= 8:
        return GradeBand.GRADES_6_8
    return GradeBand.GRADES_9_12


def grade_band_for_label(grade_level: str) -> GradeBand | None:
    """Canonical band from a free-text grade label (e.g. "Grade 10", "K",
    "Kindergarten"). Returns `None` if no grade can be parsed, rather than
    guessing -- callers decide their own fallback."""
    if _KINDERGARTEN_PATTERN.search(grade_level):
        return GradeBand.K_2
    match = _GRADE_NUMBER_PATTERN.search(grade_level)
    if match is None:
        return None
    return grade_band_for_grade(int(match.group()))

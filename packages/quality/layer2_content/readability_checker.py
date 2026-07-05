"""Flesch-Kincaid grade level readability check (AF4 — detective layer)."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MAX_DEVIATION = 2.0   # allow ±2 grade levels from target


@dataclass
class ReadabilityResult:
    fk_grade_level: float
    target_grade:   int
    deviation:      float       # fk_grade_level - target_grade
    passed:         bool        # |deviation| <= MAX_DEVIATION
    warning:        str | None


def _count_syllables(word: str) -> int:
    """Approximate syllable count via vowel-cluster heuristic."""
    word = word.lower().strip(".,!?;:\"'")
    if not word:
        return 1
    count = len(re.findall(r'[aeiou]+', word))
    # Silent trailing 'e' — subtract if not the only vowel
    if word.endswith('e') and count > 1:
        count -= 1
    return max(1, count)


def _is_non_latin_text(words: list[str]) -> bool:
    """Return True when >15% of word chars are non-ASCII (e.g. Vietnamese, Arabic)."""
    all_chars = "".join(words)
    if not all_chars:
        return False
    return sum(1 for c in all_chars if ord(c) > 127) / len(all_chars) > 0.15


def check_readability(text: str, target_grade: int) -> ReadabilityResult:
    """Check Flesch-Kincaid Grade Level against a target grade.

    Args:
        text:         Input text to analyze (plain text, not HTML)
        target_grade: Expected grade level (1-13)

    Returns:
        ReadabilityResult with fk_grade_level, deviation, passed, and optional warning.
        An empty/short text always passes with fk_grade_level=0.
        Non-Latin text (>15% non-ASCII chars) always passes — FK is English-only.
    """
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    words = [w for w in text.split() if w]

    if not sentences or not words:
        return ReadabilityResult(
            fk_grade_level=0.0,
            target_grade=target_grade,
            deviation=0.0,
            passed=True,
            warning=None,
        )

    if _is_non_latin_text(words):
        return ReadabilityResult(
            fk_grade_level=0.0,
            target_grade=target_grade,
            deviation=0.0,
            passed=True,
            warning=None,
        )

    avg_sentence_length = len(words) / len(sentences)
    avg_syllables       = sum(_count_syllables(w) for w in words) / len(words)

    # Flesch-Kincaid Grade Level formula
    fk_grade  = 0.39 * avg_sentence_length + 11.8 * avg_syllables - 15.59
    deviation = fk_grade - target_grade
    passed    = abs(deviation) <= MAX_DEVIATION

    warning: str | None = None
    if not passed:
        direction = "too complex" if deviation > 0 else "too simple"
        warning = (
            f"Readability {direction} for Grade {target_grade}: "
            f"FK Grade Level {fk_grade:.1f} (deviation: {deviation:+.1f})"
        )
        logger.warning(
            "Readability check failed",
            extra={
                "fk_grade_level": round(fk_grade, 2),
                "target_grade":   target_grade,
                "deviation":      round(deviation, 2),
            },
        )

    return ReadabilityResult(
        fk_grade_level=round(fk_grade, 2),
        target_grade=target_grade,
        deviation=round(deviation, 2),
        passed=passed,
        warning=warning,
    )

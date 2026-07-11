"""Shared fixed-answer question shape for non-arithmetic Subject Capability
Packs (#449 Language and Literacy, #450 Humanities and Social Studies).

Mirrors solver_question_builder.py's question shape and question_card
projection, but for content whose correctness isn't solver-verifiable
arithmetic: every question carries a declared, bilingually-authored correct
answer and a declared misconception distractor (never computed), plus two
additional plausible-but-wrong options. Subject-specific modules supply the
grade-band prompt/option generators; this module supplies the common
question shape and question_card projection.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from common.contracts.grade_band import GradeBand


@dataclass(frozen=True, slots=True)
class FixedAnswerQuestion:
    id: str
    grade_band: GradeBand
    standard_code: str
    misconception_id: str
    prompt_en: str
    prompt_vi: str
    correct_en: str
    correct_vi: str
    misconception_en: str
    misconception_vi: str
    distractor_a_en: str
    distractor_a_vi: str
    distractor_b_en: str
    distractor_b_vi: str
    explain_en: str
    explain_vi: str


def build_fixed_answer_question(
    *,
    id_prefix: str,
    index: int,
    grade_band: GradeBand,
    standard_code: str,
    misconception_id: str,
    prompt_en: str,
    prompt_vi: str,
    correct_en: str,
    correct_vi: str,
    misconception_en: str,
    misconception_vi: str,
    distractor_a_en: str,
    distractor_a_vi: str,
    distractor_b_en: str,
    distractor_b_vi: str,
    explain_en: str,
    explain_vi: str,
) -> FixedAnswerQuestion:
    return FixedAnswerQuestion(
        id=f"{id_prefix}-{grade_band.value}-{index + 1}",
        grade_band=grade_band,
        standard_code=standard_code,
        misconception_id=misconception_id,
        prompt_en=prompt_en,
        prompt_vi=prompt_vi,
        correct_en=correct_en,
        correct_vi=correct_vi,
        misconception_en=misconception_en,
        misconception_vi=misconception_vi,
        distractor_a_en=distractor_a_en,
        distractor_a_vi=distractor_a_vi,
        distractor_b_en=distractor_b_en,
        distractor_b_vi=distractor_b_vi,
        explain_en=explain_en,
        explain_vi=explain_vi,
    )


def to_question_card(question: FixedAnswerQuestion, *, locale: str = "vi") -> dict[str, object]:
    """Projects a FixedAnswerQuestion into the same question_card shape
    `solver_question_builder.to_question_card` emits, so quiz_specialist/
    drill_specialist can treat every subject uniformly."""
    is_vi = locale == "vi"
    prompt = question.prompt_vi if is_vi else question.prompt_en
    explain = question.explain_vi if is_vi else question.explain_en
    ordered_texts = [
        question.correct_vi if is_vi else question.correct_en,
        question.misconception_vi if is_vi else question.misconception_en,
        question.distractor_a_vi if is_vi else question.distractor_a_en,
        question.distractor_b_vi if is_vi else question.distractor_b_en,
    ]
    letters = ["A", "B", "C", "D"]
    # Shuffle deterministically (seeded from the question id) so the correct
    # answer isn't always slot 0 -- a real quiz can't let students exploit
    # "the answer is always A".
    order = list(range(4))
    random.Random(question.id).shuffle(order)
    options = {letter: ordered_texts[position] for letter, position in zip(letters, order, strict=True)}
    answer_letter = letters[order.index(0)]
    return {
        "type": "question_card",
        "id": question.id,
        "text": prompt,
        "options": options,
        "answer": answer_letter,
        "explain": explain,
        "grade_band": question.grade_band.value,
        "standard_code": question.standard_code,
        "misconception_id": question.misconception_id,
    }

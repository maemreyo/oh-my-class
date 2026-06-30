from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MoetOutcomeRow:
    student_pseudonym: str
    score_0_10: float
    assessment_period: str
    comment: str
    matrix_code: str


def export_so_theo_doi(rows: list[MoetOutcomeRow]) -> str:
    header = "student_pseudonym,score_0_10,assessment_period,comment,matrix_code"
    body = [
        f"{row.student_pseudonym},{row.score_0_10:.1f},{row.assessment_period},{row.comment},{row.matrix_code}"
        for row in rows
    ]
    return "\n".join([header, *body])

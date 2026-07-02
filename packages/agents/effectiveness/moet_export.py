from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from common.contracts.outcome import StudentAttempt

_PERIOD_COLUMNS: Final = {
    "ĐĐGtx": "DDGtx",
    "gk": "gk",
    "ck": "ck",
}


@dataclass(frozen=True, slots=True)
class MoetOutcomeRow:
    student_pseudonym: str
    score_0_10: float
    assessment_period: str
    comment: str
    matrix_code: str


def export_so_theo_doi(rows: list[MoetOutcomeRow]) -> str:
    header = "student_pseudonym,DDGtx,gk,ck,nhan_xet,ma_tran"
    body = [_format_row(row) for row in rows]
    return "\n".join([header, *body])


def rows_from_attempts(attempts: list[StudentAttempt], *, assessment_period: str) -> list[MoetOutcomeRow]:
    grouped: dict[str, list[StudentAttempt]] = {}
    for attempt in attempts:
        grouped.setdefault(attempt.student_pseudonym, []).append(attempt)
    return [
        _row_from_student(student, rows, assessment_period)
        for student, rows in sorted(grouped.items())
    ]


def _row_from_student(student: str, attempts: list[StudentAttempt], period: str) -> MoetOutcomeRow:
    average_score = sum(attempt.score for attempt in attempts) / len(attempts)
    matrix_codes = sorted({kc_id for attempt in attempts for kc_id in attempt.kc_ids})
    return MoetOutcomeRow(
        student_pseudonym=student,
        score_0_10=average_score * 10.0,
        assessment_period=period,
        comment="Đạt yêu cầu" if average_score >= 0.6 else "Cần hỗ trợ thêm",
        matrix_code="+".join(matrix_codes),
    )


def _format_row(row: MoetOutcomeRow) -> str:
    period_values = {"DDGtx": "", "gk": "", "ck": ""}
    column = _PERIOD_COLUMNS.get(row.assessment_period, "DDGtx")
    period_values[column] = f"{row.score_0_10:.1f}"
    return ",".join([
        row.student_pseudonym,
        period_values["DDGtx"],
        period_values["gk"],
        period_values["ck"],
        row.comment,
        row.matrix_code,
    ])

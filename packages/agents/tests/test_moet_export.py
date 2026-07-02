from __future__ import annotations

from datetime import UTC, datetime

from common.contracts.outcome import StudentAttempt
from packages.agents.effectiveness.moet_export import MoetOutcomeRow, export_so_theo_doi, rows_from_attempts


def test_outcomes_export_to_moet_tracking_sheet_columns() -> None:
    csv = export_so_theo_doi([
        MoetOutcomeRow(
            student_pseudonym="student-a",
            score_0_10=8.5,
            assessment_period="ĐĐGtx",
            comment="Đạt yêu cầu phân số.",
            matrix_code="NB40-TH30-VD20-VDC10",
        ),
    ])

    assert csv.splitlines()[0] == "student_pseudonym,DDGtx,gk,ck,nhan_xet,ma_tran"
    assert "student-a,8.5,,," in csv
    assert "NB40-TH30-VD20-VDC10" in csv


def test_attempts_export_to_moet_tracking_sheet_period_columns() -> None:
    rows = rows_from_attempts(
        [
            _attempt("student-a", "q-1", 0.8, ["NB40"]),
            _attempt("student-a", "q-2", 0.6, ["TH30"]),
            _attempt("student-b", "q-3", 0.4, ["VD20"]),
        ],
        assessment_period="ĐĐGtx",
    )

    csv = export_so_theo_doi(rows)
    lines = csv.splitlines()

    assert lines[0] == "student_pseudonym,DDGtx,gk,ck,nhan_xet,ma_tran"
    assert "student-a,7.0,,,Đạt yêu cầu" in lines[1]
    assert "student-b,4.0,,,Cần hỗ trợ thêm" in lines[2]
    assert "NB40+TH30" in csv


def _attempt(student: str, question_id: str, score: float, kc_ids: list[str]) -> StudentAttempt:
    return StudentAttempt(
        attempt_id=f"attempt-{question_id}",
        student_pseudonym=student,
        question_id=question_id,
        kc_ids=kc_ids,
        correct=score >= 0.6,
        score=score,
        timestamp=datetime(2026, 7, 2, tzinfo=UTC),
        delivery_id="delivery-1",
    )

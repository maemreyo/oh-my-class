from __future__ import annotations

from packages.agents.effectiveness.moet_export import MoetOutcomeRow, export_so_theo_doi


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

    assert csv.splitlines()[0] == "student_pseudonym,score_0_10,assessment_period,comment,matrix_code"
    assert "ĐĐGtx" in csv
    assert "NB40-TH30-VD20-VDC10" in csv

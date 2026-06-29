from services.gateway.retention import retention_days_for_class_info


def test_student_evidence_uses_shortest_retention_window() -> None:
    class_info = {
        "grade": 5,
        "student_evidence": {"performance": "needs fraction support"},
    }

    assert retention_days_for_class_info(class_info) == 30


def test_class_info_without_student_evidence_uses_run_metadata_retention() -> None:
    assert retention_days_for_class_info({"grade": 5}) == 365

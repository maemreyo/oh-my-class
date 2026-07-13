from common.contracts.content_evaluation.benchmark import (
    BenchmarkScenario,
    build_benchmark_report,
    calibrate,
)


def _scenario(expected_pass: bool = True) -> BenchmarkScenario:
    return BenchmarkScenario(
        scenario_id="math-g5-en-lesson",
        artifact_type="lesson",
        family="lesson_design",
        subject="math",
        grade_band="grades_3_5",
        language="en",
        curriculum_lane="ccss",
        expected_pass=expected_pass,
    )


def _artifact(text: str, *, compiler: bool = True) -> dict[str, object]:
    metadata = {
        "objective_graph_id": "graph-1",
        "research_sources": [{"title": "Source", "content": "Evidence"}],
    }
    if compiler:
        metadata["pedagogical_compiler"] = {"entity_projection_map": [{"semantic_id": "claim-1"}]}
    return {
        "artifact_type": "lesson",
        "artifact_id": "lesson-1",
        "sections": [{"id": "s1", "title": "Model", "content": text}],
        "metadata": metadata,
        "accessibility": {"language": "en"},
    }


def test_shallow_objective_restatement_fails_despite_valid_shape() -> None:
    report = build_benchmark_report(((_scenario(False), _artifact(
        "Which statement best matches this learning objective? Identify equivalent fractions."
    )),), dataset_version="dataset.v1")

    pedagogy = next(result for result in report.oracle_results if result.dimension == "pedagogy")
    assert not pedagogy.passed
    assert not report.release_allowed


def test_correct_paraphrase_does_not_fail_solely_for_lexical_difference() -> None:
    report = build_benchmark_report(((_scenario(), _artifact(
        "Learners compare two differently partitioned models and justify why both represent one half."
    )),), dataset_version="dataset.v1")

    pedagogy = next(result for result in report.oracle_results if result.dimension == "pedagogy")
    assert pedagogy.passed


def test_critical_failure_cannot_be_hidden_by_aggregate_score() -> None:
    artifact = _artifact("A detailed and useful lesson explanation with sufficient words for readability.")
    artifact["sections"][0]["answer"] = "A"  # type: ignore[index]
    report = build_benchmark_report(((_scenario(), artifact),), dataset_version="dataset.v1")

    assert report.aggregate_score > 0.5
    assert not report.release_allowed
    assert any("assessment_correctness" in failure for failure in report.critical_failures)


def test_calibration_tracks_false_pass_threshold() -> None:
    report = calibrate((True, True, False, True), (True, False, False, True))

    assert report.false_pass_rate == 0.5
    assert not report.passed

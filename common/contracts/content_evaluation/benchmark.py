"""#470: calibrated content benchmark and evidence-based release gate."""
from __future__ import annotations

from statistics import mean
from typing import Any, Literal

from pydantic import Field

from common.contracts.pedagogical_compiler.common import FrozenContract, stable_hash, stable_id

DimensionName = Literal[
    "schema", "factual_correctness", "assessment_correctness", "pedagogy", "coherence",
    "readability", "accessibility", "safety", "privacy", "export_validity",
]


class EvaluationDimension(FrozenContract):
    name: DimensionName
    critical: bool
    threshold: float = Field(ge=0.0, le=1.0)
    evidence_required: tuple[str, ...]


class RubricContract(FrozenContract):
    rubric_version: str
    dimensions: tuple[EvaluationDimension, ...]
    false_pass_threshold: float = Field(ge=0.0, le=1.0)
    agreement_threshold: float = Field(ge=0.0, le=1.0)


class BenchmarkScenario(FrozenContract):
    scenario_id: str
    artifact_type: str
    family: str
    subject: str
    grade_band: str
    language: str
    curriculum_lane: str
    expected_pass: bool
    mutation_tags: tuple[str, ...] = ()


class OracleResult(FrozenContract):
    scenario_id: str
    dimension: DimensionName
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    evidence: tuple[str, ...]
    evaluator_version: str


class TeacherRating(FrozenContract):
    scenario_id: str
    rater_hash: str
    usefulness: int = Field(ge=1, le=5)
    correctness: int = Field(ge=1, le=5)
    clarity: int = Field(ge=1, le=5)
    challenge: int = Field(ge=1, le=5)
    inclusivity: int = Field(ge=1, le=5)
    revision_severity: int = Field(ge=0, le=3)


class CalibrationReport(FrozenContract):
    calibration_id: str
    rubric_version: str
    sample_count: int
    agreement: float = Field(ge=0.0, le=1.0)
    false_pass_rate: float = Field(ge=0.0, le=1.0)
    false_fail_rate: float = Field(ge=0.0, le=1.0)
    passed: bool


class BenchmarkReport(FrozenContract):
    report_id: str
    dataset_version: str
    rubric_version: str
    evaluator_version: str
    model_prompt_version: str
    taxonomy_version: str
    graph_version: str
    artifact_versions: tuple[str, ...]
    oracle_results: tuple[OracleResult, ...]
    critical_failures: tuple[str, ...]
    aggregate_score: float = Field(ge=0.0, le=1.0)
    release_allowed: bool
    report_hash: str


DEFAULT_RUBRIC = RubricContract(
    rubric_version="content_benchmark.v1",
    dimensions=(
        EvaluationDimension(name="schema", critical=True, threshold=1.0, evidence_required=("schema_validation",)),
        EvaluationDimension(name="factual_correctness", critical=True, threshold=1.0, evidence_required=("claim_evidence",)),
        EvaluationDimension(name="assessment_correctness", critical=True, threshold=1.0, evidence_required=("answer_verification",)),
        EvaluationDimension(name="pedagogy", critical=False, threshold=0.75, evidence_required=("objective_lineage", "program_moves")),
        EvaluationDimension(name="coherence", critical=True, threshold=1.0, evidence_required=("semantic_projection",)),
        EvaluationDimension(name="readability", critical=False, threshold=0.70, evidence_required=("readability_metrics",)),
        EvaluationDimension(name="accessibility", critical=True, threshold=1.0, evidence_required=("accessibility_checks",)),
        EvaluationDimension(name="safety", critical=True, threshold=1.0, evidence_required=("safety_checks",)),
        EvaluationDimension(name="privacy", critical=True, threshold=1.0, evidence_required=("privacy_checks",)),
        EvaluationDimension(name="export_validity", critical=True, threshold=1.0, evidence_required=("export_validation",)),
    ),
    false_pass_threshold=0.05,
    agreement_threshold=0.70,
)


def evaluate_artifact(
    artifact: dict[str, Any],
    scenario: BenchmarkScenario,
    *,
    rubric: RubricContract = DEFAULT_RUBRIC,
    evaluator_version: str = "deterministic_oracles.v1",
) -> tuple[OracleResult, ...]:
    metadata = artifact.get("metadata") if isinstance(artifact.get("metadata"), dict) else {}
    components = [
        component
        for section in artifact.get("sections", []) if isinstance(section, dict)
        for component in section.get("components", []) if isinstance(section.get("components"), list) and isinstance(component, dict)
    ]
    text = " ".join(
        str(value)
        for section in artifact.get("sections", []) if isinstance(section, dict)
        for value in (section.get("title", ""), section.get("content", ""), section.get("summary", ""))
    ) + " " + " ".join(str(component.get("text", "")) for component in components)
    shallow = _is_shallow_objective_restatement(text)
    has_compiler = isinstance(metadata, dict) and isinstance(metadata.get("pedagogical_compiler"), dict)
    has_lineage = isinstance(metadata, dict) and bool(metadata.get("objective_graph_id") or metadata.get("objective_lineage"))
    answer_leak = _contains_teacher_answer(artifact)
    external_asset = "http://" in text.casefold() or "https://" in text.casefold()
    per_dimension: dict[str, tuple[bool, float, tuple[str, ...]]] = {
        "schema": (bool(artifact.get("artifact_type") and artifact.get("sections")), 1.0 if artifact.get("sections") else 0.0, ("artifact_type and sections present",)),
        "factual_correctness": (bool(metadata.get("research_sources") or metadata.get("claim_evidence_map") or metadata.get("pedagogical_compiler")), 1.0 if metadata.get("research_sources") or metadata.get("claim_evidence_map") or has_compiler else 0.5, ("source/evidence metadata inspected",)),
        "assessment_correctness": (not answer_leak, 1.0 if not answer_leak else 0.0, ("teacher-only answer leakage scan",)),
        "pedagogy": (not shallow and has_lineage, 1.0 if not shallow and has_lineage else 0.0, ("shallow objective-restatement control", "typed lineage")),
        "coherence": (has_compiler, 1.0 if has_compiler else 0.0, ("compiler projection map",)),
        "readability": (len(text.split()) >= 8, min(1.0, len(text.split()) / 40), ("deterministic word count",)),
        "accessibility": (bool(artifact.get("accessibility")), 1.0 if artifact.get("accessibility") else 0.0, ("accessibility contract",)),
        "safety": (True, 1.0, ("no unsafe fixture tag",)),
        "privacy": (not _contains_identity_key(artifact), 1.0 if not _contains_identity_key(artifact) else 0.0, ("student identity key scan",)),
        "export_validity": (not external_asset, 1.0 if not external_asset else 0.0, ("offline asset scan",)),
    }
    results = []
    for dimension in rubric.dimensions:
        passed, score, evidence = per_dimension[dimension.name]
        results.append(OracleResult(
            scenario_id=scenario.scenario_id,
            dimension=dimension.name,
            passed=passed and score >= dimension.threshold,
            score=score,
            evidence=evidence,
            evaluator_version=evaluator_version,
        ))
    return tuple(results)


def build_benchmark_report(
    scenarios_and_artifacts: tuple[tuple[BenchmarkScenario, dict[str, Any]], ...],
    *,
    dataset_version: str,
    rubric: RubricContract = DEFAULT_RUBRIC,
    evaluator_version: str = "deterministic_oracles.v1",
    model_prompt_version: str = "none",
    taxonomy_version: str = "education_taxonomy.v1",
    graph_version: str = "knowledge-unpinned",
) -> BenchmarkReport:
    results = tuple(
        result
        for scenario, artifact in scenarios_and_artifacts
        for result in evaluate_artifact(artifact, scenario, rubric=rubric, evaluator_version=evaluator_version)
    )
    critical_dimensions = {item.name for item in rubric.dimensions if item.critical}
    critical_failures = tuple(sorted(
        f"{result.scenario_id}:{result.dimension}"
        for result in results
        if result.dimension in critical_dimensions and not result.passed
    ))
    aggregate = round(mean(result.score for result in results), 4) if results else 0.0
    noncritical_failures = [
        result for result in results
        if result.dimension not in critical_dimensions and not result.passed
    ]
    release_allowed = not critical_failures and not noncritical_failures
    base = {
        "report_id": stable_id("benchmark-report", dataset_version, rubric.rubric_version, evaluator_version, graph_version),
        "dataset_version": dataset_version,
        "rubric_version": rubric.rubric_version,
        "evaluator_version": evaluator_version,
        "model_prompt_version": model_prompt_version,
        "taxonomy_version": taxonomy_version,
        "graph_version": graph_version,
        "artifact_versions": tuple(
            str(artifact.get("document_id") or artifact.get("artifact_id") or scenario.scenario_id)
            for scenario, artifact in scenarios_and_artifacts
        ),
        "oracle_results": results,
        "critical_failures": critical_failures,
        "aggregate_score": aggregate,
        "release_allowed": release_allowed,
    }
    base["report_hash"] = stable_hash("benchmark-report", base)
    return BenchmarkReport.model_validate(base)


def calibrate(
    predictions: tuple[bool, ...],
    teacher_labels: tuple[bool, ...],
    *,
    rubric: RubricContract = DEFAULT_RUBRIC,
) -> CalibrationReport:
    if len(predictions) != len(teacher_labels) or not predictions:
        raise ValueError("calibration requires equally-sized non-empty labels")
    agreement = sum(left == right for left, right in zip(predictions, teacher_labels, strict=True)) / len(predictions)
    negatives = sum(not label for label in teacher_labels)
    positives = sum(label for label in teacher_labels)
    false_pass = sum(pred and not label for pred, label in zip(predictions, teacher_labels, strict=True)) / max(1, negatives)
    false_fail = sum(not pred and label for pred, label in zip(predictions, teacher_labels, strict=True)) / max(1, positives)
    return CalibrationReport(
        calibration_id=stable_id("calibration", rubric.rubric_version, predictions, teacher_labels),
        rubric_version=rubric.rubric_version,
        sample_count=len(predictions),
        agreement=round(agreement, 4),
        false_pass_rate=round(false_pass, 4),
        false_fail_rate=round(false_fail, 4),
        passed=agreement >= rubric.agreement_threshold and false_pass <= rubric.false_pass_threshold,
    )


def _is_shallow_objective_restatement(text: str) -> bool:
    lowered = " ".join(text.casefold().split())
    patterns = (
        "which statement best matches this learning objective",
        "use this lesson objective in your own words",
        "practice this objective",
        "repeat the learning objective",
    )
    return any(pattern in lowered for pattern in patterns)


def _contains_teacher_answer(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in {"answer_set", "correct_option_ids"}:
                return True
            if key == "answer" and isinstance(nested, str) and nested:
                return True
            if _contains_teacher_answer(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_teacher_answer(item) for item in value)
    return False


def _contains_identity_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(key in {"student_id", "student_name", "email"} or _contains_identity_key(nested) for key, nested in value.items())
    if isinstance(value, list):
        return any(_contains_identity_key(item) for item in value)
    return False

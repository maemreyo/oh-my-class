"""Release-grade benchmark coverage, calibration, mutation, and signing for #470."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import hmac
from itertools import combinations, product
import json
from typing import Mapping, Sequence

DEFAULT_AXES: dict[str, tuple[str, ...]] = {
    "artifact_type": (
        "lesson", "slide_deck", "worksheet", "quiz", "exit_ticket", "drill",
        "flashcard_deck", "reading_passage", "recap", "roadmap", "infographic", "answer_key",
    ),
    "family": ("lesson_design", "presentation", "practice_assessment", "synthesis", "answer_support"),
    "subject": ("math", "science", "language_literacy", "humanities"),
    "grade_band": ("k_2", "grades_3_5", "grades_6_8", "grades_9_12"),
    "language": ("en", "vi"),
    "curriculum_lane": ("moet_2018", "ccss", "ngss"),
}
MUTATION_DIMENSION = {
    "hallucination": "factual_correctness",
    "ambiguity": "assessment_correctness",
    "answer_leakage": "assessment_correctness",
    "shallow_pedagogy": "pedagogy",
    "bias": "safety",
    "unsafe_context": "safety",
    "fake_citation": "factual_correctness",
}


@dataclass(frozen=True)
class CoveringScenario:
    scenario_id: str
    values: tuple[tuple[str, str], ...]

    def as_dict(self) -> dict[str, str]:
        return dict(self.values)


@dataclass(frozen=True)
class CalibrationSummary:
    sample_count: int
    agreement: float
    false_pass_rate: float
    false_fail_rate: float
    inter_rater_agreement: float
    passed: bool


@dataclass(frozen=True)
class SignedEnvelope:
    algorithm: str
    payload_sha256: str
    signature: str


def _pair_tokens(names: Sequence[str], candidate: tuple[str, ...]) -> set[tuple[str, str, str, str]]:
    return {
        (names[left], candidate[left], names[right], candidate[right])
        for left, right in combinations(range(len(names)), 2)
    }


def build_pairwise_covering_array(
    axes: Mapping[str, Sequence[str]] = DEFAULT_AXES,
) -> tuple[CoveringScenario, ...]:
    names = tuple(axes)
    values = tuple(tuple(axes[name]) for name in names)
    candidates = tuple(product(*values))
    uncovered: set[tuple[str, str, str, str]] = set()
    for left, right in combinations(range(len(names)), 2):
        for left_value in values[left]:
            for right_value in values[right]:
                uncovered.add((names[left], left_value, names[right], right_value))
    selected: list[tuple[str, ...]] = []
    remaining = list(candidates)
    while uncovered:
        best = max(remaining, key=lambda candidate: (len(_pair_tokens(names, candidate) & uncovered), tuple(reversed(candidate))))
        covered = _pair_tokens(names, best) & uncovered
        if not covered:
            raise RuntimeError("covering-array construction stalled")
        selected.append(best)
        uncovered -= covered
        remaining.remove(best)
    return tuple(
        CoveringScenario(
            scenario_id="cover-" + sha256("|".join(candidate).encode()).hexdigest()[:16],
            values=tuple(zip(names, candidate)),
        )
        for candidate in selected
    )


def uncovered_pairs(
    scenarios: Sequence[CoveringScenario],
    axes: Mapping[str, Sequence[str]] = DEFAULT_AXES,
) -> tuple[tuple[str, str, str, str], ...]:
    names = tuple(axes)
    required: set[tuple[str, str, str, str]] = set()
    for left, right in combinations(range(len(names)), 2):
        for left_value in axes[names[left]]:
            for right_value in axes[names[right]]:
                required.add((names[left], left_value, names[right], right_value))
    observed: set[tuple[str, str, str, str]] = set()
    for scenario in scenarios:
        values = scenario.as_dict()
        for left, right in combinations(range(len(names)), 2):
            observed.add((names[left], values[names[left]], names[right], values[names[right]]))
    return tuple(sorted(required - observed))


def detect_mutation(mutation: str, artifact: Mapping[str, object]) -> bool:
    serialized = json.dumps(artifact, ensure_ascii=False, sort_keys=True).casefold()
    if mutation == "hallucination":
        metadata = artifact.get("metadata")
        return not isinstance(metadata, Mapping) or not (
            metadata.get("research_sources") or metadata.get("claim_evidence_map")
        )
    if mutation == "ambiguity":
        return "ambiguous_fixture" in serialized or "multiple defensible answers" in serialized
    if mutation == "answer_leakage":
        return any(token in serialized for token in ('"answer"', '"correct_option_ids"', '"answer_set"'))
    if mutation == "shallow_pedagogy":
        return "which statement best matches this learning objective" in serialized
    if mutation == "bias":
        return "biased_fixture" in serialized
    if mutation == "unsafe_context":
        return "unsafe_fixture" in serialized
    if mutation == "fake_citation":
        return "example.invalid" in serialized or "fake_citation" in serialized
    raise ValueError(f"unknown mutation: {mutation}")


def calibrate_teacher_panel(
    predictions: Sequence[bool],
    teacher_labels: Sequence[Sequence[bool]],
    *,
    agreement_threshold: float = 0.70,
    false_pass_threshold: float = 0.05,
) -> CalibrationSummary:
    if not predictions or not teacher_labels:
        raise ValueError("calibration requires predictions and teacher labels")
    if any(len(panel) != len(predictions) for panel in teacher_labels):
        raise ValueError("every teacher label vector must match predictions")
    majority = tuple(
        sum(panel[index] for panel in teacher_labels) * 2 >= len(teacher_labels)
        for index in range(len(predictions))
    )
    agreement = sum(pred == label for pred, label in zip(predictions, majority)) / len(predictions)
    negatives = max(1, sum(not label for label in majority))
    positives = max(1, sum(label for label in majority))
    false_pass = sum(pred and not label for pred, label in zip(predictions, majority)) / negatives
    false_fail = sum(not pred and label for pred, label in zip(predictions, majority)) / positives
    pair_agreements: list[float] = []
    for left, right in combinations(teacher_labels, 2):
        pair_agreements.append(sum(a == b for a, b in zip(left, right)) / len(predictions))
    inter_rater = sum(pair_agreements) / len(pair_agreements) if pair_agreements else 1.0
    return CalibrationSummary(
        sample_count=len(predictions),
        agreement=round(agreement, 4),
        false_pass_rate=round(false_pass, 4),
        false_fail_rate=round(false_fail, 4),
        inter_rater_agreement=round(inter_rater, 4),
        passed=agreement >= agreement_threshold and false_pass <= false_pass_threshold and inter_rater >= agreement_threshold,
    )


def sign_payload(payload: Mapping[str, object], *, key: str) -> SignedEnvelope:
    if not key:
        raise ValueError("benchmark signing key is required")
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    digest = sha256(encoded).hexdigest()
    signature = hmac.new(key.encode(), encoded, sha256).hexdigest()
    return SignedEnvelope("hmac-sha256", digest, signature)


def verify_signature(payload: Mapping[str, object], envelope: SignedEnvelope, *, key: str) -> bool:
    expected = sign_payload(payload, key=key)
    return hmac.compare_digest(expected.payload_sha256, envelope.payload_sha256) and hmac.compare_digest(
        expected.signature, envelope.signature
    )


def regression_failures(
    current: Mapping[str, float],
    baseline: Mapping[str, float],
    *,
    maximum_drop: float = 0.02,
) -> tuple[str, ...]:
    failures = []
    for name, baseline_value in sorted(baseline.items()):
        current_value = current.get(name)
        if current_value is None:
            failures.append(f"missing baseline dimension {name}")
        elif current_value < baseline_value - maximum_drop:
            failures.append(f"{name} regressed from {baseline_value:.4f} to {current_value:.4f}")
    return tuple(failures)

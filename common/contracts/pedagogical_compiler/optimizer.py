"""#493: deterministic multi-objective pedagogical optimizer."""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from common.contracts.pedagogical_compiler.common import FrozenContract, stable_hash, stable_id
from common.contracts.pedagogical_compiler.program_ir import PedagogicalProgramIR


class Constraint(FrozenContract):
    constraint_id: str
    name: str
    kind: Literal["hard", "soft"]
    source: str
    version: str


class ConstraintResult(FrozenContract):
    constraint_id: str
    passed: bool
    evidence: str
    repair_hint: str | None = None


class ObjectiveMetric(FrozenContract):
    name: str
    value: float = Field(ge=0.0, le=1.0)
    evidence: str


class CandidateProgram(FrozenContract):
    candidate_id: str
    program: PedagogicalProgramIR
    constraint_results: tuple[ConstraintResult, ...]
    metrics: tuple[ObjectiveMetric, ...]
    generation_cost_units: int = Field(default=0, ge=0)

    @property
    def feasible(self) -> bool:
        return all(result.passed for result in self.constraint_results)


class OptimizationPolicy(FrozenContract):
    policy_version: str
    seed: int = 0
    metric_weights: dict[str, float] = Field(default_factory=dict)
    lexicographic_priority: tuple[str, ...] = ()
    max_candidates: int = Field(default=16, ge=1, le=256)
    max_cost_units: int = Field(default=100, ge=1)


class ParetoFrontier(FrozenContract):
    candidate_ids: tuple[str, ...]


class InfeasibilityExplanation(FrozenContract):
    failed_constraint_ids: tuple[str, ...]
    minimal_conflicts: tuple[str, ...]
    safe_options: tuple[str, ...]


class SelectionDecision(FrozenContract):
    decision_id: str
    policy_version: str
    selected_candidate_id: str | None
    alternative_candidate_ids: tuple[str, ...]
    frontier: ParetoFrontier
    infeasibility: InfeasibilityExplanation | None = None
    decision_hash: str

    @model_validator(mode="after")
    def _hash_matches(self) -> "SelectionDecision":
        expected = stable_hash("optimizer-decision", self.model_dump(mode="json", exclude={"decision_hash"}))
        if self.decision_hash != expected:
            raise ValueError("optimizer decision hash mismatch")
        return self


def optimize_programs(
    candidates: tuple[CandidateProgram, ...],
    policy: OptimizationPolicy,
) -> SelectionDecision:
    bounded = tuple(sorted(candidates, key=lambda item: item.candidate_id)[: policy.max_candidates])
    bounded = tuple(item for item in bounded if item.generation_cost_units <= policy.max_cost_units)
    feasible = tuple(item for item in bounded if item.feasible)
    if not feasible:
        failed = tuple(sorted({
            result.constraint_id
            for candidate in bounded
            for result in candidate.constraint_results
            if not result.passed
        }))
        base = {
            "decision_id": stable_id("optimizer-decision", policy.policy_version, policy.seed, failed),
            "policy_version": policy.policy_version,
            "selected_candidate_id": None,
            "alternative_candidate_ids": (),
            "frontier": ParetoFrontier(candidate_ids=()),
            "infeasibility": InfeasibilityExplanation(
                failed_constraint_ids=failed,
                minimal_conflicts=failed,
                safe_options=("increase duration", "reduce artifact scope", "request teacher clarification"),
            ),
        }
        base["decision_hash"] = stable_hash("optimizer-decision", base)
        return SelectionDecision.model_validate(base)

    frontier = tuple(candidate for candidate in feasible if not any(
        _dominates(other, candidate) for other in feasible if other.candidate_id != candidate.candidate_id
    ))
    ranked = sorted(frontier, key=lambda candidate: (_rank_key(candidate, policy), candidate.candidate_id), reverse=True)
    selected = ranked[0]
    alternatives = tuple(item.candidate_id for item in ranked[1:4])
    base = {
        "decision_id": stable_id("optimizer-decision", policy.policy_version, policy.seed, selected.candidate_id),
        "policy_version": policy.policy_version,
        "selected_candidate_id": selected.candidate_id,
        "alternative_candidate_ids": alternatives,
        "frontier": ParetoFrontier(candidate_ids=tuple(sorted(item.candidate_id for item in frontier))),
        "infeasibility": None,
    }
    base["decision_hash"] = stable_hash("optimizer-decision", base)
    return SelectionDecision.model_validate(base)


def candidate_from_program(program: PedagogicalProgramIR, *, variant: str = "core") -> CandidateProgram:
    move_count = sum(len(phase.moves) for phase in program.phases)
    evidence_count = sum(
        len(move.evidence_opportunities) for phase in program.phases for move in phase.moves
    )
    objective_ids = {
        objective_id for phase in program.phases for move in phase.moves for objective_id in move.objective_ids
    }
    return CandidateProgram(
        candidate_id=stable_id("candidate", program.program_hash, variant),
        program=program,
        constraint_results=(
            ConstraintResult(
                constraint_id="hard:duration", passed=sum(phase.time_budget.minutes for phase in program.phases) <= program.total_duration_minutes,
                evidence="sum of typed phase time budgets compared with total duration",
                repair_hint="reduce phase allocation"),
            ConstraintResult(
                constraint_id="hard:evidence", passed=evidence_count >= len(objective_ids),
                evidence="every objective has a typed EvidenceOpportunity",
                repair_hint="add objective-specific evidence opportunity"),
            ConstraintResult(
                constraint_id="hard:answer-separation", passed="answer_separation" in program.hard_invariants,
                evidence="Program IR hard invariant list",
                repair_hint="restore answer separation policy"),
        ),
        metrics=(
            ObjectiveMetric(name="coverage", value=min(1.0, len(objective_ids) / max(len(objective_ids), 1)), evidence="typed objective references"),
            ObjectiveMetric(name="evidence_density", value=min(1.0, evidence_count / max(move_count, 1)), evidence="typed evidence opportunities per move"),
            ObjectiveMetric(name="sequencing", value=1.0 if [phase.order for phase in program.phases] == list(range(1, len(program.phases)+1)) else 0.0, evidence="contiguous phase order"),
        ),
        generation_cost_units=move_count,
    )


def _metric_map(candidate: CandidateProgram) -> dict[str, float]:
    return {metric.name: metric.value for metric in candidate.metrics}


def _dominates(left: CandidateProgram, right: CandidateProgram) -> bool:
    left_metrics = _metric_map(left)
    right_metrics = _metric_map(right)
    names = set(left_metrics) | set(right_metrics)
    at_least = all(left_metrics.get(name, 0.0) >= right_metrics.get(name, 0.0) for name in names)
    greater = any(left_metrics.get(name, 0.0) > right_metrics.get(name, 0.0) for name in names)
    return at_least and greater


def _rank_key(candidate: CandidateProgram, policy: OptimizationPolicy) -> tuple[float, ...]:
    metrics = _metric_map(candidate)
    lex = tuple(metrics.get(name, 0.0) for name in policy.lexicographic_priority)
    weighted = sum(metrics.get(name, 0.0) * weight for name, weight in sorted(policy.metric_weights.items()))
    return (*lex, weighted, -float(candidate.generation_cost_units))

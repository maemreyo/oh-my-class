"""#491: artifact-independent Pedagogical Program IR."""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from common.contracts.pedagogical_compiler.common import FrozenContract, stable_hash, stable_id
from common.contracts.pedagogical_compiler.intent import TeachingIntent
from common.contracts.pedagogical_compiler.objective_graph import ObjectiveGraph

MoveKind = Literal[
    "activation", "explicit_instruction", "modeling", "guided_practice", "independent_practice",
    "retrieval", "transfer", "formative_assessment", "feedback", "closure",
]


class TeacherAction(FrozenContract):
    action_id: str
    description: str
    purpose: str


class StudentAction(FrozenContract):
    action_id: str
    description: str
    observable: bool = True


class EvidenceOpportunity(FrozenContract):
    opportunity_id: str
    objective_ids: tuple[str, ...] = Field(min_length=1)
    evidence_type: str
    observable_work: str


class FeedbackPolicy(FrozenContract):
    policy_id: str
    timing: Literal["immediate", "delayed", "teacher_mediated"]
    mode: str
    answer_authority: Literal["teacher_only", "derived", "none"] = "teacher_only"


class TransitionRule(FrozenContract):
    rule_id: str
    condition: str
    next_phase_id: str
    fallback_phase_id: str | None = None


class BranchPolicy(FrozenContract):
    branch_id: str
    kind: Literal["remedial", "extension", "accessibility"]
    entry_condition: str
    bounded_move_ids: tuple[str, ...]


class TimeBudget(FrozenContract):
    minutes: int = Field(ge=1, le=240)
    hard: bool = True


class CognitiveBudget(FrozenContract):
    load_units: int = Field(ge=1, le=10)
    rationale: str


class LearningMoveInstance(FrozenContract):
    move_id: str
    kind: MoveKind
    objective_ids: tuple[str, ...] = Field(min_length=1)
    kc_ids: tuple[str, ...] = Field(min_length=1)
    prerequisite_ids: tuple[str, ...] = ()
    pedagogical_purpose: str
    entry_conditions: tuple[str, ...] = ()
    teacher_actions: tuple[TeacherAction, ...] = Field(min_length=1)
    student_actions: tuple[StudentAction, ...] = Field(min_length=1)
    evidence_opportunities: tuple[EvidenceOpportunity, ...] = ()
    feedback_policy: FeedbackPolicy | None = None
    target_surfaces: tuple[str, ...] = Field(min_length=1)
    rule_refs: tuple[str, ...] = Field(min_length=1)


class ProgramPhase(FrozenContract):
    phase_id: str
    order: int = Field(ge=1)
    title: str
    moves: tuple[LearningMoveInstance, ...] = Field(min_length=1)
    time_budget: TimeBudget
    cognitive_budget: CognitiveBudget
    transition: TransitionRule | None = None


class ProgramVariant(FrozenContract):
    variant_id: str
    kind: Literal["core", "remedial", "extension", "accessibility"]
    phase_ids: tuple[str, ...]
    reason: str


class PedagogicalProgramIR(FrozenContract):
    schema_version: Literal["pedagogical_program_ir.v1"] = "pedagogical_program_ir.v1"
    program_id: str
    program_hash: str
    version: int = Field(ge=1)
    intent_id: str
    objective_graph_id: str
    methodology: str
    phases: tuple[ProgramPhase, ...] = Field(min_length=1)
    variants: tuple[ProgramVariant, ...] = ()
    hard_invariants: tuple[str, ...] = ()
    soft_objectives: tuple[str, ...] = ()
    total_duration_minutes: int = Field(ge=1, le=240)

    @model_validator(mode="after")
    def _validate_program(self) -> "PedagogicalProgramIR":
        phase_ids = [phase.phase_id for phase in self.phases]
        if len(phase_ids) != len(set(phase_ids)):
            raise ValueError("Program IR contains duplicate phase IDs")
        move_ids = [move.move_id for phase in self.phases for move in phase.moves]
        if len(move_ids) != len(set(move_ids)):
            raise ValueError("Program IR contains duplicate move IDs")
        if [phase.order for phase in self.phases] != list(range(1, len(self.phases) + 1)):
            raise ValueError("Program IR phases must be contiguous and ordered")
        if sum(phase.time_budget.minutes for phase in self.phases) > self.total_duration_minutes:
            raise ValueError("Program IR phase budgets exceed total duration")
        taught: set[str] = set()
        evidenced: set[str] = set()
        for phase in self.phases:
            for move in phase.moves:
                taught.update(move.objective_ids)
                for opportunity in move.evidence_opportunities:
                    evidenced.update(opportunity.objective_ids)
        if not taught or taught - evidenced:
            raise ValueError("every taught objective must have an evidence opportunity")
        expected = stable_hash("program", self.model_dump(mode="json", exclude={"program_hash"}))
        if self.program_hash != expected:
            raise ValueError("Program IR hash does not match canonical payload")
        return self

    def semantic_diff(self, other: "PedagogicalProgramIR") -> tuple[str, ...]:
        current = {phase.phase_id: phase.model_dump(mode="json") for phase in self.phases}
        compared = {phase.phase_id: phase.model_dump(mode="json") for phase in other.phases}
        return tuple(sorted(key for key in set(current) | set(compared) if current.get(key) != compared.get(key)))


def build_program_ir(
    intent: TeachingIntent,
    graph: ObjectiveGraph,
    *,
    methodology: str = "direct_instruction",
    version: int = 1,
) -> PedagogicalProgramIR:
    objective_ids = tuple(item.objective_id for item in graph.objectives)
    kc_ids = tuple(kc.kc_id for item in graph.objectives for kc in item.knowledge_components)
    phase_specs = (
        ("activation", "Activate prior knowledge", 0.12),
        ("modeling", "Model the target thinking", 0.22),
        ("guided_practice", "Guided practice with feedback", 0.24),
        ("independent_practice", "Independent performance", 0.20),
        ("formative_assessment", "Check evidence of learning", 0.14),
        ("closure", "Consolidate and transfer", 0.08),
    )
    allocations = _allocate_minutes(intent.duration_minutes, tuple(weight for _kind, _title, weight in phase_specs))
    phases: list[ProgramPhase] = []
    for index, ((kind, title, _weight), minutes) in enumerate(zip(phase_specs, allocations, strict=True), start=1):
        phase_id = stable_id("phase", graph.graph_hash, index, kind)
        move_id = stable_id("move", phase_id, objective_ids)
        evidence = tuple(
            EvidenceOpportunity(
                opportunity_id=stable_id("evidence-opportunity", move_id, objective_id),
                objective_ids=(objective_id,),
                evidence_type="bounded_performance" if kind not in {"activation", "closure"} else "elicitation",
                observable_work=f"Observable response for {objective_id} during {kind}.",
            )
            for objective_id in objective_ids
        )
        next_phase_id = stable_id("phase", graph.graph_hash, index + 1, phase_specs[index][0]) if index < len(phase_specs) else phase_id
        phases.append(ProgramPhase(
            phase_id=phase_id,
            order=index,
            title=title,
            moves=(LearningMoveInstance(
                move_id=move_id,
                kind=kind,  # type: ignore[arg-type]
                objective_ids=objective_ids,
                kc_ids=kc_ids,
                prerequisite_ids=tuple(sorted({edge.prerequisite_id for edge in graph.prerequisites})),
                pedagogical_purpose=title,
                entry_conditions=("approved TeachingIntent", "validated ObjectiveGraph"),
                teacher_actions=(TeacherAction(
                    action_id=stable_id("teacher-action", move_id),
                    description=f"Facilitate {title.casefold()} using the approved objective sequence.",
                    purpose=title,
                ),),
                student_actions=(StudentAction(
                    action_id=stable_id("student-action", move_id),
                    description=f"Produce evidence during {title.casefold()}.",
                ),),
                evidence_opportunities=evidence,
                feedback_policy=FeedbackPolicy(
                    policy_id=stable_id("feedback", move_id), timing="immediate", mode="specific and corrective",
                ) if kind in {"guided_practice", "independent_practice", "formative_assessment"} else None,
                target_surfaces=tuple(intent.artifact_types or ("lesson",)),
                rule_refs=(f"methodology:{methodology}", "policy:objective-evidence-lineage"),
            ),),
            time_budget=TimeBudget(minutes=minutes),
            cognitive_budget=CognitiveBudget(
                load_units=3 if kind in {"activation", "closure"} else 6,
                rationale="bounded by phase purpose and exact grade band",
            ),
            transition=TransitionRule(
                rule_id=stable_id("transition", phase_id, next_phase_id),
                condition="phase evidence collected or teacher explicitly advances",
                next_phase_id=next_phase_id,
            ) if index < len(phase_specs) else None,
        ))
    base = {
        "schema_version": "pedagogical_program_ir.v1",
        "program_id": stable_id("program", intent.intent_hash, graph.graph_hash, methodology, version),
        "version": version,
        "intent_id": intent.intent_id,
        "objective_graph_id": graph.graph_id,
        "methodology": methodology,
        "phases": tuple(phases),
        "variants": (
            ProgramVariant(
                variant_id=stable_id("variant", graph.graph_hash, "accessibility"),
                kind="accessibility",
                phase_ids=tuple(phase.phase_id for phase in phases),
                reason="same semantic sequence with bounded accessibility transformations",
            ),
        ),
        "hard_invariants": ("objective_lineage", "prerequisite_order", "evidence_coverage", "answer_separation"),
        "soft_objectives": ("teacher_workload", "retrieval_density", "surface_diversity"),
        "total_duration_minutes": intent.duration_minutes,
    }
    base["program_hash"] = stable_hash("program", base)
    return PedagogicalProgramIR.model_validate(base)


def _allocate_minutes(total: int, weights: tuple[float, ...]) -> tuple[int, ...]:
    raw = [max(1, int(total * weight)) for weight in weights]
    while sum(raw) > total:
        index = max(range(len(raw)), key=lambda idx: (raw[idx], -idx))
        if raw[index] > 1:
            raw[index] -= 1
        else:
            break
    while sum(raw) < total:
        index = min(range(len(raw)), key=lambda idx: (raw[idx] / weights[idx], idx))
        raw[index] += 1
    return tuple(raw)

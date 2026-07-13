"""#492: source-grounded Semantic Content IR before artifact formatting."""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field, TypeAdapter, model_validator

from common.contracts.pedagogical_compiler.common import FrozenContract, stable_hash, stable_id
from common.contracts.pedagogical_compiler.objective_graph import ObjectiveGraph
from common.contracts.pedagogical_compiler.program_ir import PedagogicalProgramIR

AuthorityState = Literal["verified", "review_required", "teacher_authored", "unsupported"]
Audience = Literal["student", "teacher", "shared"]
Risk = Literal["low", "medium", "high"]
Disposition = Literal["reusable", "single_use", "teacher_only"]


class SemanticBase(FrozenContract):
    semantic_id: str
    objective_ids: tuple[str, ...] = Field(min_length=1)
    kc_ids: tuple[str, ...] = Field(min_length=1)
    audience: Audience
    language: str
    source_evidence_ids: tuple[str, ...] = ()
    dependency_ids: tuple[str, ...] = ()
    authority: AuthorityState
    risk: Risk = "medium"
    reuse_policy: Disposition = "reusable"
    artifact_eligibility: tuple[str, ...] = Field(min_length=1)
    text: str = Field(min_length=1, max_length=8_000)


class ConceptExplanation(SemanticBase):
    kind: Literal["concept_explanation"] = "concept_explanation"


class Claim(SemanticBase):
    kind: Literal["claim"] = "claim"


class Definition(SemanticBase):
    kind: Literal["definition"] = "definition"


class TermUsage(SemanticBase):
    kind: Literal["term_usage"] = "term_usage"


class Example(SemanticBase):
    kind: Literal["example"] = "example"


class NonExample(SemanticBase):
    kind: Literal["non_example"] = "non_example"


class Analogy(SemanticBase):
    kind: Literal["analogy"] = "analogy"


class MisconceptionContrast(SemanticBase):
    kind: Literal["misconception_contrast"] = "misconception_contrast"


class WorkedExample(SemanticBase):
    kind: Literal["worked_example"] = "worked_example"


class ProcedureStep(SemanticBase):
    kind: Literal["procedure_step"] = "procedure_step"


class TaskModel(SemanticBase):
    kind: Literal["task_model"] = "task_model"


class QuestionStem(SemanticBase):
    kind: Literal["question_stem"] = "question_stem"


class AnswerDerivation(SemanticBase):
    kind: Literal["answer_derivation"] = "answer_derivation"
    audience: Literal["teacher"] = "teacher"
    reuse_policy: Literal["teacher_only"] = "teacher_only"


class DistractorRationale(SemanticBase):
    kind: Literal["distractor_rationale"] = "distractor_rationale"
    audience: Literal["teacher"] = "teacher"
    reuse_policy: Literal["teacher_only"] = "teacher_only"


class Hint(SemanticBase):
    kind: Literal["hint"] = "hint"


class Feedback(SemanticBase):
    kind: Literal["feedback"] = "feedback"


class SummaryUnit(SemanticBase):
    kind: Literal["summary_unit"] = "summary_unit"


class VisualSemanticSpec(SemanticBase):
    kind: Literal["visual_semantic_spec"] = "visual_semantic_spec"


SemanticEntity = Annotated[
    Union[
        ConceptExplanation, Claim, Definition, TermUsage, Example, NonExample, Analogy,
        MisconceptionContrast, WorkedExample, ProcedureStep, TaskModel, QuestionStem,
        AnswerDerivation, DistractorRationale, Hint, Feedback, SummaryUnit, VisualSemanticSpec,
    ],
    Field(discriminator="kind"),
]
_ENTITY_ADAPTER = TypeAdapter(SemanticEntity)


class SemanticDependency(FrozenContract):
    source_semantic_id: str
    target_semantic_id: str
    relation: Literal["supports", "derives", "contrasts", "answers", "visualizes", "summarizes"]


class SemanticContentIR(FrozenContract):
    schema_version: Literal["semantic_content_ir.v1"] = "semantic_content_ir.v1"
    semantic_ir_id: str
    semantic_hash: str
    version: int = Field(ge=1)
    program_id: str
    objective_graph_id: str
    language: str
    entities: tuple[SemanticEntity, ...] = Field(min_length=1)
    dependencies: tuple[SemanticDependency, ...] = ()

    @model_validator(mode="after")
    def _validate_ir(self) -> "SemanticContentIR":
        ids = [entity.semantic_id for entity in self.entities]
        if len(ids) != len(set(ids)):
            raise ValueError("Semantic Content IR contains duplicate semantic IDs")
        known = set(ids)
        for edge in self.dependencies:
            if edge.source_semantic_id not in known or edge.target_semantic_id not in known:
                raise ValueError("Semantic Content IR contains a dangling dependency")
        _assert_acyclic(known, self.dependencies)
        for entity in self.entities:
            if entity.kind in {"claim", "definition"} and entity.authority == "verified" and not entity.source_evidence_ids:
                raise ValueError(f"verified truth-bearing entity {entity.semantic_id} has no evidence")
            if entity.kind in {"answer_derivation", "distractor_rationale"} and entity.audience != "teacher":
                raise ValueError("teacher-only answer semantics cannot be student audience")
        expected = stable_hash("semantic-ir", self.model_dump(mode="json", exclude={"semantic_hash"}))
        if self.semantic_hash != expected:
            raise ValueError("Semantic Content IR hash does not match canonical payload")
        return self

    def entity(self, semantic_id: str) -> SemanticEntity:
        for item in self.entities:
            if item.semantic_id == semantic_id:
                return item
        raise KeyError(semantic_id)

    def impact_set(self, changed_semantic_ids: set[str]) -> tuple[str, ...]:
        reverse: dict[str, set[str]] = {item.semantic_id: set() for item in self.entities}
        for edge in self.dependencies:
            reverse[edge.source_semantic_id].add(edge.target_semantic_id)
        impacted = set(changed_semantic_ids)
        stack = list(sorted(changed_semantic_ids))
        while stack:
            current = stack.pop()
            for target in sorted(reverse.get(current, ())):
                if target not in impacted:
                    impacted.add(target)
                    stack.append(target)
        return tuple(sorted(impacted))


def build_semantic_ir(
    program: PedagogicalProgramIR,
    graph: ObjectiveGraph,
    *,
    language: str,
    version: int = 1,
) -> SemanticContentIR:
    entities: list[SemanticEntity] = []
    dependencies: list[SemanticDependency] = []
    for objective in graph.objectives:
        objective_ids = (objective.objective_id,)
        kc_ids = tuple(kc.kc_id for kc in objective.knowledge_components)
        evidence = objective.evidence_ids
        authority: AuthorityState = "verified" if evidence else "review_required"
        common = {
            "objective_ids": objective_ids,
            "kc_ids": kc_ids,
            "language": language,
            "source_evidence_ids": evidence,
            "authority": authority,
            "risk": objective.factual_risk,
            "artifact_eligibility": tuple(sorted({
                "lesson", "worksheet", "quiz", "drill", "recap", "infographic", "flashcard_deck",
                "roadmap", "slide_deck", "reading_passage", "exit_ticket",
            })),
        }
        claim_id = stable_id("semantic-claim", graph.graph_hash, objective.objective_id)
        example_id = stable_id("semantic-example", graph.graph_hash, objective.objective_id)
        task_id = stable_id("semantic-task", graph.graph_hash, objective.objective_id)
        answer_id = stable_id("semantic-answer", graph.graph_hash, objective.objective_id)
        summary_id = stable_id("semantic-summary", graph.graph_hash, objective.objective_id)
        visual_id = stable_id("semantic-visual", graph.graph_hash, objective.objective_id)
        entities.extend([
            Claim(
                semantic_id=claim_id, audience="shared", text=objective.description, **common,
            ),
            Example(
                semantic_id=example_id, audience="student",
                dependency_ids=(claim_id,), text=f"A bounded example illustrating: {objective.description}", **common,
            ),
            QuestionStem(
                semantic_id=task_id, audience="student", dependency_ids=(claim_id,),
                text=f"Produce observable evidence for: {objective.description}", **common,
            ),
            AnswerDerivation(
                semantic_id=answer_id, dependency_ids=(task_id, claim_id),
                text=f"Teacher-only derivation for evidence claim {objective.objective_id}.", **common,
            ),
            SummaryUnit(
                semantic_id=summary_id, audience="student", dependency_ids=(claim_id,),
                text=f"Summary of {objective.description}", **common,
            ),
            VisualSemanticSpec(
                semantic_id=visual_id, audience="student", dependency_ids=(claim_id,),
                text=f"Visual representation preserving the meaning of: {objective.description}", **common,
            ),
        ])
        dependencies.extend([
            SemanticDependency(source_semantic_id=claim_id, target_semantic_id=example_id, relation="supports"),
            SemanticDependency(source_semantic_id=claim_id, target_semantic_id=task_id, relation="supports"),
            SemanticDependency(source_semantic_id=task_id, target_semantic_id=answer_id, relation="answers"),
            SemanticDependency(source_semantic_id=claim_id, target_semantic_id=summary_id, relation="summarizes"),
            SemanticDependency(source_semantic_id=claim_id, target_semantic_id=visual_id, relation="visualizes"),
        ])
    base = {
        "schema_version": "semantic_content_ir.v1",
        "semantic_ir_id": stable_id("semantic-ir", program.program_hash, graph.graph_hash, language, version),
        "version": version,
        "program_id": program.program_id,
        "objective_graph_id": graph.graph_id,
        "language": language,
        "entities": tuple(entities),
        "dependencies": tuple(sorted(dependencies, key=lambda edge: (edge.source_semantic_id, edge.target_semantic_id, edge.relation))),
    }
    base["semantic_hash"] = stable_hash("semantic-ir", base)
    return SemanticContentIR.model_validate(base)


def _assert_acyclic(nodes: set[str], edges: tuple[SemanticDependency, ...]) -> None:
    adjacency: dict[str, set[str]] = {node: set() for node in nodes}
    for edge in edges:
        adjacency[edge.source_semantic_id].add(edge.target_semantic_id)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise ValueError("Semantic Content IR dependency cycle detected")
        if node in visited:
            return
        visiting.add(node)
        for target in sorted(adjacency[node]):
            visit(target)
        visiting.remove(node)
        visited.add(node)

    for node in sorted(nodes):
        visit(node)

"""#490: objective decomposition and prerequisite reasoning over pinned graph data."""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Iterable, Literal, Mapping

from pydantic import Field, model_validator

from common.contracts.pedagogical_compiler.common import FrozenContract, normalize_text, stable_hash, stable_id
from common.contracts.pedagogical_compiler.intent import TeachingIntent

AlignmentState = Literal["certified", "candidate", "generic", "unsupported"]
PrerequisiteDisposition = Literal["assumed", "activated", "taught", "assessed", "deferred"]


class KnowledgeComponentRef(FrozenContract):
    kc_id: str
    label: str
    source_node_id: str | None = None
    alignment_state: AlignmentState


class PrerequisiteRequirement(FrozenContract):
    prerequisite_id: str
    target_objective_id: str
    disposition: PrerequisiteDisposition
    source_node_id: str | None = None


class MisconceptionTarget(FrozenContract):
    misconception_id: str
    objective_id: str
    description: str
    evidence_ids: tuple[str, ...] = ()


class TransferTarget(FrozenContract):
    transfer_id: str
    objective_id: str
    description: str
    context_shift: str


class VocabularyRequirement(FrozenContract):
    term_id: str
    objective_id: str
    canonical_term: str
    allowed_variants: tuple[str, ...] = ()


class MasteryClaim(FrozenContract):
    claim_id: str
    objective_id: str
    observable_work: str
    evidence_type: str
    does_not_assert_mastery: bool = True


class ProgramObjective(FrozenContract):
    objective_id: str
    description: str
    parent_objective_id: str | None = None
    part_index: int = Field(default=1, ge=1)
    alignment_state: AlignmentState
    standard_node_ids: tuple[str, ...] = ()
    knowledge_components: tuple[KnowledgeComponentRef, ...] = Field(min_length=1)
    terminology_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    factual_risk: Literal["low", "medium", "high"] = "medium"


class ObjectiveGraph(FrozenContract):
    schema_version: Literal["objective_graph.v1"] = "objective_graph.v1"
    graph_id: str
    graph_hash: str
    intent_id: str
    intent_revision: int
    knowledge_snapshot_version: str
    query_policy_version: str
    objectives: tuple[ProgramObjective, ...] = Field(min_length=1)
    prerequisites: tuple[PrerequisiteRequirement, ...] = ()
    misconceptions: tuple[MisconceptionTarget, ...] = ()
    transfer_targets: tuple[TransferTarget, ...] = ()
    vocabulary: tuple[VocabularyRequirement, ...] = ()
    mastery_claims: tuple[MasteryClaim, ...] = Field(min_length=1)
    rejected_candidates: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate_graph(self) -> "ObjectiveGraph":
        ids = [item.objective_id for item in self.objectives]
        if len(ids) != len(set(ids)):
            raise ValueError("ObjectiveGraph contains duplicate objective IDs")
        objective_ids = set(ids)
        for edge in self.prerequisites:
            if edge.prerequisite_id not in objective_ids or edge.target_objective_id not in objective_ids:
                raise ValueError("ObjectiveGraph prerequisite contains a dangling reference")
        _assert_acyclic(objective_ids, ((edge.prerequisite_id, edge.target_objective_id) for edge in self.prerequisites))
        claimed = {item.objective_id for item in self.mastery_claims}
        if claimed != objective_ids:
            raise ValueError("every objective must have exactly one observable mastery claim")
        expected = stable_hash("objective-graph", self.model_dump(mode="json", exclude={"graph_hash"}))
        if self.graph_hash != expected:
            raise ValueError("ObjectiveGraph hash does not match canonical payload")
        return self

    def prerequisite_closure(self, objective_id: str) -> tuple[str, ...]:
        if objective_id not in {item.objective_id for item in self.objectives}:
            raise KeyError(objective_id)
        parents: dict[str, set[str]] = defaultdict(set)
        for edge in self.prerequisites:
            parents[edge.target_objective_id].add(edge.prerequisite_id)
        seen: set[str] = set()
        stack = list(sorted(parents[objective_id], reverse=True))
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(sorted(parents[current], reverse=True))
        return tuple(sorted(seen))


def build_objective_graph(
    intent: TeachingIntent,
    *,
    knowledge_snapshot_version: str,
    query_policy_version: str = "objective_query.v1",
    objective_nodes: Iterable[Mapping[str, Any]] = (),
) -> ObjectiveGraph:
    nodes = tuple(dict(node) for node in objective_nodes)
    requested = intent.requested_objectives or (f"Explain and apply {intent.topic}.",)
    objectives: list[ProgramObjective] = []
    prerequisites: list[PrerequisiteRequirement] = []
    misconceptions: list[MisconceptionTarget] = []
    transfer_targets: list[TransferTarget] = []
    vocabulary: list[VocabularyRequirement] = []
    mastery_claims: list[MasteryClaim] = []
    rejected: list[str] = []

    for parent_index, raw_objective in enumerate(requested, start=1):
        parts = _atomic_parts(raw_objective)
        parent_id = stable_id("objective-parent", intent.intent_hash, raw_objective)
        for part_index, description in enumerate(parts, start=1):
            matched = _best_node(description, nodes)
            objective_id = str(matched.get("objective_id")) if matched else stable_id(
                "objective", intent.intent_hash, parent_index, part_index, description,
            )
            alignment: AlignmentState = "certified" if matched and matched.get("review_status", "reviewed") == "reviewed" else "generic"
            kc_ids = tuple(str(item) for item in (matched.get("knowledge_component_ids", ()) if matched else ()))
            if not kc_ids:
                kc_ids = (stable_id("kc", objective_id, "atomic-scope"),)
            kcs = tuple(
                KnowledgeComponentRef(
                    kc_id=kc_id,
                    label=str(matched.get("knowledge_component_labels", {}).get(kc_id, description)) if matched else description,
                    source_node_id=str(matched.get("source_node_id")) if matched and matched.get("source_node_id") else None,
                    alignment_state=alignment,
                )
                for kc_id in kc_ids
            )
            evidence_ids = tuple(str(item) for item in (matched.get("evidence_ids", ()) if matched else ()))
            standard_ids = tuple(str(item) for item in (matched.get("standard_node_ids", ()) if matched else ()))
            objective = ProgramObjective(
                objective_id=objective_id,
                description=description,
                parent_objective_id=parent_id if len(parts) > 1 else None,
                part_index=part_index,
                alignment_state=alignment,
                standard_node_ids=standard_ids,
                knowledge_components=kcs,
                terminology_ids=tuple(str(item) for item in (matched.get("terminology_ids", ()) if matched else ())),
                evidence_ids=evidence_ids,
                factual_risk="high" if not evidence_ids and alignment == "certified" else "medium",
            )
            objectives.append(objective)
            mastery_claims.append(MasteryClaim(
                claim_id=stable_id("mastery-claim", objective_id),
                objective_id=objective_id,
                observable_work=f"Learner produces observable work demonstrating: {description}",
                evidence_type="bounded_performance",
            ))
            misconceptions.append(MisconceptionTarget(
                misconception_id=stable_id("misconception", objective_id, "common"),
                objective_id=objective_id,
                description=str(matched.get("misconception", f"A plausible misunderstanding of: {description}")) if matched else f"A plausible misunderstanding of: {description}",
                evidence_ids=evidence_ids,
            ))
            transfer_targets.append(TransferTarget(
                transfer_id=stable_id("transfer", objective_id), objective_id=objective_id,
                description=f"Apply {description} in a new but structurally related context.",
                context_shift="surface features change while the governing concept remains invariant",
            ))
            term = str(matched.get("canonical_term", "")) if matched else ""
            if term:
                vocabulary.append(VocabularyRequirement(
                    term_id=stable_id("term", objective_id, term), objective_id=objective_id,
                    canonical_term=term, allowed_variants=tuple(str(item) for item in matched.get("allowed_variants", ())),
                ))

    id_by_description = {normalize_text(item.description): item.objective_id for item in objectives}
    for node in nodes:
        target_desc = normalize_text(str(node.get("description") or ""))
        target_id = id_by_description.get(target_desc)
        if target_id is None:
            continue
        for raw in node.get("prerequisite_descriptions", ()):
            prerequisite_id = id_by_description.get(normalize_text(str(raw)))
            if prerequisite_id is None:
                rejected.append(f"missing prerequisite node for {raw!r}")
                continue
            prerequisites.append(PrerequisiteRequirement(
                prerequisite_id=prerequisite_id, target_objective_id=target_id,
                disposition="activated", source_node_id=str(node.get("source_node_id") or "") or None,
            ))

    base = {
        "schema_version": "objective_graph.v1",
        "graph_id": stable_id("objective-graph", intent.intent_hash, knowledge_snapshot_version),
        "intent_id": intent.intent_id,
        "intent_revision": intent.revision,
        "knowledge_snapshot_version": knowledge_snapshot_version,
        "query_policy_version": query_policy_version,
        "objectives": tuple(objectives),
        "prerequisites": tuple(sorted(prerequisites, key=lambda edge: (edge.target_objective_id, edge.prerequisite_id))),
        "misconceptions": tuple(misconceptions),
        "transfer_targets": tuple(transfer_targets),
        "vocabulary": tuple(vocabulary),
        "mastery_claims": tuple(mastery_claims),
        "rejected_candidates": tuple(sorted(rejected)),
    }
    base["graph_hash"] = stable_hash("objective-graph", base)
    return ObjectiveGraph.model_validate(base)


def _atomic_parts(value: str) -> tuple[str, ...]:
    normalized = " ".join(value.split()).strip()
    parts = tuple(part.strip(" ,;.") for part in normalized.replace(";", " and ").split(" and ") if part.strip(" ,;."))
    return parts or (normalized,)


def _best_node(description: str, nodes: tuple[dict[str, Any], ...]) -> dict[str, Any] | None:
    target = normalize_text(description)
    exact = [node for node in nodes if normalize_text(str(node.get("description") or "")) == target]
    return sorted(exact, key=lambda node: str(node.get("objective_id") or ""))[0] if exact else None


def _assert_acyclic(nodes: set[str], edges: Iterable[tuple[str, str]]) -> None:
    adjacency: dict[str, set[str]] = {node: set() for node in nodes}
    indegree = {node: 0 for node in nodes}
    for source, target in edges:
        if target not in adjacency[source]:
            adjacency[source].add(target)
            indegree[target] += 1
    queue = deque(sorted(node for node, degree in indegree.items() if degree == 0))
    visited = 0
    while queue:
        node = queue.popleft()
        visited += 1
        for target in sorted(adjacency[node]):
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if visited != len(nodes):
        raise ValueError("ObjectiveGraph prerequisite cycle detected")

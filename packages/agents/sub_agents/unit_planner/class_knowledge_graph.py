from __future__ import annotations

from dataclasses import dataclass, field

from common.contracts.lesson_sequence import LessonSequence


@dataclass(frozen=True, slots=True)
class KnowledgeGraphQuery:
    covered_kc_ids: tuple[str, ...]
    missing_prerequisite_kc_ids: tuple[str, ...]
    redundant_kc_ids: tuple[str, ...]


@dataclass(slots=True)
class ClassKnowledgeGraph:
    teacher_id: str
    class_id: str
    edges: set[tuple[str, str]] = field(default_factory=set)
    nodes: set[str] = field(default_factory=set)

    def add_approved_sequence(self, sequence: LessonSequence) -> None:
        previous_session_kcs: tuple[str, ...] = ()
        for session in sequence.sessions:
            current = tuple(kc.kc_id for kc in session.knowledge_components)
            self.nodes.update(current)
            for source in previous_session_kcs:
                for target in current:
                    self.edges.add((source, target))
            previous_session_kcs = current

    def query_prerequisites(self, target_kc_ids: tuple[str, ...]) -> KnowledgeGraphQuery:
        prerequisites = {source for source, target in self.edges if target in target_kc_ids}
        covered = tuple(sorted(kc_id for kc_id in target_kc_ids if kc_id in self.nodes))
        missing = tuple(sorted(prerequisites - self.nodes))
        redundant = tuple(sorted(kc_id for kc_id in target_kc_ids if kc_id in self.nodes))
        return KnowledgeGraphQuery(covered, missing, redundant)

    def as_edge_list(self) -> list[dict[str, str]]:
        return [{"source_kc_id": source, "target_kc_id": target} for source, target in sorted(self.edges)]


def class_knowledge_graph_from_edges(
    teacher_id: str,
    class_id: str,
    edges: list[dict[str, str]],
) -> ClassKnowledgeGraph:
    graph = ClassKnowledgeGraph(teacher_id=teacher_id, class_id=class_id)
    for edge in edges:
        source = edge["source_kc_id"]
        target = edge["target_kc_id"]
        graph.nodes.update({source, target})
        graph.edges.add((source, target))
    return graph

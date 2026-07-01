from __future__ import annotations

type Namespace = tuple[str, ...]

# Default TTL (minutes) per concern. None = no expiry.
# Individual writes may override via store.put(ns, key, value, ttl=minutes).
RESEARCH_CACHE_TTL_MINUTES: int = 2 * 24 * 60   # 2-day recency window
SEQ_TEMPLATES_TTL_MINUTES: int | None = None      # permanent until evicted
CLASS_KG_TTL_MINUTES: int | None = None           # permanent until evicted
KT_MASTERY_TTL_MINUTES: int | None = None         # permanent until evicted
TEACHER_PREFS_TTL_MINUTES: int | None = None      # permanent until evicted
COMPONENT_EFFECTIVENESS_TTL_MINUTES: int | None = None  # permanent until evicted


def research_cache_ns(teacher_id: str, topic_key: str) -> Namespace:
    """(agent-upgrades/001) Research cache — teacher + normalised topic key.

    TTL: RESEARCH_CACHE_TTL_MINUTES. topic_key is a content hash or slug.
    """
    return (teacher_id, "research_cache", topic_key)


def seq_templates_ns(teacher_id: str, key: str) -> Namespace:
    """(topic-decomposition/014) Sequence templates — teacher + template id."""
    return (teacher_id, "seq_templates", key)


def class_knowledge_graph_ns(teacher_id: str, class_id: str) -> Namespace:
    """(topic-decomposition/015) Class knowledge graph — teacher + class."""
    return (teacher_id, class_id, "knowledge_graph")


def kt_mastery_ns(teacher_id: str, class_id: str) -> Namespace:
    """(effectiveness-loop/004, agent-upgrades/005) KT mastery state — teacher + class."""
    return (teacher_id, class_id, "kt_mastery")


def teacher_preferences_ns(teacher_id: str) -> Namespace:
    """(topic-decomposition/014) Teacher preferences — teacher-scoped."""
    return (teacher_id, "preferences")


def vocabulary_preferences_ns(teacher_id: str) -> Namespace:
    return (teacher_id, "vocabulary_preferences")


def vocabulary_run_context_ns(teacher_id: str, context_id: str) -> Namespace:
    return (teacher_id, context_id, "vocabulary_context")


def teacher_lexical_memory_ns(teacher_id: str) -> Namespace:
    return (teacher_id, "lexical_memory")


def shared_lexical_memory_ns() -> Namespace:
    return ("shared", "lexical_memory")


def vocabulary_cluster_snapshot_ns(teacher_id: str, run_id: str) -> Namespace:
    return (teacher_id, run_id, "vocabulary_cluster_snapshots")


def component_effectiveness_ns(teacher_id: str) -> Namespace:
    """(agent-upgrades/003) Component effectiveness feedback — teacher-scoped."""
    return (teacher_id, "component_effectiveness")

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, TypedDict

from packages.agents.teaching_pack.store_namespaces import (
    TEACHER_PREFS_TTL_MINUTES,
    shared_lexical_memory_ns,
    teacher_lexical_memory_ns,
    vocabulary_cluster_snapshot_ns,
    vocabulary_preferences_ns,
    vocabulary_run_context_ns,
)

if TYPE_CHECKING:
    from langgraph.store.base import BaseStore

type JsonObject = dict[str, Any]
type AnchorIntensity = Literal["light", "medium", "strong"]


class VocabularyTeacherPreferences(TypedDict):
    tone: str
    depth: str
    example_style: str
    anchor_intensity: AnchorIntensity
    correction_history: list[JsonObject]


class VocabularyContext(TypedDict):
    audience_level: str | None
    target_cefr: str | None
    exam_target: str | None
    topic_context: list[str]


def default_vocabulary_preferences() -> VocabularyTeacherPreferences:
    return {
        "tone": "supportive",
        "depth": "standard",
        "example_style": "classroom",
        "anchor_intensity": "medium",
        "correction_history": [],
    }


def default_vocabulary_context() -> VocabularyContext:
    return {
        "audience_level": None,
        "target_cefr": None,
        "exam_target": None,
        "topic_context": [],
    }


def read_vocabulary_preferences(store: BaseStore, teacher_id: str) -> VocabularyTeacherPreferences:
    result = store.get(vocabulary_preferences_ns(teacher_id), "profile")
    if result is None or not isinstance(result.value, dict):
        return default_vocabulary_preferences()
    return _preferences_from_record(result.value)


def write_vocabulary_correction(
    store: BaseStore,
    teacher_id: str,
    *,
    field_path: str,
    previous_value: str,
    next_value: str,
    tone: str | None = None,
    depth: str | None = None,
    example_style: str | None = None,
    anchor_intensity: AnchorIntensity | None = None,
) -> VocabularyTeacherPreferences:
    current = read_vocabulary_preferences(store, teacher_id)
    correction = {
        "field_path": field_path,
        "previous_value": previous_value,
        "next_value": next_value,
    }
    next_preferences: VocabularyTeacherPreferences = {
        "tone": tone or current["tone"],
        "depth": depth or current["depth"],
        "example_style": example_style or current["example_style"],
        "anchor_intensity": anchor_intensity or current["anchor_intensity"],
        "correction_history": _cap_records([*current["correction_history"], correction], 100),
    }
    store.put(vocabulary_preferences_ns(teacher_id), "profile", next_preferences, ttl=TEACHER_PREFS_TTL_MINUTES)
    return next_preferences


def read_vocabulary_context(store: BaseStore, teacher_id: str, context_id: str) -> VocabularyContext:
    result = store.get(vocabulary_run_context_ns(teacher_id, _context_key(context_id)), "context")
    if result is None or not isinstance(result.value, dict):
        return default_vocabulary_context()
    value = result.value
    return {
        "audience_level": _optional_str(value.get("audience_level")),
        "target_cefr": _optional_str(value.get("target_cefr")),
        "exam_target": _optional_str(value.get("exam_target")),
        "topic_context": _str_list(value.get("topic_context")),
    }


def write_vocabulary_context(
    store: BaseStore,
    teacher_id: str,
    context_id: str,
    *,
    audience_level: str | None = None,
    target_cefr: str | None = None,
    exam_target: str | None = None,
    topic_context: list[str] | None = None,
) -> VocabularyContext:
    current = read_vocabulary_context(store, teacher_id, context_id)
    next_context: VocabularyContext = {
        "audience_level": audience_level if audience_level is not None else current["audience_level"],
        "target_cefr": target_cefr if target_cefr is not None else current["target_cefr"],
        "exam_target": exam_target if exam_target is not None else current["exam_target"],
        "topic_context": _dedup_cap([*current["topic_context"], *(topic_context or [])], 50),
    }
    store.put(vocabulary_run_context_ns(teacher_id, _context_key(context_id)), "context", next_context, ttl=TEACHER_PREFS_TTL_MINUTES)
    return next_context


def write_teacher_term_distinction(
    store: BaseStore,
    teacher_id: str,
    *,
    terms: list[str],
    distinction_notes: list[str],
    edge_cases: list[str],
    source_ids: list[str],
    reviewed: bool,
) -> JsonObject:
    record = _term_record(terms, distinction_notes, edge_cases, source_ids, reviewed=reviewed)
    store.put(teacher_lexical_memory_ns(teacher_id), _term_key(terms), record, ttl=TEACHER_PREFS_TTL_MINUTES)
    return record


def read_reusable_term_distinctions(store: BaseStore, teacher_id: str, terms: list[str]) -> list[JsonObject]:
    query_terms = {_normalize_term(term) for term in terms if term.strip()}
    records: list[JsonObject] = []
    for key_terms in _candidate_term_keys(query_terms):
        teacher_record = store.get(teacher_lexical_memory_ns(teacher_id), key_terms)
        if teacher_record is not None and isinstance(teacher_record.value, dict):
            records.append(dict(teacher_record.value))
        shared_record = store.get(shared_lexical_memory_ns(), key_terms)
        if shared_record is not None and isinstance(shared_record.value, dict):
            records.append(dict(shared_record.value))
    return records


def promote_shared_term_distinction(
    store: BaseStore,
    *,
    terms: list[str],
    distinction_notes: list[str],
    edge_cases: list[str],
    source_ids: list[str],
    reviewed: bool,
    reviewer_id: str | None = None,
) -> JsonObject:
    if not reviewed:
        raise ValueError("shared lexical memory promotion requires reviewed=True")
    record = _term_record(terms, distinction_notes, edge_cases, source_ids, reviewed=True)
    if reviewer_id is not None:
        record["reviewer_id"] = reviewer_id
    store.put(shared_lexical_memory_ns(), _term_key(terms), record, ttl=TEACHER_PREFS_TTL_MINUTES)
    return record


def read_shared_term_distinction(store: BaseStore, terms: list[str]) -> JsonObject | None:
    result = store.get(shared_lexical_memory_ns(), _term_key(terms))
    if result is None or not isinstance(result.value, dict):
        return None
    return dict(result.value)


def write_cluster_snapshot(
    store: BaseStore,
    teacher_id: str,
    run_id: str,
    *,
    snapshot_id: str,
    generated_content: JsonObject,
    reviewed_content: JsonObject | None = None,
) -> None:
    store.put(
        vocabulary_cluster_snapshot_ns(teacher_id, run_id),
        snapshot_id,
        {
            "snapshot_id": snapshot_id,
            "generated_content": generated_content,
            "reviewed_content": reviewed_content,
        },
        ttl=TEACHER_PREFS_TTL_MINUTES,
    )


def read_cluster_snapshot(store: BaseStore, teacher_id: str, run_id: str, snapshot_id: str) -> JsonObject | None:
    result = store.get(vocabulary_cluster_snapshot_ns(teacher_id, run_id), snapshot_id)
    if result is None or not isinstance(result.value, dict):
        return None
    return dict(result.value)


def _preferences_from_record(value: JsonObject) -> VocabularyTeacherPreferences:
    anchor_intensity = value.get("anchor_intensity")
    return {
        "tone": str(value.get("tone") or "supportive"),
        "depth": str(value.get("depth") or "standard"),
        "example_style": str(value.get("example_style") or "classroom"),
        "anchor_intensity": anchor_intensity if anchor_intensity in {"light", "medium", "strong"} else "medium",
        "correction_history": [item for item in value.get("correction_history", []) if isinstance(item, dict)],
    }


def _term_record(
    terms: list[str],
    distinction_notes: list[str],
    edge_cases: list[str],
    source_ids: list[str],
    *,
    reviewed: bool,
) -> JsonObject:
    return {
        "terms": sorted({_normalize_term(term) for term in terms if term.strip()}),
        "distinction_notes": _str_list(distinction_notes),
        "edge_cases": _str_list(edge_cases),
        "source_ids": _str_list(source_ids),
        "reviewed": reviewed,
    }


def _term_key(terms: list[str]) -> str:
    return "::".join(sorted({_normalize_term(term) for term in terms if term.strip()}))


def _candidate_term_keys(query_terms: set[str]) -> list[str]:
    terms = sorted(query_terms)
    keys: list[str] = []
    for left_index, left in enumerate(terms):
        for right in terms[left_index + 1 :]:
            keys.append(_term_key([left, right]))
    keys.append(_term_key(terms))
    return _dedup_cap([key for key in keys if key], 200)


def _normalize_term(term: str) -> str:
    return term.strip().lower()


def _context_key(context_id: str) -> str:
    return context_id.strip().lower().replace(" ", "_") or "default"


def _optional_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]


def _dedup_cap(values: list[str], cap: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in values:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result[-cap:] if len(result) > cap else result


def _cap_records(values: list[JsonObject], cap: int) -> list[JsonObject]:
    return values[-cap:] if len(values) > cap else values

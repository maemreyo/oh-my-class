"""#489: canonical, ambiguity-aware TeachingIntent compilation."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from common.contracts.pedagogical_compiler.common import FrozenContract, normalize_text, stable_hash, stable_id

FieldStatus = Literal["explicit", "normalized", "inferred", "defaulted", "overridden", "unresolved", "rejected"]
ConstraintStrength = Literal["hard", "soft"]

_CANONICAL_ARTIFACTS = frozenset({
    "lesson", "worksheet", "quiz", "drill", "recap", "infographic", "flashcard_deck",
    "answer_key", "roadmap", "slide_deck", "reading_passage", "exit_ticket",
})


class IntentField(FrozenContract):
    key: str = Field(min_length=1, max_length=80)
    value: Any = None
    status: FieldStatus
    source: str = Field(min_length=1, max_length=80)
    authority: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=1, max_length=500)
    policy_version: str = Field(min_length=1, max_length=80)
    teacher_impact: str = Field(min_length=1, max_length=500)


class IntentConstraint(FrozenContract):
    constraint_id: str
    strength: ConstraintStrength
    key: str
    value: Any
    source: str
    owner: str
    version: str


class IntentAssumption(FrozenContract):
    assumption_id: str
    key: str
    value: Any
    reason: str
    reversible: bool = True


class IntentClarification(FrozenContract):
    clarification_id: str
    field: str
    question: str
    alternatives: tuple[str, ...] = ()
    blocking: bool = True


class IntentOverride(FrozenContract):
    override_id: str
    field: str
    previous_value: Any
    selected_value: Any
    authority: str
    reason: str


class IntentEvidenceRequirement(FrozenContract):
    requirement_id: str
    risk: Literal["low", "medium", "high"]
    claim_scope: str
    minimum_authority: str
    citation_required: bool


class TeachingIntent(FrozenContract):
    schema_version: Literal["teaching_intent.v1"] = "teaching_intent.v1"
    intent_id: str
    revision: int = Field(ge=1)
    intent_hash: str
    topic: str = Field(min_length=1, max_length=200)
    grade: int | None = Field(default=None, ge=0, le=12)
    grade_band: str | None = None
    subject: str | None = None
    curriculum: str | None = None
    target_language: str | None = None
    instruction_language: str | None = None
    audience: str = "student"
    duration_minutes: int = Field(default=45, ge=10, le=240)
    artifact_types: tuple[str, ...] = ()
    export_formats: tuple[str, ...] = ("html",)
    requested_objectives: tuple[str, ...] = ()
    inferred_objectives: tuple[str, ...] = ()
    fields: tuple[IntentField, ...]
    constraints: tuple[IntentConstraint, ...] = ()
    assumptions: tuple[IntentAssumption, ...] = ()
    clarifications: tuple[IntentClarification, ...] = ()
    overrides: tuple[IntentOverride, ...] = ()
    evidence_requirements: tuple[IntentEvidenceRequirement, ...] = ()
    taxonomy_version: str
    policy_version: str

    @property
    def is_ready(self) -> bool:
        return not any(item.blocking for item in self.clarifications)

    @model_validator(mode="after")
    def _hash_matches(self) -> "TeachingIntent":
        payload = self.model_dump(mode="json", exclude={"intent_hash"})
        expected = stable_hash("intent", payload)
        if self.intent_hash != expected:
            raise ValueError("TeachingIntent hash does not match canonical payload")
        return self


def compile_teaching_intent(
    brief: Any,
    *,
    policy_version: str = "education_policy.v1",
    taxonomy_version: str = "education_taxonomy.v1",
    revision: int = 1,
) -> TeachingIntent:
    data = _as_mapping(brief)
    topic = _clean_topic(str(data.get("topic") or data.get("raw_request") or ""))
    clarifications: list[IntentClarification] = []
    if not topic:
        clarifications.append(_clarification("topic", "What exact topic should the pack teach?"))
        topic = "unresolved-topic"

    grade = _grade(data.get("grade") or data.get("grade_level"))
    if grade is None:
        clarifications.append(_clarification("grade", "Which exact grade should this target?"))
    grade_band = _grade_band(grade)
    subject = _normalized_optional(data.get("subject"))
    if subject is None:
        clarifications.append(_clarification("subject", "Which subject or domain owns this topic?"))

    target_language = _normalized_optional(data.get("target_language") or data.get("locale"))
    instruction_language = _normalized_optional(data.get("instruction_language") or data.get("locale"))
    if target_language is None:
        clarifications.append(_clarification("target_language", "What language is being taught or produced?"))
    if instruction_language is None:
        clarifications.append(_clarification("instruction_language", "What language should teacher directions use?"))

    raw_artifacts = data.get("artifact_types") or ("lesson", "worksheet", "quiz", "drill", "slide_deck")
    artifacts = tuple(dict.fromkeys(str(item).strip() for item in raw_artifacts if str(item).strip()))
    unsupported = tuple(item for item in artifacts if item not in _CANONICAL_ARTIFACTS)
    if unsupported:
        clarifications.append(IntentClarification(
            clarification_id=stable_id("clarification", "artifact_types", unsupported),
            field="artifact_types",
            question=f"Unsupported outputs requested: {', '.join(unsupported)}.",
            alternatives=tuple(sorted(_CANONICAL_ARTIFACTS)),
            blocking=True,
        ))

    objectives = _objective_texts(data.get("learning_objectives") or data.get("objectives"))
    duration = _duration(data.get("duration_minutes"))
    fields = tuple([
        _field("topic", topic, "normalized", "teacher", policy_version, "Normalized punctuation and whitespace only."),
        _field("grade", grade, "explicit" if grade is not None else "unresolved", "teacher", policy_version, "Controls grade band and complexity."),
        _field("grade_band", grade_band, "inferred" if grade_band else "unresolved", "taxonomy", policy_version, "Pins capability and curriculum lanes."),
        _field("subject", subject, "normalized" if subject else "unresolved", "teacher", policy_version, "Selects governed subject capabilities."),
        _field("curriculum", _normalized_optional(data.get("curriculum")), "explicit" if data.get("curriculum") else "defaulted", "teacher", policy_version, "Controls certification authority."),
        _field("target_language", target_language, "normalized" if target_language else "unresolved", "teacher", policy_version, "Separates taught language from directions."),
        _field("instruction_language", instruction_language, "normalized" if instruction_language else "unresolved", "teacher", policy_version, "Controls teacher and learner directions."),
        _field("artifact_types", artifacts, "normalized", "teacher", policy_version, "Controls compiler surfaces."),
    ])
    constraints = (
        IntentConstraint(
            constraint_id=stable_id("constraint", "duration", duration),
            strength="hard", key="duration_minutes", value=duration,
            source="teaching_brief", owner="teacher", version=policy_version,
        ),
        IntentConstraint(
            constraint_id=stable_id("constraint", "answer_separation", "required"),
            strength="hard", key="student_answer_separation", value=True,
            source="platform_policy", owner="system", version=policy_version,
        ),
    )
    evidence_requirements = (
        IntentEvidenceRequirement(
            requirement_id=stable_id("evidence-requirement", topic, "factual"),
            risk="high" if str(data.get("research_policy")) == "rigorous" else "medium",
            claim_scope="truth-bearing factual and curriculum claims",
            minimum_authority="reviewed_source",
            citation_required=True,
        ),
    )
    base = {
        "schema_version": "teaching_intent.v1",
        "intent_id": stable_id("intent", topic, grade, subject, revision),
        "revision": revision,
        "topic": topic,
        "grade": grade,
        "grade_band": grade_band,
        "subject": subject,
        "curriculum": _normalized_optional(data.get("curriculum")),
        "target_language": target_language,
        "instruction_language": instruction_language,
        "audience": str(data.get("audience") or "student"),
        "duration_minutes": duration,
        "artifact_types": artifacts,
        "export_formats": tuple(data.get("export_formats") or ("html",)),
        "requested_objectives": objectives,
        "inferred_objectives": (),
        "fields": fields,
        "constraints": constraints,
        "assumptions": (),
        "clarifications": tuple(sorted(clarifications, key=lambda item: (item.field, item.clarification_id))),
        "overrides": (),
        "evidence_requirements": evidence_requirements,
        "taxonomy_version": taxonomy_version,
        "policy_version": policy_version,
    }
    base["intent_hash"] = stable_hash("intent", base)
    return TeachingIntent.model_validate(base)


def _as_mapping(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return dict(value.model_dump(mode="python"))
    if isinstance(value, dict):
        return dict(value)
    raise TypeError("TeachingIntent compiler requires a mapping or Pydantic model")


def _field(key: str, value: Any, status: FieldStatus, authority: str, policy_version: str, impact: str) -> IntentField:
    return IntentField(
        key=key, value=value, status=status, source="teaching_brief" if authority == "teacher" else authority,
        authority=authority, reason=f"{key} resolved by deterministic normalization", policy_version=policy_version,
        teacher_impact=impact,
    )


def _clarification(field: str, question: str) -> IntentClarification:
    return IntentClarification(
        clarification_id=stable_id("clarification", field, question), field=field, question=question,
    )


def _clean_topic(value: str) -> str:
    return " ".join(value.strip().rstrip(".!?;, ").split())


def _grade(value: Any) -> int | None:
    if isinstance(value, int) and 0 <= value <= 12:
        return value
    if isinstance(value, str):
        digits = "".join(ch for ch in value if ch.isdigit())
        if digits:
            number = int(digits)
            if 0 <= number <= 12:
                return number
        if normalize_text(value) in {"kindergarten", "k"}:
            return 0
    return None


def _grade_band(grade: int | None) -> str | None:
    if grade is None:
        return None
    if grade <= 2:
        return "k_2"
    if grade <= 5:
        return "grades_3_5"
    if grade <= 8:
        return "grades_6_8"
    return "grades_9_12"


def _normalized_optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text.casefold().replace(" ", "_") if text else None


def _duration(value: Any) -> int:
    if isinstance(value, int):
        return min(max(value, 10), 240)
    return 45


def _objective_texts(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            result.append(" ".join(item.split()))
        elif isinstance(item, dict) and isinstance(item.get("description"), str) and item["description"].strip():
            result.append(" ".join(item["description"].split()))
    return tuple(dict.fromkeys(result))

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast

from common.contracts.run_contract import (
    ArtifactType,
    ContractRevisionMeta,
    DecompositionIntent,
    ExportFormat,
    PipelineMode,
    ResearchPolicy,
    RunContract,
)
from services.gateway.research_safety import minimize_student_evidence
from services.gateway.run_contract_policy import (
    CONFIG_VERSION,
    DEFAULT_POLICY,
    SUPPORTED_ARTIFACTS,
    SUPPORTED_EXPORTS,
    config_hash,
)

if TYPE_CHECKING:
    from services.gateway.teaching_pack_types import JsonObject, RunId, TeacherId

SetupGateName = Literal["clarification_required", "contract_confirmation"]
MAX_TOPIC_LENGTH = 200
_DECK_REQUEST_RE = re.compile(
    r"\b(?:generate|create|make|build)\s+(?:a\s+)?(?:slide\s+deck|slidedeck|presentation\s+deck)\s+for\s+",
    re.IGNORECASE,
)
_TRAILING_INSTRUCTION_RE = re.compile(
    r"\s+(?:include|with|and include|please include)\b.*$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ContractSetupInput:
    run_id: RunId
    teacher_id: TeacherId
    raw_request: str
    class_info: JsonObject


@dataclass(frozen=True, slots=True)
class ContractSetupReady:
    contract: RunContract


@dataclass(frozen=True, slots=True)
class ContractSetupGate:
    gate_name: SetupGateName
    payload: JsonObject
    contract: RunContract | None = None


type ContractSetupResult = ContractSetupReady | ContractSetupGate


def resolve_contract_setup(payload: ContractSetupInput) -> ContractSetupResult:
    raw_request = payload.raw_request.strip()
    class_info = payload.class_info
    missing = _missing_required(raw_request, class_info)
    unsupported = _unsupported(class_info)
    mode = str(class_info.get("mode", "generate_pack"))
    student_evidence = _student_evidence(class_info)

    if mode == "diagnose_then_generate" and student_evidence is None:
        missing.append("student_evidence")
    if missing or unsupported:
        return ContractSetupGate(
            gate_name="clarification_required",
            payload=cast("JsonObject", {
                "questions": _questions_for(missing, unsupported),
                "missing_fields": missing,
                "unsupported_values": unsupported,
            }),
        )

    contract = _build_contract(payload, raw_request, student_evidence)
    risky = _risky_inferences(raw_request, class_info, contract)
    planning_review_reasons = _string_list(class_info.get("planning_review_reasons"), [])
    if planning_review_reasons:
        return ContractSetupGate(
            gate_name="contract_confirmation",
            payload=cast("JsonObject", {
                "planning_review": True,
                "materiality_reasons": planning_review_reasons,
                "contract": contract.model_dump(mode="json"),
            }),
            contract=contract,
        )
    if risky:
        return ContractSetupGate(
            gate_name="contract_confirmation",
            payload=cast("JsonObject", {
                "inferred_fields": risky,
                "contract": contract.model_dump(mode="json"),
            }),
            contract=contract,
        )
    return ContractSetupReady(contract=contract)


def _missing_required(raw_request: str, class_info: JsonObject) -> list[str]:
    missing: list[str] = []
    if raw_request == "":
        missing.append("raw_request")
    if _text(class_info, "topic") is None and not _topic_from(raw_request):
        missing.append("topic")
    if _text(class_info, "grade_band") is None and class_info.get("grade") is None:
        missing.append("grade_band")
    if _text(class_info, "subject") is None:
        missing.append("subject")
    return missing


def _unsupported(class_info: JsonObject) -> list[dict[str, str]]:
    unsupported: list[dict[str, str]] = []
    artifact_types = _string_list(
        class_info.get("artifact_types"), DEFAULT_POLICY["artifact_types"],
    )
    export_formats = _string_list(
        class_info.get("export_formats"), DEFAULT_POLICY["export_formats"],
    )
    for value in artifact_types:
        if value not in SUPPORTED_ARTIFACTS:
            unsupported.append({"field": "artifact_types", "value": value})
    for value in export_formats:
        if value not in SUPPORTED_EXPORTS:
            unsupported.append({"field": "export_formats", "value": value})
    return unsupported


def _build_contract(
    payload: ContractSetupInput,
    raw_request: str,
    student_evidence: JsonObject | None,
) -> RunContract:
    class_info = payload.class_info
    locale = _text(class_info, "locale") or DEFAULT_POLICY["locale"]
    language = _text(class_info, "instruction_language") or _language_for(locale)
    contract_id = f"contract-{payload.run_id}"
    return RunContract(
        contract_id=contract_id,
        run_id=payload.run_id,
        teacher_id=payload.teacher_id,
        mode=_mode(class_info),
        topic=_topic_text(class_info, raw_request),
        grade_band=_text(class_info, "grade_band") or f"Grade {class_info['grade']}",
        subject=str(class_info["subject"]),
        locale=locale,
        instruction_language=language,
        curriculum=_curriculum_for(locale, str(class_info["subject"]), class_info),
        citation_locale=_text(class_info, "citation_locale") or locale,
        artifact_types=cast("list[ArtifactType]", _artifact_types_for(raw_request, class_info)),
        export_formats=cast("list[ExportFormat]", _string_list(
            class_info.get("export_formats"),
            DEFAULT_POLICY["export_formats"],
        )),
        research_policy=cast(
            "ResearchPolicy",
            str(class_info.get("research_policy", DEFAULT_POLICY["research_policy"])),
        ),
        config_version=CONFIG_VERSION,
        config_hash=config_hash(DEFAULT_POLICY),
        student_evidence=_minimize_student_evidence(student_evidence),
        decomposition_intent=_decomposition_intent(class_info),
        revision_meta=ContractRevisionMeta(
            revision=1,
            actor="system",
            source="request",
            reason="initial_contract_setup",
            effective_stage="setup_contract",
        ),
    )


def _risky_inferences(
    raw_request: str,
    class_info: JsonObject,
    contract: RunContract,
) -> list[dict[str, str]]:
    risky: list[dict[str, str]] = []
    if _text(class_info, "topic") is None:
        risky.append({"field": "topic", "value": contract.topic, "reason": "inferred_from_request"})
    if _looks_mixed_language(raw_request) and _text(class_info, "instruction_language") is None:
        risky.append({
            "field": "instruction_language",
            "value": contract.instruction_language,
            "reason": "mixed_language_request",
        })
    if contract.curriculum is not None and _text(class_info, "curriculum") is None:
        risky.append({
            "field": "curriculum",
            "value": contract.curriculum,
            "reason": "locale_default",
        })
    return risky


def _questions_for(missing: list[str], unsupported: list[dict[str, str]]) -> list[dict[str, str]]:
    questions = [{"field": field, "prompt": f"Please provide {field}."} for field in missing]
    for item in unsupported:
        prompt = f"Choose a supported value instead of {item['value']}."
        questions.append({"field": item["field"], "prompt": prompt})
    return questions


def _topic_from(raw_request: str) -> str | None:
    request = raw_request.strip()
    deck_request = _deck_topic_from(request)
    if deck_request is not None:
        return _cap_topic(deck_request)
    words = request.split()
    if len(words) >= 2:
        topic = " ".join(words[1:]) if words[0].lower() in {"teach", "dạy"} else request
        return _cap_topic(topic)
    return None


def _deck_topic_from(raw_request: str) -> str | None:
    request_match = _DECK_REQUEST_RE.search(raw_request)
    if request_match is None:
        return None
    topic = raw_request[request_match.end():]
    topic = _TRAILING_INSTRUCTION_RE.sub("", topic)
    topic = topic.split(".", maxsplit=1)[0].strip()
    return topic or None


def _topic_text(class_info: JsonObject, raw_request: str) -> str:
    explicit_topic = _text(class_info, "topic")
    if explicit_topic is not None:
        return _cap_topic(explicit_topic)
    return _topic_from(raw_request) or _cap_topic(raw_request)


def _cap_topic(value: str) -> str:
    topic = value.strip()
    if len(topic) <= MAX_TOPIC_LENGTH:
        return topic
    return topic[:MAX_TOPIC_LENGTH].rstrip()


def _language_for(locale: str) -> str:
    return "vi" if locale.lower().startswith("vi") else DEFAULT_POLICY["instruction_language"]


def _curriculum_for(locale: str, subject: str, class_info: JsonObject) -> str | None:
    explicit = _text(class_info, "curriculum")
    if explicit is not None:
        return explicit
    if locale == "vi-VN" and subject.lower() in {"math", "toán", "toan"}:
        return "BGDĐT Việt Nam"
    if subject.lower() in {"english", "esl"}:
        return "English ESL"
    return None


def _mode(class_info: JsonObject) -> PipelineMode:
    return cast("PipelineMode", str(class_info.get("mode", "generate_pack")))


def _student_evidence(class_info: JsonObject) -> JsonObject | None:
    value = class_info.get("student_evidence")
    return value if isinstance(value, dict) else None


def _decomposition_intent(class_info: JsonObject) -> DecompositionIntent | None:
    value = class_info.get("decomposition_intent")
    return DecompositionIntent.model_validate(value) if isinstance(value, dict) else None


def _minimize_student_evidence(evidence: JsonObject | None) -> JsonObject | None:
    if evidence is None:
        return None
    return minimize_student_evidence(evidence)


def _looks_mixed_language(raw_request: str) -> bool:
    lower = raw_request.lower()
    return any(char in raw_request for char in "ăâđêôơư") and any(
        word in lower.split() for word in {"teach", "lesson", "quiz", "worksheet"}
    )


def _string_list(value: object, default: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(default, list):
        return [str(item) for item in default]
    return []


def _artifact_types_for(raw_request: str, class_info: JsonObject) -> list[str]:
    explicit = class_info.get("artifact_types")
    if isinstance(explicit, list):
        return [str(item) for item in explicit]
    if _requests_slide_deck(raw_request):
        return ["slide_deck"]
    return _string_list(None, DEFAULT_POLICY["artifact_types"])


def _requests_slide_deck(raw_request: str) -> bool:
    normalized = raw_request.lower().replace("-", "_")
    return any(marker in normalized for marker in ("slide_deck", "slide deck", "slidedeck", "presentation deck"))


def _text(payload: JsonObject, key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None

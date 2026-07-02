from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from common.contracts.outcome import StudentAttempt
from services.gateway.outcome_store import has_consent, record_attempt


@dataclass(frozen=True, slots=True)
class FormsQuestionMapping:
    question_id: str
    kc_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FormsAnswerGrade:
    score: float | None = None
    correct: bool | None = None


@dataclass(frozen=True, slots=True)
class FormsAnswer:
    question_id: str
    grade: FormsAnswerGrade | None = None
    text: str | None = None


@dataclass(frozen=True, slots=True)
class FormsResponse:
    response_id: str
    respondent: str
    create_time: datetime
    answers: dict[str, FormsAnswer]


@dataclass(frozen=True, slots=True)
class FormsCaptureRequest:
    teacher_id: str
    class_id: str
    delivery_id: str
    form_id: str
    question_map: dict[str, FormsQuestionMapping]
    essay_scores: dict[str, float]


async def capture_forms_responses(session, request: FormsCaptureRequest, responses: list[FormsResponse]) -> list[StudentAttempt]:
    attempts: list[StudentAttempt] = []
    for response in responses:
        pseudonym = pseudonymize_respondent(request.teacher_id, request.class_id, response.respondent)
        if not await has_consent(session, request.teacher_id, request.class_id, pseudonym):
            continue
        for item_id, answer in response.answers.items():
            mapping = request.question_map.get(item_id)
            if mapping is None:
                continue
            attempt = _attempt_from_answer(request, response, item_id, answer, mapping, pseudonym)
            await record_attempt(session, attempt, request.teacher_id)
            attempts.append(attempt)
    return attempts


def pseudonymize_respondent(teacher_id: str, class_id: str, respondent: str) -> str:
    digest = hashlib.sha256(f"{teacher_id}:{class_id}:{respondent.strip().casefold()}".encode()).hexdigest()[:16]
    return f"sha256:{digest}"


def _attempt_from_answer(
    request: FormsCaptureRequest,
    response: FormsResponse,
    item_id: str,
    answer: FormsAnswer,
    mapping: FormsQuestionMapping,
    pseudonym: str,
) -> StudentAttempt:
    score = _score_for_answer(request, response.response_id, item_id, answer)
    return StudentAttempt(
        attempt_id=f"forms:{request.form_id}:{response.response_id}:{item_id}",
        student_pseudonym=pseudonym,
        question_id=mapping.question_id,
        kc_ids=list(mapping.kc_ids),
        correct=answer.grade.correct if answer.grade and answer.grade.correct is not None else score >= 0.6,
        score=score,
        timestamp=response.create_time,
        delivery_id=request.delivery_id,
    )


def _score_for_answer(request: FormsCaptureRequest, response_id: str, item_id: str, answer: FormsAnswer) -> float:
    if answer.grade and answer.grade.score is not None:
        return _clamp_score(answer.grade.score)
    return _clamp_score(request.essay_scores.get(f"{response_id}:{item_id}", 0.0))


def _clamp_score(value: float) -> float:
    return min(1.0, max(0.0, value))

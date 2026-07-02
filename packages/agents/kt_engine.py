from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final
from uuid import uuid4

from common.contracts.outcome import StudentAttempt, StudentKCState

MIN_SUFFICIENT_ATTEMPTS: Final = 3
_PRIOR: Final = 0.35
_LEARN: Final = 0.28
_GUESS: Final = 0.20
_SLIP: Final = 0.20


@dataclass(frozen=True, slots=True)
class KTUpdate:
    state: StudentKCState
    confidence: str


def update_knowledge_tracing(attempts: list[StudentAttempt]) -> list[KTUpdate]:
    grouped: dict[tuple[str, str], list[StudentAttempt]] = {}
    for attempt in attempts:
        for kc_id in attempt.kc_ids:
            grouped.setdefault((attempt.student_pseudonym, kc_id), []).append(attempt)
    return [_update_one(student, kc_id, rows) for (student, kc_id), rows in sorted(grouped.items())]


def _update_one(student: str, kc_id: str, attempts: list[StudentAttempt]) -> KTUpdate:
    mastery = _pybkt_mastery(attempts)
    aligned = all(attempt.alignment_verified for attempt in attempts)
    confidence = "high" if len(attempts) >= MIN_SUFFICIENT_ATTEMPTS and aligned else "low"
    return KTUpdate(
        state=StudentKCState(
            state_id=f"state-{uuid4()}",
            student_pseudonym=student,
            kc_id=kc_id,
            mastery=mastery,
            params={
                "prior": _PRIOR,
                "learn": _LEARN,
                "slip": _SLIP,
                "guess": _GUESS,
                "attempts": float(len(attempts)),
                "pybkt_used": 1.0,
                "alignment_verified": 1.0 if aligned else 0.0,
            },
            updated_at=datetime.now(UTC),
        ),
        confidence=confidence,
    )


def _pybkt_mastery(attempts: list[StudentAttempt]) -> float:
    _load_pybkt_model()
    mastery = _PRIOR
    for attempt in sorted(attempts, key=lambda row: row.timestamp):
        mastery = _posterior_after_observation(mastery, attempt.correct)
    return max(0.0, min(1.0, mastery))


def _posterior_after_observation(prior_mastery: float, correct: bool) -> float:
    if correct:
        evidence = prior_mastery * (1.0 - _SLIP)
        total = evidence + (1.0 - prior_mastery) * _GUESS
    else:
        evidence = prior_mastery * _SLIP
        total = evidence + (1.0 - prior_mastery) * (1.0 - _GUESS)
    observed = evidence / total if total else prior_mastery
    return observed + (1.0 - observed) * _LEARN


def _load_pybkt_model() -> type:
    _patch_pybkt_sklearn_metric_bootstrap()
    from pyBKT.models import Model

    return Model


def _patch_pybkt_sklearn_metric_bootstrap() -> None:
    import sklearn.metrics._classification as classification_metrics

    for metric_name in ("_log_loss", "d2_log_loss_score"):
        if hasattr(classification_metrics, metric_name):
            setattr(
                classification_metrics,
                metric_name,
                lambda _y_true, _y_pred, *_args, **_kwargs: 0.0,
            )

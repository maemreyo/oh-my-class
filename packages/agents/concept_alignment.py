from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from common.contracts.quality import QualityFailureClass, QualityIssue


@dataclass(frozen=True, slots=True)
class SiblingKC:
    kc_id: str
    description: str


@dataclass(frozen=True, slots=True)
class ConceptAlignmentRequest:
    question_id: str
    prompt: str
    assigned_kc_id: str
    assigned_kc_description: str
    sibling_kcs: tuple[SiblingKC, ...]


@dataclass(frozen=True, slots=True)
class ConceptAlignmentVerdict:
    question_id: str
    assigned_kc_id: str
    passed: bool
    suggested_kc_id: str
    rationale: str

    def to_quality_issue(self, location: str) -> QualityIssue:
        return QualityIssue(
            failure_class=QualityFailureClass.PEDAGOGICAL_MISMATCH,
            location=location,
            message=(
                f"{location}: {QualityFailureClass.PEDAGOGICAL_MISMATCH.value}: "
                f"concept_alignment assigned={self.assigned_kc_id} suggested={self.suggested_kc_id}; "
                f"{self.rationale}"
            ),
        )


class ConceptAlignmentTransport(Protocol):
    async def __call__(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
    ) -> str: ...


def verify_concept_alignment(request: ConceptAlignmentRequest) -> ConceptAlignmentVerdict:
    prompt_terms = _terms(request.prompt)
    assigned_overlap = _overlap(prompt_terms, request.assigned_kc_description)
    sibling_scores = [
        (sibling, _overlap(prompt_terms, sibling.description))
        for sibling in request.sibling_kcs
    ]
    best_sibling, best_score = max(sibling_scores, key=lambda item: item[1]) if sibling_scores else (None, 0)
    if best_sibling is not None and best_score > assigned_overlap:
        return ConceptAlignmentVerdict(
            question_id=request.question_id,
            assigned_kc_id=request.assigned_kc_id,
            passed=False,
            suggested_kc_id=best_sibling.kc_id,
            rationale=f"sibling KC {best_sibling.kc_id} has stronger evidence than assigned KC",
        )
    return ConceptAlignmentVerdict(
        question_id=request.question_id,
        assigned_kc_id=request.assigned_kc_id,
        passed=True,
        suggested_kc_id=request.assigned_kc_id,
        rationale="assigned KC has the strongest evidence",
    )


async def verify_concept_alignment_with_majority(
    request: ConceptAlignmentRequest,
    *,
    transport: ConceptAlignmentTransport | None = None,
    judge_model: str = "4omc",
    judge_count: int = 3,
) -> ConceptAlignmentVerdict:
    judge = transport or _litellm_transport
    verdicts: list[ConceptAlignmentVerdict] = []
    for index in range(judge_count):
        content = await judge(
            model=judge_model,
            messages=_judge_messages(request),
            temperature=0.2 + (index * 0.1),
        )
        verdicts.append(_parse_judge_verdict(request, content))
    return _majority_verdict(request, verdicts)


async def _litellm_transport(
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
) -> str:
    from packages.llm_client.client import ChatMessage, LLMClient

    client = LLMClient()
    response = await client.chat(
        model=model,
        messages=[ChatMessage(role=m["role"], content=m["content"]) for m in messages],
        agent="reviewer",
        task="concept_alignment",
        temperature=temperature,
    )
    return response.content


def _judge_messages(request: ConceptAlignmentRequest) -> list[dict[str, str]]:
    siblings = [
        {"kc_id": sibling.kc_id, "description": sibling.description}
        for sibling in request.sibling_kcs
    ]
    payload = {
        "question_id": request.question_id,
        "prompt": request.prompt,
        "assigned_kc_id": request.assigned_kc_id,
        "assigned_kc_description": request.assigned_kc_description,
        "sibling_kcs": siblings,
    }
    return [
        {
            "role": "system",
            "content": (
                "Judge whether the question requires the assigned knowledge component rather than a sibling KC. "
                "Return JSON only with keys: passed, suggested_kc_id, rationale."
            ),
        },
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def _parse_judge_verdict(request: ConceptAlignmentRequest, content: str) -> ConceptAlignmentVerdict:
    raw = content.strip()
    if raw.startswith("```json"):
        raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
    elif raw.startswith("```"):
        raw = raw.split("```", 2)[1].strip()
    data = json.loads(raw)
    passed = bool(data["passed"])
    suggested = str(data["suggested_kc_id"])
    rationale = str(data["rationale"])
    return ConceptAlignmentVerdict(
        question_id=request.question_id,
        assigned_kc_id=request.assigned_kc_id,
        passed=passed,
        suggested_kc_id=suggested,
        rationale=rationale,
    )


def _majority_verdict(
    request: ConceptAlignmentRequest,
    verdicts: list[ConceptAlignmentVerdict],
) -> ConceptAlignmentVerdict:
    pass_count = sum(1 for verdict in verdicts if verdict.passed)
    passed = pass_count >= (len(verdicts) * 2 / 3)
    suggested = _most_common_suggestion(verdicts, request.assigned_kc_id)
    rationale = "; ".join(verdict.rationale for verdict in verdicts)
    return ConceptAlignmentVerdict(
        question_id=request.question_id,
        assigned_kc_id=request.assigned_kc_id,
        passed=passed,
        suggested_kc_id=request.assigned_kc_id if passed else suggested,
        rationale=f"majority {pass_count}/{len(verdicts)} passed; {rationale}",
    )


def _most_common_suggestion(verdicts: list[ConceptAlignmentVerdict], fallback: str) -> str:
    counts: dict[str, int] = {}
    for verdict in verdicts:
        if verdict.passed:
            continue
        counts[verdict.suggested_kc_id] = counts.get(verdict.suggested_kc_id, 0) + 1
    if not counts:
        return fallback
    return max(counts.items(), key=lambda item: item[1])[0]


def _terms(value: str) -> set[str]:
    return {
        token.strip(".,?!;:()[]{}\"'").casefold()
        for token in value.split()
        if len(token.strip(".,?!;:()[]{}\"'")) >= 4
    }


def _overlap(prompt_terms: set[str], description: str) -> int:
    return len(prompt_terms & _terms(description))

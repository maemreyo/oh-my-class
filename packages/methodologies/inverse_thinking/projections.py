from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from common.contracts.components import Callout, Heading, Paragraph, QuestionCard, QuestionList, Table
from common.contracts.inverse_thinking import (
    InverseThinkingPack,
    InverseThinkingSummaryRow,
    InverseThinkingTeacherOnly,
)

StudentComponent = Heading | Paragraph | Callout | Table | QuestionList
ProjectionArtifactType = Literal["lesson", "worksheet", "quiz", "drill"]


class InverseThinkingProjection(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifact_type: ProjectionArtifactType
    methodology: Literal["inverse_thinking"] = "inverse_thinking"
    case_ids: list[str] = Field(..., min_length=1)
    student_components: list[StudentComponent] = Field(..., min_length=1)
    summary_rows: list[InverseThinkingSummaryRow] = Field(default_factory=list)
    teacher_only: InverseThinkingTeacherOnly


class _SemanticIssue(BaseModel):
    case_id: str
    step: Literal["disaster", "key_clues", "safe_zone", "filing_note"]
    message: str


def normalize_pack(payload: InverseThinkingPack | dict[str, Any]) -> InverseThinkingPack:
    if isinstance(payload, InverseThinkingPack):
        data = payload.model_dump()
    else:
        data = dict(payload)
    data.setdefault("methodology", "inverse_thinking")
    data.setdefault("creative_frame", "auto")
    return InverseThinkingPack.model_validate(data)


def validate_semantics(payload: InverseThinkingPack | dict[str, Any]) -> InverseThinkingPack:
    pack = normalize_pack(payload)
    issues: list[_SemanticIssue] = []
    for case in pack.cases:
        disaster = case.disaster.lower()
        safe_zone = case.safe_zone.lower()
        filing_note = case.filing_note.lower()
        if disaster.startswith(("use ", "remember ", "the rule ")):
            issues.append(_SemanticIssue(case_id=case.id, step="disaster", message="case must start from a failure"))
        if not case.key_clues:
            issues.append(_SemanticIssue(case_id=case.id, step="key_clues", message="case needs clues"))
        if not any(token in safe_zone for token in ("use ", "rename", "current", "same", "rule", "before")):
            issues.append(_SemanticIssue(case_id=case.id, step="safe_zone", message="case needs a boundary rule"))
        if len(filing_note.split()) < 4:
            issues.append(_SemanticIssue(case_id=case.id, step="filing_note", message="case needs synthesis"))
    if issues:
        details = [
            {
                "type": "value_error",
                "loc": (issue.case_id, issue.step),
                "msg": issue.message,
                "input": issue.model_dump(),
                "ctx": {"error": ValueError(issue.message)},
            }
            for issue in issues
        ]
        raise ValidationError.from_exception_data("InverseThinkingSemantics", details)
    return pack


def project_lesson(payload: InverseThinkingPack | dict[str, Any]) -> InverseThinkingProjection:
    pack = validate_semantics(payload)
    components: list[StudentComponent] = [Heading(level=2, text="Disaster-first case file")]
    for case in pack.cases:
        components.extend(
            [
                Heading(level=3, text=f"{case.alias or case.id}: {case.title}", id=case.id),
                Callout(variant="warning", title="Scene", body=case.disaster),
                Paragraph(text="Key clues: " + "; ".join(case.key_clues)),
                Callout(variant="tip", title="Safe zone", body=case.safe_zone),
                Paragraph(text="Filing note: " + case.filing_note),
                Paragraph(text="Student task: " + case.student_task),
            ]
        )
    components.append(_summary_table(pack.summary_table))
    return _projection("lesson", pack, components)


def project_worksheet(payload: InverseThinkingPack | dict[str, Any]) -> InverseThinkingProjection:
    pack = validate_semantics(payload)
    components: list[StudentComponent] = [Heading(level=2, text="Evidence worksheet")]
    for case in pack.cases:
        components.extend(
            [
                Callout(variant="warning", title=f"Evidence {case.id}", body=case.disaster),
                Paragraph(text=f"Clue work for {case.id}: " + "; ".join(case.key_clues)),
                Paragraph(text=f"Write the safe-zone repair for {case.id}: {case.safe_zone}"),
            ]
        )
    components.extend([
        _summary_table(pack.summary_table),
        Paragraph(text="Summary-table practice: complete the trap, clue, and safe rule for a new case."),
    ])
    return _projection("worksheet", pack, components)


def project_quiz(payload: InverseThinkingPack | dict[str, Any]) -> InverseThinkingProjection:
    pack = validate_semantics(payload)
    questions = [
        QuestionCard(
            id=case.id,
            text=f"Which clue makes this disaster unsafe? {case.disaster}",
            options={"A": case.key_clues[0], "B": case.foil, "C": case.target_concept},
            answer="A",
            explain=case.safe_zone,
        )
        for case in pack.cases
    ]
    components: list[StudentComponent] = [
        Heading(level=2, text="Inverse-thinking quiz"),
        QuestionList(
            questions=questions,
            section_key="inverse_thinking_quiz",
            group="inverse_thinking",
            title="Spot the unsafe clue",
        ),
    ]
    return _projection("quiz", pack, components)


def project_drill(payload: InverseThinkingPack | dict[str, Any]) -> InverseThinkingProjection:
    pack = validate_semantics(payload)
    questions = [
        QuestionCard(
            id=f"{challenge.case_id}:{challenge.id}",
            text=f"{challenge.case_id}: {challenge.prompt}",
            options={"A": "Use the safe-zone rule", "B": "Keep the disaster", "C": "Ignore the clues"},
            answer="A",
            explain=_safe_zone_for(pack, challenge.case_id),
        )
        for challenge in pack.student_challenges
    ]
    components: list[StudentComponent] = [
        Heading(level=2, text="Inverse-thinking drill"),
        QuestionList(
            questions=questions,
            section_key="inverse_thinking_drill",
            group="inverse_thinking",
            title="Repair the disaster",
        ),
    ]
    return _projection("drill", pack, components)


def _projection(
    artifact_type: ProjectionArtifactType,
    pack: InverseThinkingPack,
    components: list[StudentComponent],
) -> InverseThinkingProjection:
    return InverseThinkingProjection(
        artifact_type=artifact_type,
        case_ids=[case.id for case in pack.cases],
        student_components=components,
        summary_rows=pack.summary_table,
        teacher_only=pack.teacher_only,
    )


def _summary_table(rows: list[InverseThinkingSummaryRow]) -> Table:
    return Table(
        columns=["Case", "Trap", "Clue", "Safe rule"],
        rows=[[row.case_id, row.trap, row.clue, row.safe_rule] for row in rows],
        caption="Inverse-thinking summary",
    )


def _safe_zone_for(pack: InverseThinkingPack, case_id: str) -> str:
    for case in pack.cases:
        if case.id == case_id:
            return case.safe_zone
    return pack.cases[0].safe_zone

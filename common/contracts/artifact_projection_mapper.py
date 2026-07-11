from __future__ import annotations

from typing import Any, Literal

from common.contracts.artifact import ArtifactContent
from common.contracts.artifact_document import (
    ArtifactDocument,
    ArtifactPayload,
    AssessmentOption,
    AssessmentQuestion,
    RichDocumentSection,
)
from common.contracts.slide_deck import SlideDeckData

_ASSESSMENT_TYPES = frozenset({"quiz", "drill", "exit_ticket"})


class ArtifactProjectionConversionError(ValueError):
    pass


def artifact_document_from_content(
    content: ArtifactContent | dict[str, Any],
    *,
    document_id: str,
    artifact_id: str,
    version: int = 1,
) -> ArtifactDocument:
    parsed = ArtifactContent.model_validate(content)
    audience: Literal["student", "teacher", "print"] = "teacher" if parsed.artifact_type == "answer_key" else "student"
    if parsed.artifact_type == "slide_deck":
        # Slide decks carry their answer boundary in a required, typed
        # `teacher_only`/`teacher_notes` object, not loose leaf keys -- the
        # generic `_student_content` sweep below would delete just `rationale`
        # (a required field) and corrupt the deck instead of removing the
        # boundary. Strip the whole object via `_slide_deck_payload` instead.
        payload = _slide_deck_payload(parsed, audience=audience)
        metadata = {key: value for key, value in parsed.metadata.items() if key != "slide_deck_data"}
        if audience == "student":
            metadata = _student_value(metadata)
    else:
        if audience == "student":
            parsed = _student_content(parsed)
        match parsed.artifact_type:
            case artifact_type if artifact_type in _ASSESSMENT_TYPES:
                payload = _assessment_payload(parsed)
            case _:
                payload = _rich_payload(parsed)
        metadata = parsed.metadata
    language = _document_language(parsed.accessibility)
    return ArtifactDocument(
        document_id=document_id,
        artifact_id=artifact_id,
        artifact_type=parsed.artifact_type,
        version=version,
        language=language,
        audience=audience,
        authority="generated",
        title=parsed.title,
        theme=parsed.theme,
        metadata=metadata,
        payload=payload,
    )


def artifact_content_from_document(document: ArtifactDocument, *, theme: str | None = None) -> ArtifactContent:
    match document.payload.payload_kind:
        case "assessment_document":
            sections = [{
                "title": "Questions",
                "components": [
                    {
                        "type": "question_card",
                        "id": question.entity_id,
                        "text": question.prompt,
                        "options": {option.entity_id: option.text for option in question.options},
                    }
                    for question in document.payload.questions or []
                ],
            }]
        case "block_document":
            sections = [
                {
                    "id": section.entity_id,
                    "title": section.title,
                    "components": [
                        {
                            "type": "heading" if block.block_kind == "heading" else "paragraph",
                            "text": block.text,
                            **({"level": block.level} if block.level is not None else {}),
                        }
                        for block in section.blocks
                    ],
                }
                for section in document.payload.sections or []
            ]
        case "rich_document":
            sections = [
                {
                    "id": section.entity_id,
                    "title": section.title,
                    "components": section.components,
                }
                for section in document.payload.rich_sections or []
            ]
        case "slide_deck_document":
            slide_deck = document.payload.slide_deck
            if slide_deck is None:
                raise ArtifactProjectionConversionError("slide_deck_document requires slide_deck")
            sections = [{"title": "Deck", "components": [{"type": "paragraph", "text": "Slide deck"}]}]
        case unreachable:
            raise ArtifactProjectionConversionError(f"unknown payload kind {unreachable}")
    return ArtifactContent(
        artifact_type=document.artifact_type,
        theme=theme or document.theme,
        title=document.title,
        sections=sections,
        metadata={
            **document.metadata,
            "document_id": document.document_id,
            "document_version": document.version,
            **({"slide_deck_data": slide_deck.model_dump(mode="json")} if document.payload.payload_kind == "slide_deck_document" else {}),
        },
        accessibility={"language": document.language},
    )


def _assessment_payload(content: ArtifactContent) -> ArtifactPayload:
    questions: list[AssessmentQuestion] = []
    for section in content.sections:
        components = section.get("components")
        if not isinstance(components, list):
            continue
        for component in components:
            if not isinstance(component, dict) or component.get("type") != "question_card":
                continue
            question_id = component.get("id")
            prompt = component.get("text")
            options = component.get("options")
            if not isinstance(question_id, str) or not question_id or not isinstance(prompt, str) or not prompt:
                raise ArtifactProjectionConversionError("question_card requires a non-empty id and text")
            if not isinstance(options, dict) or not all(
                isinstance(option_id, str) and option_id and isinstance(text, str) and text
                for option_id, text in options.items()
            ):
                raise ArtifactProjectionConversionError("question_card requires string option identifiers and text")
            questions.append(AssessmentQuestion(
                entity_id=question_id,
                prompt=prompt,
                options=[AssessmentOption(entity_id=option_id, text=text) for option_id, text in options.items()],
            ))
    if not questions:
        raise ArtifactProjectionConversionError("assessment requires answer-bearing question_card components")
    return ArtifactPayload(payload_kind="assessment_document", questions=questions)


def _rich_payload(content: ArtifactContent) -> ArtifactPayload:
    sections: list[RichDocumentSection] = []
    for index, section in enumerate(content.sections, start=1):
        components = section.get("components")
        if not isinstance(components, list) or not components:
            content_text = section.get("content")
            if not isinstance(content_text, str) or not content_text:
                raise ArtifactProjectionConversionError(f"section {index} has no mappable student-safe content")
            components = [{"type": "paragraph", "text": content_text}]
        title = section.get("title")
        sections.append(RichDocumentSection(
            entity_id=str(section.get("id") or f"section-{index}"),
            title=title if isinstance(title, str) and title else f"Section {index}",
            components=components,
        ))
    return ArtifactPayload(payload_kind="rich_document", rich_sections=sections)


def _slide_deck_payload(content: ArtifactContent, *, audience: str) -> ArtifactPayload:
    deck_data = content.metadata.get("slide_deck_data")
    if not isinstance(deck_data, dict):
        raise ArtifactProjectionConversionError("slide_deck requires metadata.slide_deck_data")
    deck = SlideDeckData.model_validate(deck_data)
    if audience == "student":
        deck = _student_safe_slide_deck(deck)
    return ArtifactPayload(payload_kind="slide_deck_document", slide_deck=deck)


def _student_safe_slide_deck(deck: SlideDeckData) -> SlideDeckData:
    """Drop each slide's `teacher_notes` and each interaction's `teacher_only`
    object wholesale -- those objects ARE the deck's answer-separation
    boundary, so removing them (not their individual leaf keys) is what makes
    the student projection structurally answer-free."""
    return deck.model_copy(update={
        "slides": [
            slide.model_copy(update={
                "teacher_notes": None,
                "interactions": [
                    interaction.model_copy(update={"teacher_only": None})
                    for interaction in slide.interactions
                ],
            })
            for slide in deck.slides
        ],
    })


def _document_language(accessibility: dict[str, Any]) -> Literal["en", "vi"]:
    language = accessibility.get("language")
    match language:
        case "vi":
            return "vi"
        case _:
            return "en"


def _student_content(content: ArtifactContent | dict[str, Any]) -> ArtifactContent:
    projection = ArtifactContent.model_validate(content).model_dump(mode="json")
    projection["metadata"] = _student_value(projection["metadata"])
    projection["sections"] = _student_value(projection["sections"])
    return ArtifactContent.model_validate(projection)


def _student_value(value: Any) -> Any:
    forbidden_keys = frozenset({
        "answer",
        "answer_set",
        "accepted_answers",
        "correct_option_ids",
        "explain",
        "rationale",
        "wrong_reasons",
    })
    if isinstance(value, list):
        return [_student_value(item) for item in value]
    if not isinstance(value, dict):
        return value
    return {
        key: _student_value(item)
        for key, item in value.items()
        if key not in forbidden_keys
    }

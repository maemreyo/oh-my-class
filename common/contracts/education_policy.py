from __future__ import annotations

from enum import StrEnum
from typing import Literal

EDUCATION_POLICY_VERSION = "education_policy.v1"
SubjectKeyValue = Literal[
    "english", "geography", "history", "informatics", "language_arts",
    "literature", "math", "science", "vietnamese",
]
CurriculumFrameworkValue = Literal["ccss", "general", "moet_2018", "ngss"]
InstructionLanguageValue = Literal["en", "vi"]
TargetLanguageValue = Literal["en", "vi"]


class SubjectKey(StrEnum):
    ENGLISH = "english"
    GEOGRAPHY = "geography"
    HISTORY = "history"
    INFORMATICS = "informatics"
    LANGUAGE_ARTS = "language_arts"
    LITERATURE = "literature"
    MATH = "math"
    SCIENCE = "science"
    VIETNAMESE = "vietnamese"


class CurriculumFramework(StrEnum):
    CCSS = "ccss"
    GENERAL = "general"
    MOET_2018 = "moet_2018"
    NGSS = "ngss"


class Audience(StrEnum):
    STUDENT = "student"
    TEACHER = "teacher"


class ArtifactKind(StrEnum):
    ANSWER_KEY = "answer_key"
    DRILL = "drill"
    EXIT_TICKET = "exit_ticket"
    FLASHCARD_DECK = "flashcard_deck"
    INFOGRAPHIC = "infographic"
    LESSON = "lesson"
    QUIZ = "quiz"
    READING_PASSAGE = "reading_passage"
    RECAP = "recap"
    ROADMAP = "roadmap"
    SLIDE_DECK = "slide_deck"
    WORKSHEET = "worksheet"


class CapabilityStatus(StrEnum):
    CERTIFIED = "certified"
    EXPERIMENTAL = "experimental"
    UNSUPPORTED = "unsupported"


class ClaimRisk(StrEnum):
    HIGH = "high"
    LOW = "low"
    STANDARD = "standard"


class ResearchRigor(StrEnum):
    BASIC = "basic"
    RIGOROUS = "rigorous"
    STANDARD = "standard"


def normalize_subject(value: str) -> SubjectKey | None:
    normalized = value.strip().lower().replace(" ", "_")
    aliases = {
        "english_esl": SubjectKey.ENGLISH,
        "language": SubjectKey.LANGUAGE_ARTS,
        "maths": SubjectKey.MATH,
        "mathematics": SubjectKey.MATH,
        "social_studies": SubjectKey.HISTORY,
    }
    match normalized:
        case "english":
            return SubjectKey.ENGLISH
        case "geography":
            return SubjectKey.GEOGRAPHY
        case "history":
            return SubjectKey.HISTORY
        case "informatics":
            return SubjectKey.INFORMATICS
        case "language_arts":
            return SubjectKey.LANGUAGE_ARTS
        case "literature":
            return SubjectKey.LITERATURE
        case "math":
            return SubjectKey.MATH
        case "science":
            return SubjectKey.SCIENCE
        case "vietnamese":
            return SubjectKey.VIETNAMESE
        case _:
            return aliases.get(normalized)


def normalize_language(value: str) -> InstructionLanguageValue | None:
    match value.strip().lower().replace("_", "-"):
        case "en" | "en-us" | "en-gb" | "english":
            return "en"
        case "vi" | "vi-vn" | "vietnamese" | "tiếng việt":
            return "vi"
        case _:
            return None


def curriculum_framework_for(value: str | None) -> CurriculumFrameworkValue:
    if value is None or value.strip() == "":
        return "general"
    normalized = value.strip().casefold()
    match normalized:
        case "ccss" | "common core":
            return "ccss"
        case "ngss":
            return "ngss"
        case "moet_2018" | "bgdđt việt nam" | "ct 2018":
            return "moet_2018"
        case _:
            return "general"

from __future__ import annotations

import json
import re
import unicodedata
from functools import cache
from importlib.resources import files
from typing import TypeVar

from pydantic import TypeAdapter

from packages.agents.grounding.models import AgeBand, GroundingContext, TopicNorm

ModelT = TypeVar("ModelT")
_GRADE_PATTERN = re.compile(r"\d+")


def retrieve_grounding(topic: str, grade: str, subject: str, locale: str) -> GroundingContext:
    grade_number = _parse_grade(grade)
    if grade_number is None:
        return GroundingContext(grounding_status="ungrounded")

    age_band = _age_band_for_grade(grade_number)
    topic_norm = _topic_norm_for(topic, grade_number, subject, locale)
    if topic_norm is None:
        if age_band is None:
            return GroundingContext(grounding_status="ungrounded")
        return GroundingContext(grounding_status="partial", age_band=age_band)

    return GroundingContext(
        grounding_status="grounded",
        curriculum=topic_norm.curriculum,
        topic_norm=topic_norm,
        age_band=age_band,
    )


def _parse_grade(grade: str) -> int | None:
    match = _GRADE_PATTERN.search(grade)
    if match is None:
        return None
    return int(match.group(0))


def _topic_norm_for(topic: str, grade: int, subject: str, locale: str) -> TopicNorm | None:
    normalized_topic = _normalize(topic)
    normalized_subject = _normalize(subject)
    for norm in _topic_norms():
        topic_matches = normalized_topic in {_normalize(value) for value in norm.topics}
        if (
            norm.grade == grade
            and norm.locale == locale
            and norm.subject == normalized_subject
            and topic_matches
        ):
            return norm
    return None


def _age_band_for_grade(grade: int) -> AgeBand | None:
    for age_band in _age_bands():
        if age_band.grade_min <= grade <= age_band.grade_max:
            return age_band
    return None


@cache
def _topic_norms() -> tuple[TopicNorm, ...]:
    return tuple(_load_records("curriculum_norms.json", TopicNorm))


@cache
def _age_bands() -> tuple[AgeBand, ...]:
    return tuple(_load_records("age_bands.json", AgeBand))


def _load_records(filename: str, model: type[ModelT]) -> list[ModelT]:
    raw = files("packages.agents.grounding.data").joinpath(filename).read_text(encoding="utf-8")
    return TypeAdapter(list[model]).validate_python(json.loads(raw))


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_marks.split())

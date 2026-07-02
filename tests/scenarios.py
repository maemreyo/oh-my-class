from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScenarioInvariant:
    artifact_types: tuple[str, ...]
    min_bloom_levels: int
    locale: str
    requires_standalone_html: bool
    forbids_answer_key_leakage: bool


@dataclass(frozen=True, slots=True)
class TeachingPackScenario:
    key: str
    raw_request: str
    class_info: dict[str, object]
    invariants: ScenarioInvariant


SCENARIOS: tuple[TeachingPackScenario, ...] = (
    TeachingPackScenario(
        key="math_vn",
        raw_request="Dạy phân số tương đương cho lớp 5 trong 45 phút",
        class_info={
            "topic": "Phân số tương đương",
            "grade": 5,
            "subject": "math",
            "locale": "vi-VN",
            "instruction_language": "vi",
            "artifact_types": ["lesson", "worksheet"],
        },
        invariants=ScenarioInvariant(
            artifact_types=("lesson", "worksheet"),
            min_bloom_levels=2,
            locale="vi-VN",
            requires_standalone_html=True,
            forbids_answer_key_leakage=True,
        ),
    ),
)


def scenario_by_key(key: str) -> TeachingPackScenario:
    for scenario in SCENARIOS:
        if scenario.key == key:
            return scenario
    raise KeyError(key)

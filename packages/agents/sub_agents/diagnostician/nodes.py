"""Diagnostician Agent — LangGraph node function.

Analyses a student's wrong answers using the DiagnosticReport schema.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from common.contracts.diagnostic_report import DiagnosticReport
from packages.agents.sub_agents.diagnostician.tools import (
    bloom_taxonomy_lookup,
    question_type_classifier,
)
from packages.agents.teaching_pack.stages import StageEnum, stage_number

if TYPE_CHECKING:
    from packages.agents.sub_agents.diagnostician.state import DiagnosticianState


async def diagnostician_node(state: DiagnosticianState) -> dict[str, Any]:
    """Analyse student_responses and return a structured DiagnosticReport.

    Enriches the LLM prompt with pre-computed tool outputs:
    - question_type_classifier groups wrong questions by knowledge section
    - bloom_taxonomy_lookup provides Vietnamese Bloom level names and descriptions

    Returns: {"diagnostic_report": {...}}
    """
    if state.get("use_structured_diagnostic", False):
        report = await _structured_report(
            state.get("student_responses") or {},
            run_id=str(state.get("run_id", "")),
            current_step=state.get("current_step", StageEnum.PLANNING_BLUEPRINT),
        )
        return {"diagnostic_report": report.model_dump()}

    from packages.agents.sub_agents.diagnostician.prompts import load_system_prompt

    system_prompt = load_system_prompt()

    student_responses = state.get("student_responses") or {}

    # Pre-compute grouped sections and Bloom reference for the LLM
    section_map = {
        str(a["question_id"]): a.get("section") or "unknown"
        for a in student_responses.get("answers", [])
    }
    grouped_by_section = question_type_classifier(
        student_responses.get("wrong_question_ids", []), section_map
    )
    bloom_reference = {
        level: bloom_taxonomy_lookup(level)
        for level in ["remember", "understand", "apply", "analyze", "evaluate", "create"]
    }

    user_prompt = f"""Analyse the following student response and produce a DiagnosticReport.

StudentResponse:
{json.dumps(student_responses, ensure_ascii=False, indent=2)}

Wrong questions grouped by section (pre-computed):
{json.dumps(grouped_by_section, ensure_ascii=False, indent=2)}

Bloom taxonomy reference (Vietnamese names):
{json.dumps(
    {k: {"vn_name": v["vn_name"], "description": v["description"]}
     for k, v in bloom_reference.items()},
    ensure_ascii=False, indent=2)}
"""

    from packages.agents.config.models import MODELS
    from packages.agents.runtime import AgentRuntime, AgentRuntimeConfig

    model = MODELS.diagnostician
    run_id = str(state.get("run_id", ""))
    current_step = state.get("current_step", StageEnum.PLANNING_BLUEPRINT)
    step = stage_number(current_step)
    runtime = AgentRuntime(AgentRuntimeConfig(
        agent="diagnostician",
        run_id=run_id,
        step=step,
        step_label=current_step.value,
        model=model,
        base_temperature=0.3,
        retry_temperature=0.3,
    ))
    messages = runtime.messages(system_prompt, user_prompt)

    try:
        content = await runtime.complete_json(
            messages=messages,
            attempt=0,
        )

        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content.strip()

        report_data = json.loads(json_str)
        report = DiagnosticReport.model_validate(report_data)
        return {"diagnostic_report": report.model_dump()}

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from LLM: {e}") from e
    except Exception as e:
        raise ValueError(f"Diagnostician agent failed: {e}") from e


async def _structured_report(
    student_responses: dict[str, Any],
    *,
    run_id: str,
    current_step: StageEnum,
) -> DiagnosticReport:
    answers = _answers(student_responses)
    wrong_answers = [answer for answer in answers if answer.get("correct") is False]
    total = max(1, len(answers))
    knowledge_gaps = [_knowledge_gap(section, grouped, total) for section, grouped in _group_by(wrong_answers, "section").items()]
    bloom_gaps = [_bloom_gap(level, grouped, total) for level, grouped in _group_by(wrong_answers, "bloom_level").items()]
    misconceptions, summary = await _misconceptions_and_summary(
        wrong_answers, knowledge_gaps, bloom_gaps, run_id=run_id, current_step=current_step,
    )
    report = DiagnosticReport(
        student_id=str(student_responses.get("student_id", "unknown")),
        knowledge_gaps=knowledge_gaps,
        bloom_gaps=bloom_gaps,
        misconception_patterns=misconceptions,
        critical_sections=[gap.category for gap in knowledge_gaps if gap.severity == "critical"],
        overall_error_rate=len(wrong_answers) / total,
        recommended_level="B1" if len(wrong_answers) / total >= 0.5 else "B2",
        summary=summary,
    )
    return report


def _answers(student_responses: dict[str, Any]) -> list[dict[str, Any]]:
    value = student_responses.get("answers")
    if not isinstance(value, list):
        return []
    return [answer for answer in value if isinstance(answer, dict)]


def _group_by(answers: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for answer in answers:
        grouped.setdefault(str(answer.get(key, "unknown")), []).append(answer)
    return grouped


def _knowledge_gap(section: str, answers: list[dict[str, Any]], total: int):
    from common.contracts.diagnostic_report import KnowledgeGap

    error_rate = len(answers) / total
    return KnowledgeGap(
        category=section,
        error_count=len(answers),
        error_rate=error_rate,
        severity=_severity(error_rate),
        question_ids=_question_ids(answers),
        confidence=min(1.0, max(0.8, error_rate)),
    )


def _bloom_gap(level: str, answers: list[dict[str, Any]], total: int):
    from common.contracts.diagnostic_report import BloomGap
    from packages.agents.sub_agents.diagnostician.tools import bloom_taxonomy_lookup

    lookup = bloom_taxonomy_lookup(level)
    error_rate = len(answers) / total
    return BloomGap(
        bloom_level=level,
        vn_name=str(lookup["vn_name"]),
        error_count=len(answers),
        error_rate=error_rate,
        confidence=min(1.0, max(0.5, error_rate)),
    )


async def _misconceptions_and_summary(
    wrong_answers: list[dict[str, Any]],
    knowledge_gaps: list[Any],
    bloom_gaps: list[Any],
    *,
    run_id: str,
    current_step: StageEnum,
) -> tuple[list[Any], str]:
    """Deterministic grouping/counts stay exact; LLM only names/describes each
    misconception and writes the student-facing summary — numbers can't drift."""
    from common.contracts.diagnostic_report import MisconceptionPattern

    error_answers = [answer for answer in wrong_answers if answer.get("error")]
    grouped = _group_by(error_answers, "error")
    if not grouped:
        return [], "No wrong answers to diagnose — no misconceptions detected."

    classifications = await _classify_misconceptions_llm(
        list(grouped.keys()), knowledge_gaps, bloom_gaps, run_id=run_id, current_step=current_step,
    )
    patterns: list[MisconceptionPattern] = []
    for index, (error, grouped_answers) in enumerate(grouped.items(), start=1):
        systematic = "systematic" if len(grouped_answers) >= 2 else "contextual"
        classification = classifications.misconceptions.get(error)
        title = classification.title if classification else "Contextual procedural slip"
        description = classification.description if classification else f"Ungrouped error pattern: {error}"
        patterns.append(MisconceptionPattern(
            id=f"M{index:02d}",
            group=classification.group if classification else "a",
            title=title,
            description=description,
            question_ids=_question_ids(grouped_answers),
            systematicity=systematic,
            confidence=min(1.0, len(grouped_answers) / max(1, len(wrong_answers))),
        ))
    return patterns, classifications.summary


@dataclass(frozen=True, slots=True)
class _MisconceptionClassification:
    title: str
    description: str
    group: str


@dataclass(frozen=True, slots=True)
class _DiagnosticClassifications:
    misconceptions: dict[str, _MisconceptionClassification]
    summary: str


async def _classify_misconceptions_llm(
    error_keys: list[str],
    knowledge_gaps: list[Any],
    bloom_gaps: list[Any],
    *,
    run_id: str,
    current_step: StageEnum,
) -> _DiagnosticClassifications:
    from packages.agents.config.models import MODELS
    from packages.agents.llm import extract_json_text
    from packages.agents.runtime import AgentRuntime, AgentRuntimeConfig

    system_prompt = (
        "You are an expert math/language tutor analysing a student's wrong answers. "
        "For each error description given, name the underlying misconception (a short "
        "title) and a one-sentence explanation, grounded ONLY in the error text — do "
        "not invent details not implied by it. Also write a 1-2 sentence teacher-facing "
        "summary of this student's overall diagnostic picture.\n\n"
        'Respond ONLY with JSON: {"misconceptions": {"<error text>": '
        '{"title": "...", "description": "...", "group": "<a|b|c|d|e>"}}, "summary": "..."}. '
        "No prose, no explanation, no markdown fences."
    )
    user_prompt = (
        f"Error patterns to classify:\n{json.dumps(error_keys, ensure_ascii=False, indent=2)}\n\n"
        f"Knowledge gaps: {json.dumps([g.category for g in knowledge_gaps], ensure_ascii=False)}\n"
        f"Bloom gaps: {json.dumps([g.bloom_level for g in bloom_gaps], ensure_ascii=False)}"
    )
    runtime = AgentRuntime(AgentRuntimeConfig(
        agent="diagnostician",
        run_id=run_id,
        step=stage_number(current_step),
        step_label=current_step.value,
        model=MODELS.diagnostician,
        base_temperature=0.3,
        retry_temperature=0.2,
    ))
    messages = runtime.messages(system_prompt, user_prompt)

    def parse(content: str) -> _DiagnosticClassifications:
        data = json.loads(extract_json_text(content))
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object")
        raw_misconceptions = data.get("misconceptions")
        if not isinstance(raw_misconceptions, dict):
            raise ValueError("expected 'misconceptions' to be an object")
        misconceptions = {
            str(key): _MisconceptionClassification(
                title=str(value.get("title", "Contextual procedural slip")),
                description=str(value.get("description", "")),
                group=str(value.get("group", "a")),
            )
            for key, value in raw_misconceptions.items()
            if isinstance(value, dict)
        }
        return _DiagnosticClassifications(misconceptions=misconceptions, summary=str(data.get("summary", "")))

    try:
        return await runtime.complete_json_with_retries(
            messages=messages,
            parse=parse,
            retry_messages=lambda _err, _content: runtime.messages(
                system_prompt, "Invalid response. Return ONLY the JSON object described above.",
            ),
        )
    except (ValueError, json.JSONDecodeError) as parse_err:
        raise ValueError(f"Diagnostician misconception classification failed: {parse_err}") from parse_err
    except Exception as exc:
        raise ValueError(f"Diagnostician misconception classification failed: {exc}") from exc


def _severity(error_rate: float):
    if error_rate >= 0.5:
        return "critical"
    if error_rate >= 0.25:
        return "moderate"
    return "minor"


def _question_ids(answers: list[dict[str, Any]]) -> list[int | str]:
    return [answer.get("question_id", "unknown") for answer in answers]

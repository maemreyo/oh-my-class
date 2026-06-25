"""Diagnostician Agent — LangGraph node function.

Analyses a student's wrong answers using the DiagnosticReport schema.
"""

from __future__ import annotations

import json
from typing import Any

from common.contracts.diagnostic_report import DiagnosticReport

from packages.agents.sub_agents.diagnostician.state import DiagnosticianState
from packages.agents.sub_agents.diagnostician.tools import (
    bloom_taxonomy_lookup,
    question_type_classifier,
)


async def diagnostician_node(state: DiagnosticianState) -> dict[str, Any]:
    """Analyse student_responses and return a structured DiagnosticReport.

    Enriches the LLM prompt with pre-computed tool outputs:
    - question_type_classifier groups wrong questions by knowledge section
    - bloom_taxonomy_lookup provides Vietnamese Bloom level names and descriptions

    Returns: {"diagnostic_report": {...}}
    """
    import litellm

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
{json.dumps({k: {"vn_name": v["vn_name"], "description": v["description"]} for k, v in bloom_reference.items()}, ensure_ascii=False, indent=2)}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = await litellm.acompletion(
            model="f.light",
            messages=messages,
            temperature=0.3,
            extra_body={
                "metadata": {
                    "tags": [
                        "agent:diagnostician",
                        f"step:{state.get('current_step', 0)}",
                        f"run:{state.get('run_id', '')}",
                        "pipeline:oh-my-class",
                    ]
                }
            },
        )

        content = response.choices[0].message.content

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

"""Content Creator Agent — LangGraph node function and validators."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from common.contracts.artifact import ArtifactContent
from packages.agents.sub_agents.content_creator.summarizers import (
    summarize_lesson_plan,
    summarize_research_bundle,
)

if TYPE_CHECKING:
    from packages.agents.sub_agents.content_creator.state import ContentCreatorState


RUNTIME_SYSTEM_PROMPT = """You are the Content Creator Agent for oh-my-class.
Return only a JSON array of ArtifactContent objects. No markdown, prose, or raw HTML.

ArtifactContent fields: artifact_type, theme, title, sections, metadata (dict, not string),
accessibility (dict e.g. {"language":"vi"}, not string).
Allowed artifact_type values: lesson, worksheet, quiz, drill, recap, infographic.
Allowed theme values: default, ocean, forest.

Hard rules:
- Output structured JSON data for the Eta renderer, never HTML.
- No CDN references, external asset URLs, placeholders, or student PII.
- Answer keys and correct answers must be in teacher_only sections or component fields.
- Every section needs type, title, and components unless it is a question_card section.
- Use components as the primary content carrier.

Component types: heading, paragraph, callout, table, stat_grid, pattern_grid,
trait_grid, taxonomy_grid, phase_timeline, flow_step, question_card,
question_list, concept_map, timeline, vocab_cluster, contrastive_pairs,
active_recall_prompt, hw_list.

Required component fields:
- heading requires: type, level, text. Level must be 1|2|3|4.
- paragraph requires: type, text.
- callout requires: type, variant (note|warning|tip|alert), body.
- table requires: type, columns (list[str]), rows (list[list[str]]).
- stat_grid requires: type, stats (list of {label, value}).
- phase_timeline requires: type, phases (list of {title, when}).
- flow_step requires: type, steps (list of {time, title, body}).
- question_card requires: type, id, text, options (dict e.g. {"A":"..","B":".."}), answer, explain.
- question_list requires: type, questions, section_key, group, title.
- concept_map requires: type, nodes (list of {id, label}).
- timeline requires: type, events (list of {time, label}).
- vocab_cluster requires: type, title, items (list of {word, definition}).
- active_recall_prompt requires: type, instruction.

For lesson artifacts: create at least 5 titled student-facing sections, at least
2 non-structural components, one teaching component, and one assessment component.
Question cards use: id, text, options A-D, answer, explain, wrong_reasons.
"""


async def content_creator_node(state: ContentCreatorState) -> dict[str, Any]:
    """Generate lesson artifacts from plan + research.

    Returns: {"artifacts": [...]}
    """
    lesson_plan = state.get("lesson_plan") or {}
    research_bundle = state.get("research_bundle") or {}
    artifact_types = state.get("artifact_types") or ["lesson"]
    theme = state.get("theme", "default")
    lesson_summary = summarize_lesson_plan(lesson_plan)
    research_summary = summarize_research_bundle(research_bundle)

    user_prompt = f"""
Generate artifacts for the following lesson:

Lesson Plan Summary:
{json.dumps(lesson_summary, ensure_ascii=False, indent=2)}

Research Summary:
{json.dumps(research_summary, ensure_ascii=False, indent=2)}

Artifact types to generate: {artifact_types}
Theme: {theme}

Please generate one ArtifactContent JSON for each artifact type.
Return a JSON array of artifacts.
"""
    base_user_prompt = user_prompt

    from packages.agents.config.models import MODELS
    from packages.agents.llm import (
        chat_messages,
        complete_json_chat,
        extract_json_text,
        log_llm_failure,
        log_llm_start,
        log_llm_success,
    )

    model = MODELS.content_creator
    run_id = str(state.get("run_id", ""))
    step = int(state.get("current_step", 8))
    system_prompt = RUNTIME_SYSTEM_PROMPT
    messages = chat_messages(system_prompt, user_prompt)

    content = None
    for attempt in range(3):
        attempt_number = attempt + 1
        started = log_llm_start(
            "content_creator", run_id, step, model, attempt_number,
        )
        try:
            content = await complete_json_chat(
                model=model,
                messages=messages,
                temperature=0.3 if attempt > 0 else 0.7,
                tags=[
                    "agent:content_creator",
                    f"step:{state.get('current_step', 8)}",
                    f"run:{state.get('run_id', '')}",
                    "pipeline:oh-my-class",
                ],
            )
            log_llm_success("content_creator", run_id, step, model, attempt_number, started)
            json_str = extract_json_text(content)
            artifacts_data = json.loads(json_str)

            if isinstance(artifacts_data, dict):
                # LLM returned single object — wrap in array
                artifacts_data = [artifacts_data]

            artifacts = []
            for artifact_data in artifacts_data:
                artifact = ArtifactContent.model_validate(artifact_data)
                artifacts.append(artifact.model_dump())

            return {"artifacts": artifacts}
        except (ValueError, json.JSONDecodeError) as parse_err:
            log_llm_failure(
                "content_creator", run_id, step, model, attempt_number, started, parse_err,
            )
            if attempt < 2:
                messages = chat_messages(
                    system_prompt,
                    _retry_prompt(base_user_prompt, parse_err),
                )
                continue
            raise ValueError(f"Content creator agent failed: {parse_err}") from parse_err
        except Exception as e:
            log_llm_failure("content_creator", run_id, step, model, attempt_number, started, e)
            if attempt < 2:
                messages = chat_messages(system_prompt, _retry_prompt(base_user_prompt, e))
                continue
            raise ValueError(f"Content creator agent failed: {e}") from e

    raise ValueError("Content creator agent failed: exhausted retries")


def _retry_prompt(base_user_prompt: str, error: BaseException) -> str:
    return f"""
Previous validation error:
{str(error)[:1200]}

Repair the response using the same lesson and research context below.
Return ONLY a JSON array of ArtifactContent objects. Do not return markdown or prose.
Make every component satisfy its required fields, especially heading.level.

{base_user_prompt}
"""


def validate_no_cdn(artifacts: list[dict[str, Any]]) -> list[str]:
    """Check for CDN references in artifacts."""
    issues = []
    cdn_patterns = ["cdn.", "cloudflare.com", "jsdelivr.net", "unpkg.com"]
    for i, artifact in enumerate(artifacts):
        content = json.dumps(artifact)
        for pattern in cdn_patterns:
            if pattern in content:
                issues.append(f"CDN reference found in artifact {i}: {pattern}")
    return issues


def validate_no_pii(artifacts: list[dict[str, Any]]) -> list[str]:
    """Check for PII in artifacts."""
    issues = []
    email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    phone_pattern = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")
    for i, artifact in enumerate(artifacts):
        content = json.dumps(artifact)
        if email_pattern.search(content):
            issues.append(f"Email found in artifact {i}")
        if phone_pattern.search(content):
            issues.append(f"Phone number found in artifact {i}")
    return issues

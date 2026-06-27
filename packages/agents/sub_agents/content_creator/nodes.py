"""Content Creator Agent — LangGraph node function and validators."""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

_LOGGER = logging.getLogger(__name__)

from common.contracts.artifact import ArtifactContent
from packages.agents.sub_agents.content_creator.summarizers import (
    summarize_lesson_plan,
    summarize_research_bundle,
)

if TYPE_CHECKING:
    from packages.agents.sub_agents.content_creator.state import ContentCreatorState


_JSON_ONLY_SUFFIX = (
    "\n\nCRITICAL: Respond ONLY with a JSON array of ArtifactContent objects. "
    "No prose, no explanation, no markdown code fences. Just the raw JSON."
)


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
    from packages.agents.sub_agents.content_creator.prompts import load_system_prompt

    model = MODELS.content_creator
    run_id = str(state.get("run_id", ""))
    step = int(state.get("current_step", 8))
    system_prompt = load_system_prompt() + _JSON_ONLY_SUFFIX
    messages = chat_messages(system_prompt, user_prompt)

    content = None
    last_content = None
    for attempt in range(3):
        attempt_number = attempt + 1
        started = log_llm_start(
            "content_creator", run_id, step, model, attempt_number,
        )
        try:
            content = await complete_json_chat(
                model=model,
                messages=messages,
                temperature=0.3,
                tags=[
                    "agent:content_creator",
                    f"step:{state.get('current_step', 8)}",
                    f"run:{state.get('run_id', '')}",
                    f"attempt:{attempt_number}",
                    "pipeline:oh-my-class",
                ],
            )
            last_content = content
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
                    _retry_prompt(base_user_prompt, parse_err, last_content),
                )
                continue
            raise ValueError(f"Content creator agent failed: {parse_err}") from parse_err
        except Exception as e:
            log_llm_failure("content_creator", run_id, step, model, attempt_number, started, e)
            if attempt < 2:
                messages = chat_messages(system_prompt, _retry_prompt(base_user_prompt, e, last_content))
                continue
            _LOGGER.warning(
                "content_creator.fallback_placeholder run_id=%s model=%s error=%s",
                run_id, model, str(e)[:200],
            )
            topic = lesson_plan.get("topic", "Bài học")
            placeholders = _build_placeholder_artifacts(artifact_types, theme, topic)
            return {"artifacts": placeholders}

    raise ValueError("Content creator agent failed: exhausted retries")


def _retry_prompt(base_user_prompt: str, error: BaseException, last_content: str | None = None) -> str:
    failed_output_section = ""
    if last_content:
        failed_output_section = f"""
Your previous output (which failed validation):
{last_content[:3000]}

"""
    return f"""
{failed_output_section}Previous validation error:
{str(error)[:1200]}

Fix the specific issues above. Return ONLY a JSON array of ArtifactContent objects.
Do not return markdown or prose. Every component must satisfy its required fields:
- heading: type, level (1|2|3|4), text
- paragraph: type, text
- callout: type, variant (note|warning|tip|alert), body
- question_card: type, id, text, options (dict with A-D keys), answer, explain
- question_list: type, questions (list of question_card), section_key, group, title

{base_user_prompt}
"""


def _build_placeholder_artifacts(
    artifact_types: list[str], theme: str, topic: str,
) -> list[dict[str, Any]]:
    placeholders = []
    for atype in artifact_types:
        placeholder = ArtifactContent(
            artifact_type=atype,  # type: ignore[arg-type]
            theme=theme,
            title=f"[Cần tạo lại] {topic} — {atype}",
            sections=[{
                "components": [{
                    "type": "heading",
                    "level": 2,
                    "text": f"Nội dung {atype} đang chờ tạo lại",
                }, {
                    "type": "paragraph",
                    "text": (
                        "Hệ thống gặp lỗi khi tạo nội dung tự động. "
                        "Vui lòng từ chối và yêu cầu tạo lại."
                    ),
                }],
            }],
            metadata={"placeholder": True, "error": "LLM timeout"},
        )
        placeholders.append(placeholder.model_dump())
    return placeholders


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

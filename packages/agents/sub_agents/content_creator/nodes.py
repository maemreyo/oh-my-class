"""Content Creator Agent — LangGraph node function and validators."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from common.contracts.artifact import ArtifactContent

if TYPE_CHECKING:
    from packages.agents.sub_agents.content_creator.state import ContentCreatorState


async def content_creator_node(state: ContentCreatorState) -> dict[str, Any]:
    """Generate lesson artifacts from plan + research.

    Returns: {"artifacts": [...]}
    """
    from packages.agents.sub_agents.content_creator.prompts import load_system_prompt
    content_creator_system_prompt = load_system_prompt()

    lesson_plan = state.get("lesson_plan") or {}
    research_bundle = state.get("research_bundle") or {}
    artifact_types = state.get("artifact_types") or ["lesson"]
    theme = state.get("theme", "default")

    user_prompt = f"""
Generate artifacts for the following lesson:

Lesson Plan:
{json.dumps(lesson_plan, indent=2)}

Research Bundle:
{json.dumps(research_bundle, indent=2)}

Artifact types to generate: {artifact_types}
Theme: {theme}

Please generate one ArtifactContent JSON for each artifact type.
Return a JSON array of artifacts.
"""

    from packages.agents.llm import (
        chat_messages,
        complete_json_chat,
        extract_json_text,
        log_llm_failure,
        log_llm_start,
        log_llm_success,
        resolve_model,
    )

    model = resolve_model("f.light")
    run_id = str(state.get("run_id", ""))
    step = int(state.get("current_step", 8))
    system_prompt = (
        content_creator_system_prompt
        + "\n\nCRITICAL: Respond ONLY with a JSON array. "
        "No prose, no explanation, no markdown fences."
    )
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
                    "Invalid response. Return ONLY the JSON array of artifacts.",
                )
                continue
            raise ValueError(f"Content creator agent failed: {parse_err}") from parse_err
        except Exception as e:
            log_llm_failure("content_creator", run_id, step, model, attempt_number, started, e)
            if attempt < 2:
                continue
            raise ValueError(f"Content creator agent failed: {e}") from e

    raise ValueError("Content creator agent failed: exhausted retries")


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
